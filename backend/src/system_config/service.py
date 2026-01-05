import json
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError

from .models import SystemConfig
from .api.v1.schemas import ConfigCreate, ConfigUpdate


class ConfigCache:
    """Simple in-memory cache class for public configurations"""
    
    def __init__(self):
        self._public_cache: Dict[str, Any] = {}
    
    def get_public_configs(self) -> Dict[str, Any]:
        """Get all public configurations cache"""
        return self._public_cache.copy()
    
    def set_public_configs(self, configs: Dict[str, Any]) -> None:
        """Set public configurations cache"""
        self._public_cache = configs.copy()
    
    def clear(self) -> None:
        """Clear all cache"""
        self._public_cache.clear()


class ConfigService:
    """Configuration management service"""
    
    def __init__(self):
        self.cache = ConfigCache()
    
    async def get_config(self, session: AsyncSession, key: str) -> Optional[SystemConfig]:
        """Get single configuration item"""
        result = await session.execute(
            select(SystemConfig).where(
                SystemConfig.key == key,
                SystemConfig.is_enabled
            )
        )
        return result.scalar_one_or_none()
    
    async def get_config_value(self, session: AsyncSession, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        config = await self.get_config(session, key)
        return config.get_value() if config else default
    
    async def get_all_configs(self, session: AsyncSession) -> List[SystemConfig]:
        """Get all configuration items"""
        result = await session.execute(
            select(SystemConfig).order_by(SystemConfig.key)
        )
        return result.scalars().all()
    
    async def get_public_configs(self, session: AsyncSession) -> Dict[str, Any]:
        """Get all public configurations"""
        # Try to get from cache first
        cached_configs = self.cache.get_public_configs()
        if cached_configs:
            return cached_configs
        
        # Get from database
        result = await session.execute(
            select(SystemConfig).where(
                SystemConfig.is_public,
                SystemConfig.is_enabled
            )
        )
        configs = result.scalars().all()
        
        # Build configuration dictionary
        config_dict = {config.key: config.get_value() for config in configs}
        
        # Update cache
        self.cache.set_public_configs(config_dict)
        
        return config_dict
    
    async def create_config(self, session: AsyncSession, config_data: ConfigCreate) -> SystemConfig:
        """Create configuration item"""
        try:
            config = SystemConfig(
                key=config_data.key,
                description=config_data.description,
                is_public=config_data.is_public,
                is_enabled=config_data.is_enabled,
                config_type=config_data.config_type,
                config_group=config_data.config_group,
                label=config_data.label,
                options=config_data.options
            )
            config.set_value(config_data.value)
            
            session.add(config)
            await session.commit()
            await session.refresh(config)
            
            # Clear public config cache to force reload if this is a public config
            if config.is_public:
                self.cache.clear()
            
            return config
            
        except IntegrityError:
            await session.rollback()
            raise ValueError(f"Configuration item '{config_data.key}' already exists")
    
    async def update_config(self, session: AsyncSession, key: str, config_data: ConfigUpdate) -> Optional[SystemConfig]:
        """Update configuration item"""
        # First get existing configuration
        config = await self.get_config(session, key)
        if not config:
            return None
        
        # Update fields
        update_data = {}
        if config_data.value is not None:
            if isinstance(config_data.value, str):
                update_data["value"] = config_data.value
            else:
                update_data["value"] = json.dumps(config_data.value, ensure_ascii=False)
        
        if config_data.description is not None:
            update_data["description"] = config_data.description
        
        if config_data.is_public is not None:
            update_data["is_public"] = config_data.is_public
        
        if config_data.is_enabled is not None:
            update_data["is_enabled"] = config_data.is_enabled
        
        if config_data.config_type is not None:
            update_data["config_type"] = config_data.config_type
            
        if config_data.config_group is not None:
            update_data["config_group"] = config_data.config_group
            
        if config_data.label is not None:
            update_data["label"] = config_data.label
            
        if config_data.options is not None:
            update_data["options"] = config_data.options
        
        if update_data:
            await session.execute(
                update(SystemConfig)
                .where(SystemConfig.key == key)
                .values(**update_data)
            )
            await session.commit()
            
            # Re-fetch updated configuration
            await session.refresh(config)
            
            # Clear public config cache to force reload
            self.cache.clear()
        
        return config
    
    async def delete_config(self, session: AsyncSession, key: str) -> bool:
        """Delete configuration item"""
        result = await session.execute(
            delete(SystemConfig).where(SystemConfig.key == key)
        )
        
        if result.rowcount > 0:
            await session.commit()
            # Clear public config cache to force reload
            self.cache.clear()
            return True
        
        return False
    
    async def batch_update_configs(self, session: AsyncSession, configs: Dict[str, Any]) -> List[SystemConfig]:
        """Batch update configuration items"""
        updated_configs = []
        
        for key, value in configs.items():
            config_data = ConfigUpdate(value=value)
            updated_config = await self.update_config(session, key, config_data)
            if updated_config:
                updated_configs.append(updated_config)
        
        return updated_configs
    
    def clear_cache(self) -> None:
        """Clear cache"""
        self.cache.clear()
    
    # Dedicated method for title generation model configuration
    async def get_title_generation_model_id(self, session: AsyncSession) -> Optional[str]:
        """Get title generation model ID"""
        return await self.get_config_value(session, "conversation_title_model_id", None)
    
    async def set_title_generation_model_id(self, session: AsyncSession, model_id: str) -> SystemConfig:
        """Set title generation model ID"""
        # Validate if it is a valid UUID format
        try:
            uuid.UUID(model_id)
        except ValueError:
            raise ValueError("Invalid model ID format")
        
        # Check if configuration already exists
        existing_config = await self.get_config(session, "conversation_title_model_id")
        
        if existing_config:
            # Update existing configuration
            config_data = ConfigUpdate(value=model_id)
            return await self.update_config(session, "conversation_title_model_id", config_data)
        else:
            # Create new configuration
            config_data = ConfigCreate(
                key="conversation_title_model_id",
                value=model_id,
                description="Model ID used for generating conversation titles",
                is_public=False,
                is_enabled=True
            )
            return await self.create_config(session, config_data)


# Global configuration service instance
config_service = ConfigService()