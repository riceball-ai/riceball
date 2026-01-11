import asyncio
from typing import Dict, Any, Optional
import time

class StreamBuffer:
    _instance = None
    _store: Dict[str, Dict[str, Any]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StreamBuffer, cls).__new__(cls)
        return cls._instance

    async def init_stream(self, stream_id: str):
        self._store[stream_id] = {
            "content": "",
            "finished": False,
            "created_at": time.time()
        }

    async def append_content(self, stream_id: str, content: str):
        if stream_id in self._store:
            self._store[stream_id]["content"] += content

    async def set_content(self, stream_id: str, content: str):
        if stream_id in self._store:
            self._store[stream_id]["content"] = content

    async def mark_finished(self, stream_id: str):
        if stream_id in self._store:
            self._store[stream_id]["finished"] = True

    async def get_state(self, stream_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get(stream_id)

    async def cleanup(self, ttl: int = 3600):
        # Todo: Implement cleanup logic
        pass

stream_buffer = StreamBuffer()
