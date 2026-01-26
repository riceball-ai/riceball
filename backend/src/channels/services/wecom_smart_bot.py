import logging
import time
from typing import AsyncGenerator, Dict, Any, Optional

from src.channels.services.base import BaseChannelService
from src.channels.models import ChannelConfig

logger = logging.getLogger(__name__)

# Simple In-Memory Store for Stream Buffers
# Format: { stream_id: { "content": "", "finish": False, "updated_at": float } }
# TODO: Use Redis or DB for production multi-worker environments
_STREAM_STORE: Dict[str, Dict[str, Any]] = {}

def get_stream_state(stream_id: str) -> Optional[Dict[str, Any]]:
    return _STREAM_STORE.get(stream_id)

def create_stream_state(stream_id: str):
    _STREAM_STORE[stream_id] = {
        "content": "",
        "finish": False, 
        "updated_at": time.time()
    }

def append_stream_content(stream_id: str, chunk: str):
    if stream_id in _STREAM_STORE:
        _STREAM_STORE[stream_id]["content"] += chunk
        _STREAM_STORE[stream_id]["updated_at"] = time.time()

def finish_stream(stream_id: str):
    if stream_id in _STREAM_STORE:
        _STREAM_STORE[stream_id]["finish"] = True
        _STREAM_STORE[stream_id]["updated_at"] = time.time()

def cleanup_streams(ttl: int = 3600):
    now = time.time()
    to_remove = [k for k, v in _STREAM_STORE.items() if now - v["updated_at"] > ttl]
    for k in to_remove:
        del _STREAM_STORE[k]


class WecomSmartBotChannelService(BaseChannelService):
    """
    Service for WeCom Smart Bot (Active Push Side).
    Instead of calling HTTP API, we write to the shared Stream Store.
    The Client (WeCom) will poll via the Adapter (Passive Reply).
    """

    def __init__(self, channel: ChannelConfig):
        super().__init__(channel)

    async def send_text(self, target_id: str, text: str) -> None:
        """
        Write text to stream store as a single finished chunk.
        target_id: MUST be the stream_id in this context.
        """
        stream_id = target_id
        
        # Ensure stream exists (it should be created by Adapter)
        if not get_stream_state(stream_id):
            create_stream_state(stream_id)
            
        append_stream_content(stream_id, text)
        finish_stream(stream_id)


    async def send_stream(self, target_id: str, stream_generator: AsyncGenerator[str, None]) -> None:
        """
        Write stream to store.
        target_id: MUST be the stream_id.
        """
        stream_id = target_id
        
        # Ensure stream exists
        if not get_stream_state(stream_id):
            create_stream_state(stream_id)
            
        async for chunk in stream_generator:
            append_stream_content(stream_id, chunk)
            
        finish_stream(stream_id)
