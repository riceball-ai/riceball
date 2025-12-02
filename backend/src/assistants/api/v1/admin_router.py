import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_pagination import Page, Params
from fastapi_pagination.ext.sqlalchemy import paginate as sqlalchemy_paginate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from src.database import get_async_session
from src.auth import current_active_user
from src.users.models import User
from src.assistants.models import Assistant, Conversation
from src.ai_models.models import Model
from src.rag.models import KnowledgeBase
from src.agents.tools.registry import LocalToolRegistry
from .schemas import (
    AssistantCreate,
    AssistantUpdate,
    AssistantResponse,
    AssistantStatusEnum,
    AssistantTranslationsResponse,
    UpdateTranslationRequest,
)

router = APIRouter()

SORTABLE_FIELDS = {
    "name": Assistant.name,
    "status": Assistant.status,
    "created_at": Assistant.created_at,
    "updated_at": Assistant.updated_at,
}

DEFAULT_SORT_FIELD = "updated_at"
DEFAULT_SORT_DESC = True


# Tool listing schemas
class LocalToolInfo(BaseModel):
    name: str
    description: str


class MCPServerInfo(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None


class AvailableToolsResponse(BaseModel):
    local_tools: List[LocalToolInfo]
    mcp_servers: List[MCPServerInfo]


@router.get("/assistants", response_model=Page[AssistantResponse], summary="List assistants")
async def list_assistants(
    status: Optional[AssistantStatusEnum] = Query(None, description="Filter by status"),
    is_public: Optional[bool] = Query(None, description="Filter by public/private"),
    search: Optional[str] = Query(None, description="Search in name or description"),
    category: Optional[str] = Query(None, description="Filter by category"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    sort_by: Optional[str] = Query(None, description="Sort field: name, status, created_at, updated_at"),
    sort_desc: Optional[bool] = Query(None, description="Sort descending if true"),
    params: Params = Depends(),
    session: AsyncSession = Depends(get_async_session),
):
    """List assistants with filtering"""
    query = select(Assistant).options(
        selectinload(Assistant.model),
        selectinload(Assistant.owner)
    )
    
    # Apply filters
    if status:
        query = query.where(Assistant.status == status)
    
    if is_public is not None:
        query = query.where(Assistant.is_public == is_public)
    
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

    sort_field_key = sort_by if sort_by in SORTABLE_FIELDS else DEFAULT_SORT_FIELD
    if sort_desc is None:
        sort_desc_value = DEFAULT_SORT_DESC if sort_by not in SORTABLE_FIELDS else False
    else:
        sort_desc_value = sort_desc

    order_column = SORTABLE_FIELDS[sort_field_key]
    order_clause = order_column.desc() if sort_desc_value else order_column.asc()
    query = query.order_by(order_clause, Assistant.id.desc())
    
    # Get paginated results
    page_result = await sqlalchemy_paginate(session, query, params)
    
    # Create new page result with enriched items
    return Page(
        items=page_result.items,
        total=page_result.total,
        page=page_result.page,
        size=page_result.size,
        pages=page_result.pages
    )


@router.post("/assistants", response_model=AssistantResponse, summary="Create a new assistant")
async def create_assistant(
    assistant_data: AssistantCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
):
    """Create a new assistant"""
    from src.agents.models import MCPServerConfig
    
    # Check if model exists and is active
    model_result = await session.execute(
        select(Model).where(
            (Model.id == assistant_data.model_id) & 
            (Model.status == "ACTIVE")
        )
    )
    if not model_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Model not found or not active")

    knowledge_base_ids = assistant_data.knowledge_base_ids

    if len(knowledge_base_ids) != len(set(knowledge_base_ids)):
        raise HTTPException(status_code=400, detail="Duplicate knowledge base IDs provided")

    if knowledge_base_ids:
        kb_result = await session.execute(
            select(KnowledgeBase.id).where(
                KnowledgeBase.id.in_(knowledge_base_ids),
                KnowledgeBase.owner_id == current_user.id,
                KnowledgeBase.status == "ACTIVE"
            )
        )
        valid_ids = set(kb_result.scalars().all())
        missing_ids = set(knowledge_base_ids) - valid_ids
        if missing_ids:
            raise HTTPException(status_code=400, detail="Knowledge base not found or not accessible")

    # Validate MCP server IDs
    mcp_server_ids = assistant_data.mcp_server_ids or []
    mcp_servers = []
    if mcp_server_ids:
        if len(mcp_server_ids) != len(set(mcp_server_ids)):
            raise HTTPException(status_code=400, detail="Duplicate MCP server IDs provided")
        
        mcp_result = await session.execute(
            select(MCPServerConfig).where(
                MCPServerConfig.id.in_(mcp_server_ids),
                MCPServerConfig.is_active.is_(True)
            )
        )
        mcp_servers = list(mcp_result.scalars().all())
        found_ids = {mcp.id for mcp in mcp_servers}
        missing_ids = set(mcp_server_ids) - found_ids
        if missing_ids:
            raise HTTPException(status_code=400, detail="MCP server not found or not active")

    assistant_payload = assistant_data.model_dump(exclude={"knowledge_base_ids", "mcp_server_ids"})
    assistant = Assistant(
        **assistant_payload,
        owner_id=current_user.id
    )

    assistant.knowledge_base_ids = [str(kb_id) for kb_id in knowledge_base_ids]
    assistant.mcp_servers = mcp_servers

    session.add(assistant)
    await session.commit()

    result = await session.execute(
        select(Assistant)
        .options(
            selectinload(Assistant.model),
            selectinload(Assistant.owner),
            selectinload(Assistant.mcp_servers)
        )
        .where(Assistant.id == assistant.id)
    )
    assistant = result.scalar_one()

    return assistant


@router.get("/assistants/{assistant_id}", response_model=AssistantResponse, summary="Get an assistant")
async def get_assistant(
    assistant_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
):
    """Get a specific assistant by ID"""
    result = await session.execute(
        select(Assistant)
        .options(
            selectinload(Assistant.model),
            selectinload(Assistant.owner),
            selectinload(Assistant.mcp_servers)
        )
        .where(Assistant.id == assistant_id)
    )
    assistant = result.scalar_one_or_none()
    
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    
    # Check permissions: owner or public assistant
    if assistant.owner_id != current_user.id and not assistant.is_public:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return assistant


@router.put("/assistants/{assistant_id}", response_model=AssistantResponse, summary="Update an assistant")
async def update_assistant(
    assistant_id: uuid.UUID,
    assistant_data: AssistantUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
):
    """Update an assistant"""
    from src.agents.models import MCPServerConfig
    
    result = await session.execute(
        select(Assistant)
        .options(
            selectinload(Assistant.model),
            selectinload(Assistant.owner),
            selectinload(Assistant.mcp_servers)
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
    knowledge_base_ids = update_data.pop("knowledge_base_ids", None)
    mcp_server_ids = update_data.pop("mcp_server_ids", None)

    # Update primitive fields
    for field, value in update_data.items():
        setattr(assistant, field, value)

    if knowledge_base_ids is not None:
        if len(knowledge_base_ids) != len(set(knowledge_base_ids)):
            raise HTTPException(status_code=400, detail="Duplicate knowledge base IDs provided")

        if knowledge_base_ids:
            kb_result = await session.execute(
                select(KnowledgeBase.id).where(
                    KnowledgeBase.id.in_(knowledge_base_ids),
                    KnowledgeBase.owner_id == current_user.id,
                    KnowledgeBase.status == "ACTIVE"
                )
            )
            valid_ids = set(kb_result.scalars().all())
            missing_ids = set(knowledge_base_ids) - valid_ids
            if missing_ids:
                raise HTTPException(status_code=400, detail="Knowledge base not found or not accessible")

        assistant.knowledge_base_ids = [str(kb_id) for kb_id in knowledge_base_ids]

    # Update MCP servers if provided
    if mcp_server_ids is not None:
        if len(mcp_server_ids) != len(set(mcp_server_ids)):
            raise HTTPException(status_code=400, detail="Duplicate MCP server IDs provided")
        
        if mcp_server_ids:
            mcp_result = await session.execute(
                select(MCPServerConfig).where(
                    MCPServerConfig.id.in_(mcp_server_ids),
                    MCPServerConfig.is_active.is_(True)
                )
            )
            mcp_servers = list(mcp_result.scalars().all())
            found_ids = {mcp.id for mcp in mcp_servers}
            missing_ids = set(mcp_server_ids) - found_ids
            if missing_ids:
                raise HTTPException(status_code=400, detail="MCP server not found or not active")
            assistant.mcp_servers = mcp_servers
        else:
            assistant.mcp_servers = []

    await session.commit()

    result = await session.execute(
        select(Assistant)
        .options(
            selectinload(Assistant.model),
            selectinload(Assistant.owner),
            selectinload(Assistant.mcp_servers)
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
    """Delete an assistant and all associated conversations"""
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


@router.get("/assistants/{assistant_id}/stats", summary="Get assistant statistics")
async def get_assistant_stats(
    assistant_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
):
    """Get statistics for an assistant"""
    # Check if assistant exists and user has access
    assistant_result = await session.execute(
        select(Assistant).where(Assistant.id == assistant_id)
    )
    assistant = assistant_result.scalar_one_or_none()
    
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    
    # Check permissions
    if assistant.owner_id != current_user.id and not assistant.is_public:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get conversation count
    conv_count_result = await session.execute(
        select(func.count(Conversation.id)).where(Conversation.assistant_id == assistant_id)
    )
    conversation_count = conv_count_result.scalar() or 0
    
    # Get active conversation count
    active_conv_result = await session.execute(
        select(func.count(Conversation.id)).where(
            and_(
                Conversation.assistant_id == assistant_id,
                Conversation.status == "ACTIVE"
            )
        )
    )
    active_conversations = active_conv_result.scalar() or 0
    
    return {
        "assistant_id": assistant_id,
        "total_conversations": conversation_count,
        "active_conversations": active_conversations,
        "status": assistant.status.value,
        "is_public": assistant.is_public,
        "created_at": assistant.created_at
    }

@router.get("/agent-tools/available", response_model=AvailableToolsResponse, summary="List available Agent tools")
async def get_available_agent_tools(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
):
    """
    Get all available tools (local + MCP) for Agent configuration.
    Local tools are added via agent_enabled_tools field (string array).
    MCP servers are added via mcp_server_ids field (UUID array).
    """
    from src.agents.models import MCPServerConfig
    
    # Get local tools with their descriptions
    local_tools_info = LocalToolRegistry.list_tools_with_info()
    local_tools = [
        LocalToolInfo(
            name=tool_info["name"],
            description=tool_info["description"]
        )
        for tool_info in local_tools_info
    ]
    
    # Get active MCP servers from database
    mcp_result = await session.execute(
        select(MCPServerConfig).where(MCPServerConfig.is_active.is_(True))
    )
    mcp_servers_data = mcp_result.scalars().all()
    
    mcp_servers = [
        MCPServerInfo(
            id=mcp_server.id,
            name=mcp_server.name,
            description=mcp_server.description
        )
        for mcp_server in mcp_servers_data
    ]
    
    return AvailableToolsResponse(
        local_tools=local_tools,
        mcp_servers=mcp_servers
    )


# Translation management endpoints
@router.get("/assistants/{assistant_id}/translations", response_model=AssistantTranslationsResponse, summary="Get assistant translations")
async def get_assistant_translations(
    assistant_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
):
    """Get assistant translations for translation management page"""
    assistant = await session.get(Assistant, assistant_id)
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    
    # Calculate translation progress for each locale
    translatable_fields = ['name', 'description', 'system_prompt']
    translation_progress = {}
    
    if assistant.translations:
        for locale, trans in assistant.translations.items():
            filled = sum(1 for field in translatable_fields if trans.get(field))
            translation_progress[locale] = int((filled / len(translatable_fields)) * 100)
    
    return AssistantTranslationsResponse(
        id=assistant.id,
        default_name=assistant.name,
        default_description=assistant.description,
        default_system_prompt=assistant.system_prompt,
        translations=assistant.translations or {},
        translation_progress=translation_progress
    )


@router.put("/assistants/{assistant_id}/translations/{locale}", summary="Update assistant translation for a locale")
async def update_assistant_translation(
    assistant_id: uuid.UUID,
    locale: str,
    translation_data: UpdateTranslationRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Update translation for a specific locale"""
    assistant = await session.get(Assistant, assistant_id)
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    
    # Initialize translations dict if needed
    if not assistant.translations:
        assistant.translations = {}
    
    # Update translation data
    locale_data = assistant.translations.get(locale, {})
    
    if translation_data.name is not None:
        locale_data['name'] = translation_data.name
    if translation_data.description is not None:
        locale_data['description'] = translation_data.description
    if translation_data.system_prompt is not None:
        locale_data['system_prompt'] = translation_data.system_prompt
    
    assistant.translations[locale] = locale_data
    
    # Mark as modified for SQLAlchemy to detect change
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(assistant, 'translations')
    
    await session.commit()
    
    return {"message": "Translation updated successfully", "locale": locale}


@router.delete("/assistants/{assistant_id}/translations/{locale}", summary="Delete assistant translation for a locale")
async def delete_assistant_translation(
    assistant_id: uuid.UUID,
    locale: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Delete translation for a specific locale"""
    assistant = await session.get(Assistant, assistant_id)
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    
    if assistant.translations and locale in assistant.translations:
        del assistant.translations[locale]
        
        # Mark as modified for SQLAlchemy to detect change
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(assistant, 'translations')
        
        await session.commit()
        return {"message": "Translation deleted successfully", "locale": locale}
    
    raise HTTPException(status_code=404, detail=f"Translation for locale '{locale}' not found")
