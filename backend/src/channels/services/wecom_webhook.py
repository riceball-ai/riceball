import logging
import httpx
from typing import AsyncGenerator

from src.channels.services.base import BaseChannelService
from src.channels.models import ChannelConfig

logger = logging.getLogger(__name__)

class WecomWebhookChannelService(BaseChannelService):
    """
    Service for WeCom Group Robot (Webhook).
    """

    def __init__(self, channel: ChannelConfig):
        super().__init__(channel)
        self.webhook_url = self.credentials.get("webhook_url")
        
        # Helper: If user only pasted the key
        if self.webhook_url and not self.webhook_url.startswith("http"):
             self.webhook_url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={self.webhook_url}"

    async def send_text(self, target_id: str, text: str) -> None:
        """
        Send message to WeCom Group Robot.
        target_id: Ignored (The webhook URL defines the unique target).
        """
        if not self.webhook_url:
            # Fallback: Check if target_id serves as the KEY or URL?
            # This allows 1 Channel Config to serve multiple Webhooks if target_id is passed
            if target_id and (target_id.startswith("http") or len(target_id) > 20):
                 temp_url = target_id
                 if not temp_url.startswith("http"):
                     temp_url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={target_id}"
                 await self._send_to_url(temp_url, text)
                 return
            
            raise ValueError("WeCom Webhook URL not configured and no valid Target ID provided")

        await self._send_to_url(self.webhook_url, text)

    async def _send_to_url(self, url: str, text: str):
        # WeCom Webhook Markdown
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": text
            }
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload)
            try:
                data = resp.json()
                if data.get("errcode") != 0:
                    logger.error(f"WeCom Webhook send failed: {data}")
                    raise Exception(f"WeCom API Error: {data}")
            except Exception as e:
                logger.error(f"Failed to parse response: {resp.text}")
                raise e
