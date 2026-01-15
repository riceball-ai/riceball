from abc import ABC, abstractmethod
from typing import Any, Optional, Type, TypeVar
import json

T = TypeVar("T")

class CacheBackend(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]: 
        """Get a value by key."""
        ...
    
    @abstractmethod
    async def set(self, key: str, value: Any, expire: int = 60) -> None: 
        """Set a value by key with an optional expiration time in seconds."""
        ...
    
    @abstractmethod
    async def delete(self, key: str) -> None: 
        """Delete a key."""
        ...
    
    @abstractmethod
    async def exists(self, key: str) -> bool: 
        """Check if a key exists."""
        ...
    
    # Advanced features: Support direct Pydantic model storage
    async def get_model(self, key: str, model: Type[T]) -> Optional[T]:
        """
        Get a Pydantic model from cache.
        Assumes the value is stored as a JSON string or dict.
        """
        data = await self.get(key)
        if data is None:
            return None
        
        if isinstance(data, str):
            try:
                # Try to load as JSON if it's a string
                data = json.loads(data)
            except json.JSONDecodeError:
                return None
                
        if isinstance(data, dict):
            return model.model_validate(data)
            
        return None

    async def set_model(self, key: str, value: Any, expire: int = 60) -> None:
        """
        Set a Pydantic model to cache.
        """
        if hasattr(value, "model_dump_json"):
            # Pydantic v2
            json_str = value.model_dump_json()
        elif hasattr(value, "json"):
            # Pydantic v1
            json_str = value.json()
        else:
            # Fallback to json dump
            json_str = json.dumps(value)
            
        await self.set(key, json_str, expire=expire)
