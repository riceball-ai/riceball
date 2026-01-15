from typing import Any, Optional
import redis.asyncio as redis
from ..abstraction import CacheBackend

class RedisDriver(CacheBackend):
    def __init__(self, redis_url: str):
        self._redis = redis.from_url(redis_url, decode_responses=True)

    async def get(self, key: str) -> Optional[Any]:
        return await self._redis.get(key)
    
    async def set(self, key: str, value: Any, expire: int = 60) -> None:
        # Convert value to string if necessary, though redis-py handles some types.
        # But for consistency with our abstraction, we expect primitives or strings here.
        # Complex objects should be handled via set_model or serialized before calling set.
        await self._redis.set(key, value, ex=expire)
    
    async def delete(self, key: str) -> None:
        await self._redis.delete(key)
    
    async def exists(self, key: str) -> bool:
        return await self._redis.exists(key) > 0
