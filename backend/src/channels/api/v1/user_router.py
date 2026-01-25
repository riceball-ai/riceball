from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from src.database import get_async_session
from src.auth import current_active_user
from src.users.models import User
from src.channels.models import UserChannelBinding

router = APIRouter(prefix="/channel-bindings", tags=["Channel Bindings"])

class UserChannelBindingRead(BaseModel):
    id: uuid.UUID
    provider: str
    external_user_id: str
    # metadata is reserved keyword in python? no.
    metadata: dict = {}
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[UserChannelBindingRead])
async def list_my_bindings(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    List all channel bindings (external identities) for the current user.
    """
    query = select(UserChannelBinding).where(UserChannelBinding.user_id == user.id)
    result = await session.execute(query)
    # Return bindings
    return result.scalars().all()
