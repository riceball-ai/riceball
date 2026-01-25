from typing import Optional
from fastapi import Request, Response
import httpx
import logging

from src.channels.adapters.base import BaseChannelAdapter, IncomingMessage
from src.channels.models import ChannelConfig

logger = logging.getLogger(__name__)

class TelegramChannelAdapter(BaseChannelAdapter):
    BASE_URL = "https://api.telegram.org/bot"

    def __init__(self, channel: ChannelConfig):
        super().__init__(channel)
        self.token = self.credentials.get("bot_token")
        if not self.token:
            raise ValueError("Telegram Bot Token is missing in credentials")
        self.api_url = f"{self.BASE_URL}{self.token}"

    async def verify_request(self, request: Request) -> bool:
        """
        Verify request using X-Telegram-Bot-Api-Secret-Token header.
        This requires saving a 'secret_token' in channel.credentials when setting up the webhook.
        """
        secret_token = self.credentials.get("secret_token")
        if not secret_token:
            # If no secret configured, assume trusted (or relying on hidden URL path)
            return True
            
        header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if header_secret != secret_token:
            logger.warning(f"Telegram secret token mismatch: {header_secret} != {secret_token}")
            return False
            
        return True

    async def parse_webhook_body(self, request: Request) -> Optional[IncomingMessage]:
        try:
            body = await request.json()
        except Exception:
            return None

        # We only handle 'message' events for now (ignoring edited_message, channel_post, etc.)
        message = body.get("message")
        if not message:
            return None

        text = message.get("text")
        if not text:
            # Could be a photo, sticker, etc. Ignore for now.
            return None

        sender = message.get("from", {})
        user_id = sender.get("id")
        
        if not user_id:
            logger.warning("Telegram message missing 'from.id'")
            return None
            
        username = sender.get("username") # Optional
        message_id = str(message.get("message_id"))

        return IncomingMessage(
            user_id=str(user_id),
            username=username,
            content=text,
            message_id=message_id,
            channel_id=str(self.channel.id)
        )

    def should_stream_response(self, incoming: IncomingMessage) -> bool:
        """
        Telegram Webhooks do not support HTTP Response Streaming.
        (To support 'typing' effect, we would need to implement editMessageText polling in the service)
        """
        return False

    async def send_text(self, user_id: str, text: str):
        url = f"{self.api_url}/sendMessage"
        payload = {
            "chat_id": user_id,
            "text": text,
            "parse_mode": "Markdown" # Or HTML
        }
        
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(url, json=payload, timeout=10.0)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                logger.error(f"Failed to send message to Telegram: {e}")
                # Don't raise, just log.

    async def set_webhook(self, webhook_url: str):
        url = f"{self.api_url}/setWebhook"
        async with httpx.AsyncClient() as client:
            # We can also set secret_token here for extra security
            resp = await client.post(url, json={"url": webhook_url})
            resp.raise_for_status()
            return resp.json()
