from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.database import get_async_session
from src.ai_models.models import Model, ModelStatusEnum
from .schemas import ModelResponse

router = APIRouter()

@router.get("/models", response_model=List[ModelResponse], summary="List active models")
async def list_active_models(
    session: AsyncSession = Depends(get_async_session)
):
    """List all active models available for users (Chat only)"""
    query = select(Model).options(selectinload(Model.provider))
    query = query.where(Model.status == ModelStatusEnum.ACTIVE)
    
    result = await session.execute(query)
    models = result.scalars().all()
    
    # Hard restriction: only return models with 'chat' capability
    filtered_models = [model for model in models if "chat" in model.capabilities]
    
    return filtered_models
