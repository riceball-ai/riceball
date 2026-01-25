import logging
import httpx
from typing import AsyncGenerator
import asyncio

from src.channels.services.base import BaseChannelService
from src.channels.models import ChannelConfig

logger = logging.getLogger(__name__)

class TelegramChannelService(BaseChannelService):
    BASE_URL = "https://api.telegram.org/bot"

    def __init__(self, channel: ChannelConfig):
        super().__init__(channel)
        self.token = self.credentials.get("bot_token")
        if not self.token:
            raise ValueError("Telegram Bot Token is missing in credentials")
        self.api_url = f"{self.BASE_URL}{self.token}"

    async def send_text(self, target_id: str, text: str) -> None:
        """
        Send a simple text message.
        target_id: Telegram Chat ID
        """
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self.api_url}/sendMessage",
                    json={"chat_id": target_id, "text": text}
                )
                resp.raise_for_status()
            except Exception as e:
                logger.error(f"Failed to send message to Telegram {target_id}: {e}")
                raise

    async def send_stream(self, target_id: str, stream_generator: AsyncGenerator[str, None]) -> None:
        """
        Simulate stream by editing the message.
        """
        client = httpx.AsyncClient()
        msg_id: str | None = None
        full_text = ""
        last_update_text = ""
        # 频率限制：Telegram 建议编辑频率不高于 1次/秒 (群组可能更严)
        update_interval = 1.0 
        last_time = 0.0

        try:
            # 1. 发送初始消息
            init_resp = await client.post(
                f"{self.api_url}/sendMessage",
                json={"chat_id": target_id, "text": "Thinking..."}
            )
            init_resp.raise_for_status()
            msg_data = init_resp.json()
            msg_id = msg_data.get("result", {}).get("message_id")
            
            if not msg_id:
                # Fallback to accumulate mode if initialization fails
                await super().send_stream(target_id, stream_generator)
                return

            loop = asyncio.get_event_loop()
            
            async for chunk in stream_generator:
                full_text += chunk
                now = loop.time()
                
                # Check if we should update (time elapsed and content changed enough)
                if (now - last_time) >= update_interval and full_text != last_update_text:
                    try:
                        await client.post(
                            f"{self.api_url}/editMessageText",
                            json={
                                "chat_id": target_id,
                                "message_id": msg_id,
                                "text": full_text
                            }
                        )
                        last_update_text = full_text
                        last_time = now
                    except Exception as e:
                        # Continue even if edit fails (e.g. "message not modified" error)
                        logger.warning(f"Telegram edit message failed temp: {e}")

            # Final update ensures complete text
            if full_text != last_update_text:
                 await client.post(
                    f"{self.api_url}/editMessageText",
                    json={
                        "chat_id": target_id,
                        "message_id": msg_id,
                        "text": full_text
                    }
                )

        except Exception as e:
            logger.error(f"Error in telegram stream: {e}")
            # If things crash, try to send what we have as a new message?
            if full_text and full_text != last_update_text:
                 await self.send_text(target_id, full_text)
        finally:
            await client.aclose()
