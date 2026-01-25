from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Optional
from src.channels.models import ChannelConfig

class BaseChannelService(ABC):
    def __init__(self, channel: ChannelConfig):
        self.channel = channel
        self.credentials = channel.credentials
        self.settings = channel.settings

    @abstractmethod
    async def send_text(self, target_id: str, text: str) -> None:
        """
        Send a simple text message to the target.
        """
        pass

    async def send_stream(self, target_id: str, stream_generator: AsyncGenerator[str, None]) -> None:
        """
        Process stream.
        Default implementation: Accumulate full content and send as single message.
        """
        full_content = []
        async for chunk in stream_generator:
            full_content.append(chunk)
        
        text = "".join(full_content)
        if text.strip():
            await self.send_text(target_id, text)
