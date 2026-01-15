import time
from typing import Any, Optional, Dict, Tuple
from ..abstraction import CacheBackend

class MemoryDriver(CacheBackend):
    def __init__(self):
        # Store as key -> (value, expiry_timestamp)
        self._store: Dict[str, Tuple[Any, float]] = {}

    async def get(self, key: str) -> Optional[Any]:
        if key not in self._store:
            return None
        
        value, expiry = self._store[key]
        if time.time() > expiry:
            del self._store[key]
            return None
            
        return value

    async def set(self, key: str, value: Any, expire: int = 60) -> None:
        expiry = time.time() + expire
        self._store[key] = (value, expiry)

    async def delete(self, key: str) -> None:
        if key in self._store:
            del self._store[key]

    async def exists(self, key: str) -> bool:
        if key not in self._store:
            return False
            
        _, expiry = self._store[key]
        if time.time() > expiry:
            del self._store[key]
            return False
            
        return True
