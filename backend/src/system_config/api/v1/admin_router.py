from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from ...service import config_service
from .schemas import (
    ConfigCreate,
    ConfigUpdate,
    ConfigResponse,
    ConfigListResponse,
    ConfigBatchUpdate,
)


router = APIRouter()

# Admin configuration endpoints (requires superuser permissions)
@router.get("/config", response_model=ConfigListResponse, tags=["Configuration Management"])
async def get_all_configs(
    session: AsyncSession = Depends(get_async_session),
) -> ConfigListResponse:
    """
    Get all configuration items (admin only)
    """
    configs = await config_service.get_all_configs(session)
    config_responses = [ConfigResponse.model_validate(config) for config in configs]
    return ConfigListResponse(configs=config_responses, total=len(config_responses))


@router.get("/config/{key}", response_model=ConfigResponse, tags=["Configuration Management"])
async def get_config(
    key: str,
    session: AsyncSession = Depends(get_async_session),
) -> ConfigResponse:
    """
    Get specified configuration item (admin only)
    """
    config = await config_service.get_config(session, key)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration item '{key}' not found"
        )
    return ConfigResponse.model_validate(config)


@router.post("/config", response_model=ConfigResponse, tags=["Configuration Management"])
async def create_config(
    config_data: ConfigCreate,
    session: AsyncSession = Depends(get_async_session),
) -> ConfigResponse:
    """
    Create new configuration item (admin only)
    """
    try:
        config = await config_service.create_config(session, config_data)
        return ConfigResponse.model_validate(config)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/config/{key}", response_model=ConfigResponse, tags=["Configuration Management"])
async def update_config(
    key: str,
    config_data: ConfigUpdate,
    session: AsyncSession = Depends(get_async_session),
) -> ConfigResponse:
    """
    Update specified configuration item (admin only)
    """
    config = await config_service.update_config(session, key, config_data)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration item '{key}' not found"
        )
    return ConfigResponse.model_validate(config)


@router.delete("/config/{key}", tags=["Configuration Management"])
async def delete_config(
    key: str,
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, str]:
    """
    Delete specified configuration item (admin only)
    """
    success = await config_service.delete_config(session, key)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration item '{key}' not found"
        )
    return {"message": f"Configuration item '{key}' has been deleted"}


@router.post("/config/batch", response_model=ConfigListResponse, tags=["Configuration Management"])
async def batch_update_configs(
    batch_data: ConfigBatchUpdate,
    session: AsyncSession = Depends(get_async_session),
) -> ConfigListResponse:
    """
    Batch update configuration items (admin only)
    """
    configs = await config_service.batch_update_configs(session, batch_data.configs)
    config_responses = [ConfigResponse.model_validate(config) for config in configs]
    return ConfigListResponse(configs=config_responses, total=len(config_responses))


@router.post("/config/cache/clear", tags=["Configuration Management"])
async def clear_config_cache(
) -> Dict[str, str]:
    """
    Clear configuration cache (admin only)
    
    When configurations have issues, you can manually clear cache to force reload.
    """
    config_service.clear_cache()
    return {"message": "Configuration cache has been cleared"}