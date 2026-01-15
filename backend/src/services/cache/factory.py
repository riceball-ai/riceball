from functools import lru_cache
from src.config import Settings
from .abstraction import CacheBackend
from .drivers.memory import MemoryDriver
from .drivers.redis import RedisDriver

@lru_cache()
def get_cache_service() -> CacheBackend:
    settings = Settings()
    
    if settings.CACHE_DRIVER == "redis":
        if not settings.REDIS_URL:
            # Fallback or error? For now, let's error if configured but missing URL, or fallback.
            # But let's stick to the plan: use RedisDriver if configured.
            return RedisDriver(settings.REDIS_URL, prefix=settings.CACHE_PREFIX)
        return RedisDriver(settings.REDIS_URL, prefix=settings.CACHE_PREFIX)
        
    return MemoryDriver(prefix=settings.CACHE_PREFIX)
