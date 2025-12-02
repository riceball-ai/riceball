from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from ...service import config_service
from .schemas import (
    PublicConfigsResponse,
)


router = APIRouter()


# Public configuration endpoints (no authentication required)
@router.get("/config/public", response_model=PublicConfigsResponse)
async def get_public_configs(
    session: AsyncSession = Depends(get_async_session)
) -> PublicConfigsResponse:
    """
    Get all public configurations
    
    Frontend can call this endpoint to get system's public configurations,
    such as whether registration is enabled, etc.
    """
    configs = await config_service.get_public_configs(session)
    return PublicConfigsResponse(configs=configs)