import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.database import get_async_session
from src.auth import current_active_user, current_active_user_optional
from src.users.models import User
from src.assistants.models import Assistant, AssistantStatusEnum, PinnedAssistant
from src.ai_models.models import Model
from src.system_config.service import config_service
from .schemas import (
    AssistantResponse,
    AssistantCreate,
    AssistantUpdate,
)

router = APIRouter()


async def _fetch_assistant(
    assistant_id: uuid.UUID,
    session: AsyncSession,
):
    result = await session.execute(
        select(Assistant)
        .options(
            selectinload(Assistant.model),
            selectinload(Assistant.owner)
        )
        .where(Assistant.id == assistant_id)
    )
    return result.scalar_one_or_none()

@router.get("/assistants", response_model=list[AssistantResponse], summary="List assistants")
async def list_assistants(
    search: Optional[str] = Query(None, description="Search in name or description"),
    category: Optional[str] = Query(None, description="Filter by category"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    scope: Optional[str] = Query(None, description="Filter scope: 'mine' or 'public'"),
    sort_by: Optional[str] = Query("created_at", description="Sort field: created_at, updated_at, name, usage_count"),
    order: Optional[str] = Query("desc", description="Sort order: asc or desc"),
    session: AsyncSession = Depends(get_async_session),
    current_user: Optional[User] = Depends(current_active_user_optional),
):
    """List assistants with filtering and sorting"""
    # Base query: Public active assistants OR My assistants (active)
    # Note: We might want to show user's own drafts too?
    # For now, let's stick to the original logic but allow users to see their own assistants
    
    query = select(Assistant).options(
        selectinload(Assistant.model),
        selectinload(Assistant.owner)
    )
    
    if current_user:
        if scope == 'mine':
            # Only my assistants (any status)
            query = query.where(Assistant.owner_id == current_user.id)
        elif scope == 'pinned':
            # Only pinned assistants
            query = query.join(PinnedAssistant).where(PinnedAssistant.user_id == current_user.id)
        elif scope == 'public':
            # Only public active assistants
            query = query.where(
                (Assistant.is_public == True) & 
                (Assistant.status == AssistantStatusEnum.ACTIVE)
            )
        else:
            # Default: Public active OR My assistants
            query = query.where(
                (
                    (Assistant.is_public == True) & 
                    (Assistant.status == AssistantStatusEnum.ACTIVE)
                ) | 
                (Assistant.owner_id == current_user.id)
            )
    else:
        # If not logged in
        if scope == 'mine' or scope == 'pinned':
            raise HTTPException(status_code=401, detail="Authentication required to view your assistants")
            
        # Show public active only
        query = query.where(Assistant.is_public.is_(True)).where(Assistant.status == AssistantStatusEnum.ACTIVE)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            (Assistant.name.ilike(search_term)) |
            (Assistant.description.ilike(search_term))
        )
    
    if category:
        query = query.where(Assistant.category == category)
        
    if tags:
        for tag in tags:
             query = query.where(Assistant.tags.contains([tag]))
    
    # Apply sorting
    allowed_sort_fields = {
        "created_at": Assistant.created_at,
        "updated_at": Assistant.updated_at,
        "name": Assistant.name,
        "usage_count": Assistant.usage_count,
    }
    
    # Validate sort_by parameter
    if sort_by not in allowed_sort_fields:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid sort_by field. Allowed values: {', '.join(allowed_sort_fields.keys())}"
        )
    
    # Validate order parameter
    if order not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Invalid order. Allowed values: asc, desc")
    
    # Apply sorting to query
    sort_field = allowed_sort_fields[sort_by]
    if order == "desc":
        query = query.order_by(sort_field.desc())
    else:
        query = query.order_by(sort_field.asc())
    
    result = await session.execute(query)
    assistants = result.scalars().all()
    
    # Populate is_pinned if user is logged in
    if current_user:
        pinned_result = await session.execute(
            select(PinnedAssistant.assistant_id)
            .where(PinnedAssistant.user_id == current_user.id)
        )
        pinned_ids = set(pinned_result.scalars().all())
        
        for assistant in assistants:
            assistant.is_pinned = assistant.id in pinned_ids
            
    return assistants


@router.post("/assistants", response_model=AssistantResponse, summary="Create a new assistant")
async def create_assistant(
    assistant_data: AssistantCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
):
    """Create a new assistant"""
    # Check if user creation is allowed
    allow_create = await config_service.get_config_value(session, "allow_user_create_assistants", default=True)
    
    # Handle string "false" if stored as such (e.g. from JSON serialization of boolean)
    if isinstance(allow_create, str) and allow_create.lower() == "false":
        allow_create = False
        
    if not allow_create and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Assistant creation is disabled by administrator")

    # Check if model exists and is active
    model_result = await session.execute(
        select(Model).where(
            (Model.id == assistant_data.model_id) & 
            (Model.status == "ACTIVE")
        )
    )
    if not model_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Model not found or not active")

    # For user creation, we ignore knowledge_base_ids and mcp_server_ids for now as requested
    # But if they are passed, we should probably validate or just strip them if we want to enforce "simple"
    # The prompt said "Agent and RAG temporarily not supported", so we can just ignore them or ensure they are empty.
    # Let's just process them normally but the frontend won't send them.
    
    assistant_payload = assistant_data.model_dump(exclude={"knowledge_base_ids", "mcp_server_ids"})
    
    # Force status to ACTIVE or DRAFT? Let's use what's passed, defaulting to DRAFT in schema
    
    assistant = Assistant(
        **assistant_payload,
        owner_id=current_user.id
    )
    
    # Initialize empty lists for unsupported features
    assistant.knowledge_base_ids = []
    assistant.mcp_servers = []

    session.add(assistant)
    await session.commit()

    result = await session.execute(
        select(Assistant)
        .options(
            selectinload(Assistant.model),
            selectinload(Assistant.owner)
        )
        .where(Assistant.id == assistant.id)
    )
    assistant = result.scalar_one()

    return assistant


@router.put("/assistants/{assistant_id}", response_model=AssistantResponse, summary="Update an assistant")
async def update_assistant(
    assistant_id: uuid.UUID,
    assistant_data: AssistantUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
):
    """Update an assistant"""
    result = await session.execute(
        select(Assistant)
        .options(
            selectinload(Assistant.model),
            selectinload(Assistant.owner)
        )
        .where(Assistant.id == assistant_id)
    )
    assistant = result.scalar_one_or_none()
    
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    
    # Check permissions: only owner can update
    if assistant.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can update assistant")
    
    # Check if model exists and is active if model_id is being updated
    if assistant_data.model_id and assistant_data.model_id != assistant.model_id:
        model_result = await session.execute(
            select(Model).where(
                (Model.id == assistant_data.model_id) &
                (Model.status == "ACTIVE")
            )
        )
        if not model_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Model not found or not active")
    
    update_data = assistant_data.model_dump(exclude_unset=True)
    
    # Remove complex fields if they are present (since we don't support them in user update yet)
    update_data.pop("knowledge_base_ids", None)
    update_data.pop("mcp_server_ids", None)

    # Update primitive fields
    for field, value in update_data.items():
        setattr(assistant, field, value)

    await session.commit()

    result = await session.execute(
        select(Assistant)
        .options(
            selectinload(Assistant.model),
            selectinload(Assistant.owner)
        )
        .where(Assistant.id == assistant_id)
    )
    assistant = result.scalar_one()

    return assistant


@router.delete("/assistants/{assistant_id}", summary="Delete an assistant")
async def delete_assistant(
    assistant_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
):
    """Delete an assistant"""
    result = await session.execute(
        select(Assistant).where(Assistant.id == assistant_id)
    )
    assistant = result.scalar_one_or_none()
    
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    
    # Check permissions: only owner can delete
    if assistant.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can delete assistant")
    
    await session.delete(assistant)
    await session.commit()
    return {"message": "Assistant deleted successfully"}


@router.get("/assistants/{assistant_id}", response_model=AssistantResponse, summary="Get assistant detail")
async def get_assistant(
    assistant_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: Optional[User] = Depends(current_active_user_optional),
):
    """Get assistant detail"""
    assistant = await _fetch_assistant(assistant_id, session)
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
        
    # Check permissions
    # If public and active -> OK
    # If owner -> OK
    # Otherwise -> 403
    
    is_owner = current_user and assistant.owner_id == current_user.id
    is_public_active = assistant.is_public and assistant.status == AssistantStatusEnum.ACTIVE
    
    if not (is_owner or is_public_active):
        raise HTTPException(status_code=403, detail="Access denied")
        
    # Populate is_pinned
    if current_user:
        pinned_result = await session.execute(
            select(PinnedAssistant)
            .where(
                (PinnedAssistant.user_id == current_user.id) &
                (PinnedAssistant.assistant_id == assistant_id)
            )
        )
        assistant.is_pinned = pinned_result.scalar_one_or_none() is not None
    else:
        assistant.is_pinned = False

    return assistant


@router.post("/assistants/{assistant_id}/pin", summary="Pin an assistant")
async def pin_assistant(
    assistant_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
):
    """Pin an assistant for the current user"""
    # Check if assistant exists
    assistant = await session.get(Assistant, assistant_id)
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
        
    # Check if already pinned
    existing_pin = await session.execute(
        select(PinnedAssistant).where(
            (PinnedAssistant.user_id == current_user.id) &
            (PinnedAssistant.assistant_id == assistant_id)
        )
    )
    if existing_pin.scalar_one_or_none():
        return {"message": "Assistant already pinned"}
        
    # Create pin
    pin = PinnedAssistant(user_id=current_user.id, assistant_id=assistant_id)
    session.add(pin)
    await session.commit()
    
    return {"message": "Assistant pinned successfully"}


@router.delete("/assistants/{assistant_id}/pin", summary="Unpin an assistant")
async def unpin_assistant(
    assistant_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
):
    """Unpin an assistant for the current user"""
    result = await session.execute(
        select(PinnedAssistant).where(
            (PinnedAssistant.user_id == current_user.id) &
            (PinnedAssistant.assistant_id == assistant_id)
        )
    )
    pin = result.scalar_one_or_none()
    
    if not pin:
        raise HTTPException(status_code=404, detail="Assistant not pinned")
        
    await session.delete(pin)
    await session.commit()
    
    return {"message": "Assistant unpinned successfully"}
