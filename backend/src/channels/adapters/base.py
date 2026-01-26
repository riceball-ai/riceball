from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union
from fastapi import Request, Response
from pydantic import BaseModel

from src.channels.models import ChannelConfig

class IncomingMessage(BaseModel):
    """Normalized message from external channel"""
    user_id: str  # External user ID
    username: Optional[str] = None
    content: str
    message_id: str
    channel_id: str # The internal DB ID of the channel
    
    # For Streaming Polling
    is_stream_poll: bool = False
    stream_id: Optional[str] = None


class BaseChannelAdapter(ABC):
    def __init__(self, channel: ChannelConfig):
        self.channel = channel
        self.credentials = channel.credentials
        self.settings = channel.settings
        self.direct_response: Optional[Response] = None # Store synchronous response if needed

    @abstractmethod
    async def verify_request(self, request: Request) -> bool:
        """Verify the request signature/token"""
        pass

    @abstractmethod
    async def parse_webhook_body(self, request: Request) -> Optional[IncomingMessage]:
        """Parse the incoming webhook payload into a normalized format"""
        pass
    
    @abstractmethod
    async def send_text(self, user_id: str, text: str):
        """Send a text message back to the user"""
        pass
    
    def should_stream_response(self, incoming: IncomingMessage) -> bool:
        """Determine if we should initiate a stream response for this message"""
        return False

    def format_stream_response(self, stream_id: str, content: str, finished: bool, query_params: Any) -> Any:
        """Format the response for a stream poll or initiation"""
        raise NotImplementedError("This adapter does not support streaming")

    # Optional hook for handshake challenges (needed for Slack/WeCom)
    async def handle_handshake(self, request: Request) -> Optional[Response]:
        return None
