import secrets
import hashlib
import uuid
from typing import List, Optional, Tuple
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import APIKeyHeader

from src.database import get_async_session
from src.users.models import User
from .api_key_models import ApiKey

API_KEY_PREFIX = "sk-"
API_KEY_LENGTH = 48 # Random chars

def generate_api_key() -> Tuple[str, str]:
    """
    Generate a new API key.
    Returns (raw_key, hashed_key)
    """
    random_part = secrets.token_urlsafe(API_KEY_LENGTH)
    raw_key = f"{API_KEY_PREFIX}{random_part}"
    hashed_key = hash_key(raw_key)
    return raw_key, hashed_key

def hash_key(key: str) -> str:
    """Hash the API key for storage"""
    return hashlib.sha256(key.encode()).hexdigest()

class ApiKeyService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_api_key(self, user_id: uuid.UUID, name: str) -> Tuple[ApiKey, str]:
        """
        Create a new API key for the user.
        Returns (ApiKey, raw_key_string)
        """
        raw_key, hashed_key = generate_api_key()
        
        api_key = ApiKey(
            user_id=user_id,
            name=name,
            prefix=raw_key[:8] + "...",
            hashed_key=hashed_key
        )
        self.session.add(api_key)
        await self.session.commit()
        await self.session.refresh(api_key)
        return api_key, raw_key

    async def get_user_keys(self, user_id: uuid.UUID) -> List[ApiKey]:
        stmt = select(ApiKey).where(ApiKey.user_id == user_id, ApiKey.is_active == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_api_key(self, user_id: uuid.UUID, key_id: uuid.UUID) -> bool:
        stmt = select(ApiKey).where(ApiKey.user_id == user_id, ApiKey.id == key_id)
        result = await self.session.execute(stmt)
        key = result.scalar_one_or_none()
        if key:
            await self.session.delete(key)
            await self.session.commit()
            return True
        return False

    async def verify_key_and_get_user(self, raw_key: str) -> Optional[User]:
        if not raw_key.startswith(API_KEY_PREFIX):
            return None
            
        hashed = hash_key(raw_key)
        stmt = select(ApiKey).where(
            ApiKey.hashed_key == hashed,
            ApiKey.is_active == True
        ).options(selectinload(ApiKey.user))
        
        result = await self.session.execute(stmt)
        api_key_record = result.scalar_one_or_none()
        
        if api_key_record:
            # Update last used
            api_key_record.last_used_at = datetime.utcnow()
            await self.session.commit()
            
            return api_key_record.user
            
        return None

# Dependency
api_key_header_scheme = APIKeyHeader(name="Authorization", auto_error=False)

async def get_current_user_by_api_key(
    api_key_header: str = Security(api_key_header_scheme),
    session: AsyncSession = Depends(get_async_session)
) -> User:
    """
    Authenticate user via API Key.
    Supports "Bearer sk-..." or just "sk-..." in Authorization header.
    """
    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key"
        )
    
    # Handle "Bearer " prefix if present
    token = api_key_header
    if token.lower().startswith("bearer "):
        token = token[7:]
    
    service = ApiKeyService(session)
    user = await service.verify_key_and_get_user(token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    return user
