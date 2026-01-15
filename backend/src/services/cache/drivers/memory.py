import time
from typing import Any, Optional, Dict, Tuple
from ..abstraction import CacheBackend

class MemoryDriver(CacheBackend):
    def __init__(self, prefix: str = ""):
        # Store as key -> (value, expiry_timestamp)
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._prefix = prefix

    def _make_key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    async def get(self, key: str) -> Optional[Any]:
        full_key = self._make_key(key)
        if full_key not in self._store:
            return None
        
        value, expiry = self._store[full_key]
        if time.time() > expiry:
            del self._store[full_key]
            return None
            
        return value

    async def set(self, key: str, value: Any, expire: int = 60) -> None:
        full_key = self._make_key(key)
        expiry = time.time() + expire
        self._store[full_key] = (value, expiry)

    async def delete(self, key: str) -> None:
        full_key = self._make_key(key)
        if full_key in self._store:
            del self._store[full_key]

    async def exists(self, key: str) -> bool:
        full_key = self._make_key(key)
        if full_key not in self._store:
            return False
            
        _, expiry = self._store[key]
        if time.time() > expiry:
            del self._store[key]
            return False
            
        return True
