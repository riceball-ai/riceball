from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.auth import current_active_user, current_superuser
from src.users.models import User
from src.channels.schemas import ChannelRead, ChannelCreate, ChannelUpdate, ChannelProvider
from src.channels.service import ChannelService
from src.assistants.models import Assistant

router = APIRouter(prefix="/channels")

@router.post("", response_model=ChannelRead, status_code=status.HTTP_201_CREATED)
async def create_channel(
    channel_data: ChannelCreate,
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Create a new channel"""
    # Verify assistant ownership
    assistant = await session.get(Assistant, channel_data.assistant_id)
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
        
    if assistant.owner_id != current_user.id and not current_user.is_superuser:
         raise HTTPException(status_code=403, detail="Not authorized")

    service = ChannelService(session)
    return await service.create_channel(channel_data)

@router.get("/assistant/{assistant_id}", response_model=List[ChannelRead])
async def list_channels_by_assistant(
    assistant_id: uuid.UUID,
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """List channels for a specific assistant"""
    assistant = await session.get(Assistant, assistant_id)
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
        
    if assistant.owner_id != current_user.id and not current_user.is_superuser:
         raise HTTPException(status_code=403, detail="Not authorized")
         
    service = ChannelService(session)
    return await service.get_channels_by_assistant(assistant_id)

@router.get("/{channel_id}", response_model=ChannelRead)
async def get_channel(
    channel_id: uuid.UUID,
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    service = ChannelService(session)
    channel = await service.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
        
    # Check ownership via assistant
    assistant = await session.get(Assistant, channel.assistant_id)
    if assistant.owner_id != current_user.id and not current_user.is_superuser:
         raise HTTPException(status_code=403, detail="Not authorized")
         
    return channel

@router.put("/{channel_id}", response_model=ChannelRead)
async def update_channel(
    channel_id: uuid.UUID,
    channel_data: ChannelUpdate,
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    service = ChannelService(session)
    channel = await service.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
        
    assistant = await session.get(Assistant, channel.assistant_id)
    if assistant.owner_id != current_user.id and not current_user.is_superuser:
         raise HTTPException(status_code=403, detail="Not authorized")

    return await service.update_channel(channel_id, channel_data)

@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    channel_id: uuid.UUID,
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    service = ChannelService(session)
    channel = await service.get_channel(channel_id)
    if channel:
        assistant = await session.get(Assistant, channel.assistant_id)
        if assistant.owner_id != current_user.id and not current_user.is_superuser:
             raise HTTPException(status_code=403, detail="Not authorized")
        
        await service.delete_channel(channel_id)
