from typing import Any, Optional
import redis.asyncio as redis
from ..abstraction import CacheBackend

class RedisDriver(CacheBackend):
    def __init__(self, redis_url: str, prefix: str = ""):
        self._redis = redis.from_url(redis_url, decode_responses=True)
        self._prefix = prefix

    def _make_key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    async def get(self, key: str) -> Optional[Any]:
        return await self._redis.get(self._make_key(key))
    
    async def set(self, key: str, value: Any, expire: int = 60) -> None:
        # Convert value to string if necessary, though redis-py handles some types.
        # But for consistency with our abstraction, we expect primitives or strings here.
        # Complex objects should be handled via set_model or serialized before calling set.
        await self._redis.set(self._make_key(key), value, ex=expire)
    
    async def delete(self, key: str) -> None:
        await self._redis.delete(self._make_key(key))
    
    async def exists(self, key: str) -> bool:
        return await self._redis.exists(self._make_key(key)) > 0
