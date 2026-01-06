import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import Page, paginate
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.database import get_async_session
from src.auth import current_active_user
from src.users.models import User
from src.auth.api_key_service import ApiKeyService

router = APIRouter()

class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    prefix: str
    created_at: datetime
    last_used_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class ApiKeyCreateRequest(BaseModel):
    name: str

class ApiKeyCreateResponse(ApiKeyResponse):
    key: str # The raw key, only shown once

@router.get("/user/api-keys", response_model=Page[ApiKeyResponse])
async def list_api_keys(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    service = ApiKeyService(session)
    keys = await service.get_user_keys(user.id)
    return paginate(keys)

@router.post("/user/api-keys", response_model=ApiKeyCreateResponse)
async def create_api_key(
    request: ApiKeyCreateRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    service = ApiKeyService(session)
    api_key, raw_key = await service.create_api_key(user.id, request.name)
    
    # We construct response manually to include the raw key
    return ApiKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        prefix=api_key.prefix,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        key=raw_key
    )

@router.delete("/user/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    service = ApiKeyService(session)
    success = await service.delete_api_key(user.id, key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API Key not found")
