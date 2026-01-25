import logging
import httpx
import time
from typing import AsyncGenerator
import json

from src.channels.services.base import BaseChannelService
from src.channels.models import ChannelConfig

logger = logging.getLogger(__name__)

class WecomChannelService(BaseChannelService):
    API_BASE = "https://qyapi.weixin.qq.com/cgi-bin"

    def __init__(self, channel: ChannelConfig):
        super().__init__(channel)
        self.corp_id = self.credentials.get("corp_id")
        self.secret = self.credentials.get("secret")
        self.agent_id = self.credentials.get("agent_id")
        
        # Cache for access token
        self._access_token: str | None = None
        self._token_expires_at: float = 0

    async def get_access_token(self) -> str:
        """
        Get or refresh access token.
        """
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.API_BASE}/gettoken",
                params={"corpid": self.corp_id, "corpsecret": self.secret}
            )
            data = resp.json()
            if data.get("errcode") != 0:
                raise Exception(f"Failed to get WeCom access token: {data}")
            
            self._access_token = data["access_token"]
            # Set expiry a bit earlier than actual (7200s) to be safe
            self._token_expires_at = time.time() + data.get("expires_in", 7200) - 200
            return self._access_token

    async def send_text(self, target_id: str, text: str) -> None:
        """
        Send text message.
        target_id: WeCom User ID (touser). Supports multiple with '|' but here we assume single flow context.
        """
        token = await self.get_access_token()
        
        payload = {
            "touser": target_id,
            "msgtype": "text",
            "agentid": self.agent_id,
            "text": {
                "content": text
            },
            "safe": 0
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.API_BASE}/message/send",
                params={"access_token": token},
                json=payload
            )
            data = resp.json()
            if data.get("errcode") != 0:
                logger.error(f"WeCom send failed: {data}")
                raise Exception(f"WeCom API Error: {data}")

    async def send_stream(self, target_id: str, stream_generator: AsyncGenerator[str, None]) -> None:
        """
        WeCom does not support editing messages or stream.
        We must use "Accumulate & Send" strategy.
        To avoid timeouts on caller side, this is already running in background task, 
        so we just wait for full generation.
        """
        # Alternatively, we could chunk it if it's very long, 
        # but for now, simple accumulation.
        await super().send_stream(target_id, stream_generator)
