import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_pagination import Page
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_, func, distinct
from sqlalchemy.orm import joinedload, selectinload

from src.database import get_async_session
from src.auth import current_active_user
from src.users.models import User
from src.assistants.models import Conversation, Message, Assistant, MessageTypeEnum
from src.chat.service import LangchainChatService
from .schemas import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    MessageResponse,
    DashboardStatsResponse,
    AdminMessageResponse
)

router = APIRouter()


# Conversation endpoints
@router.get("/conversations", response_model=Page[ConversationResponse], summary="List conversations")
async def list_conversations(
    assistant_id: Optional[uuid.UUID] = Query(None, description="Filter by assistant"),
    user_id: Optional[uuid.UUID] = Query(None, description="Filter by user"),
    status: Optional[str] = Query("ACTIVE", description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in title"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
):
    """List user's conversations with pagination and filtering"""
    
    query = select(Conversation).options(
        joinedload(Conversation.assistant),
        joinedload(Conversation.user)
    )
    
    # Apply filters
    if assistant_id:
        query = query.where(Conversation.assistant_id == assistant_id)
    
    if user_id:
        query = query.where(Conversation.user_id == user_id)
    
    if status:
        query = query.where(Conversation.status == status)
    
    if search:
        search_term = f"%{search}%"
        # Join Message explicitly to enable filtering on message content
        query = query.outerjoin(Message, Conversation.id == Message.conversation_id)
        query = query.where(
            or_(
                Conversation.title.ilike(search_term),
                Message.content.ilike(search_term)
            )
        )
        query = query.distinct()
    
    query = query.order_by(Conversation.updated_at.desc())
    
    # Get total count
    if search:
        # If searching, we need to count distinct conversations matching criteria
        count_query = select(func.count(distinct(Conversation.id))).select_from(Conversation)
        count_query = count_query.outerjoin(Message, Conversation.id == Message.conversation_id)
        
        search_term = f"%{search}%"
        count_query = count_query.where(
            or_(
                Conversation.title.ilike(search_term),
                Message.content.ilike(search_term)
            )
        )
    else:
        count_query = select(func.count()).select_from(Conversation)
        
    if assistant_id:
        count_query = count_query.where(Conversation.assistant_id == assistant_id)
    if user_id:
        count_query = count_query.where(Conversation.user_id == user_id)
    if status:
        count_query = count_query.where(Conversation.status == status)
    
    total_result = await session.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    query = query.limit(size).offset((page - 1) * size)
    
    # Execute query
    result = await session.execute(query)
    conversations = result.scalars().unique().all()
    
    # Enrich items with assistant names
    enriched_items = []
    for conversation in conversations:
        # Get assistant name - the assistant should be loaded via joinedload
        assistant_name = None
        if conversation.assistant:
            assistant_name = conversation.assistant.name
        
        # Get user info
        user_name = None
        user_email = None
        if conversation.user:
            user_name = conversation.user.name
            user_email = conversation.user.email
        
        # Convert to response dict and add assistant_name
        conv_dict = {
            'id': conversation.id,
            'title': conversation.title,
            'assistant_id': conversation.assistant_id,
            'user_id': conversation.user_id,
            'status': conversation.status,
            'last_message_at': conversation.last_message_at,
            'message_count': conversation.message_count,
            'extra_data': conversation.extra_data,
            'created_at': conversation.created_at,
            'updated_at': conversation.updated_at,
            'assistant_name': assistant_name,
            'user_name': user_name,
            'user_email': user_email
        }
        enriched_items.append(ConversationResponse(**conv_dict))
    
    # Calculate pages
    pages = (total + size - 1) // size if total > 0 else 0
    
    # Create page result
    return Page(
        items=enriched_items,
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.post("/conversations", response_model=ConversationResponse, summary="Create a new conversation")
async def create_conversation(
    conversation_data: ConversationCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
):
    """Create a new conversation with an assistant"""
    service = LangchainChatService(session)
    
    try:
        conversation = await service.create_conversation(
            assistant_id=conversation_data.assistant_id,
            user_id=current_user.id,
            title=conversation_data.title
        )
        return conversation
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse, summary="Get a conversation")
async def get_conversation(
    conversation_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
):
    """Get a specific conversation"""
    # Direct query to bypass user_id check for admin
    query = select(Conversation).options(
        joinedload(Conversation.assistant)
    ).where(Conversation.id == conversation_id)
    
    result = await session.execute(query)
    conversation = result.scalars().unique().one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Get assistant name
    assistant_name = conversation.assistant.name if conversation.assistant else None
    
    # Convert to response
    conv_dict = {
        'id': conversation.id,
        'title': conversation.title,
        'assistant_id': conversation.assistant_id,
        'user_id': conversation.user_id,
        'status': conversation.status,
        'last_message_at': conversation.last_message_at,
        'message_count': conversation.message_count,
        'extra_data': conversation.extra_data,
        'created_at': conversation.created_at,
        'updated_at': conversation.updated_at,
        'assistant_name': assistant_name
    }
    
    return ConversationResponse(**conv_dict)


@router.put("/conversations/{conversation_id}", response_model=ConversationResponse, summary="Update a conversation")
async def update_conversation(
    conversation_id: uuid.UUID,
    conversation_data: ConversationUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
):
    """Update a conversation"""
    service = LangchainChatService(session)
    conversation = await service.get_conversation(conversation_id, current_user.id)
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Update fields
    update_data = conversation_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(conversation, field, value)
    
    await session.commit()
    await session.refresh(conversation)
    return conversation


@router.delete("/conversations/{conversation_id}", summary="Delete a conversation")
async def delete_conversation(
    conversation_id: uuid.UUID,
    permanent: bool = Query(False, description="Permanently delete conversation"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
):
    """Delete a conversation"""
    service = LangchainChatService(session)
    
    if permanent:
        success = await service.hard_delete_conversation(conversation_id)
        message = "Conversation permanently deleted"
    else:
        success = await service.delete_conversation(conversation_id, current_user.id)
        message = "Conversation deleted successfully"
    
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {"message": message}


@router.get("/conversations/{conversation_id}/messages", response_model=Page[MessageResponse], summary="Get conversation messages")
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    limit: Optional[int] = Query(50, description="Number of messages to retrieve"),
    offset: Optional[int] = Query(0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
):
    """Get messages for a conversation"""
    # Direct query to bypass user_id check
    query = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc())
    
    if offset:
        query = query.offset(offset)
    if limit:
        query = query.limit(limit)
        
    result = await session.execute(query)
    messages = result.scalars().all()
    
    return {
        "items": messages,
        "total": len(messages),
        "page": offset // limit + 1 if limit else 1,
        "size": limit or len(messages),
        "pages": 1
    }


# Dashboard stats endpoint
@router.get("/dashboard/stats", response_model=DashboardStatsResponse, summary="Get dashboard statistics")
async def get_dashboard_stats(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
):
    """Get aggregated statistics for the admin dashboard"""
    from sqlalchemy import func, desc
    from datetime import datetime, timedelta
    
    # 1. Overview Metrics
    # Total Users
    total_users_result = await session.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar() or 0
    
    # Total Token Usage - REMOVED: Billing system no longer exists
    total_token_usage = 0
    
    # Total Conversations
    total_conv_result = await session.execute(select(func.count(Conversation.id)))
    total_conversations = total_conv_result.scalar() or 0

    # Total Feedback (Like/Dislike)
    feedback_stats_query = (
        select(Message.feedback, func.count(Message.id))
        .where(Message.feedback.is_not(None))
        .group_by(Message.feedback)
    )
    feedback_stats_result = await session.execute(feedback_stats_query)
    feedback_stats = {row[0]: row[1] for row in feedback_stats_result.all()}
    
    total_feedback_like = feedback_stats.get('like', 0)
    total_feedback_dislike = feedback_stats.get('dislike', 0)
    
    # 2. Charts Data (Last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    # User Growth (Daily)
    # Note: SQLite doesn't support date_trunc, using strftime for compatibility if needed, 
    # but assuming Postgres for production. For now using generic approach or assuming Postgres.
    # Using func.date() which works in both SQLite and Postgres (mostly)
    user_growth_query = (
        select(
            func.date(User.created_at).label('date'),
            func.count(User.id).label('count')
        )
        .where(User.created_at >= thirty_days_ago)
        .group_by(func.date(User.created_at))
        .order_by('date')
    )
    user_growth_result = await session.execute(user_growth_query)
    user_growth = [
        {"name": str(row.date), "value": row.count} 
        for row in user_growth_result.all()
    ]
    
    # 3. Lists
    # Top Assistants (by conversation count)
    top_assistants_query = (
        select(
            Assistant.name,
            func.count(Conversation.id).label('conv_count')
        )
        .join(Conversation, Conversation.assistant_id == Assistant.id)
        .group_by(Assistant.id, Assistant.name)
        .order_by(desc('conv_count'))
        .limit(5)
    )
    top_assistants_result = await session.execute(top_assistants_query)
    top_assistants = [
        {"name": row.name, "count": row.conv_count}
        for row in top_assistants_result.all()
    ]
    
    # Recent Users
    recent_users_query = (
        select(User)
        .order_by(User.created_at.desc())
        .limit(5)
    )
    recent_users_result = await session.execute(recent_users_query)
    recent_users = [
        {
            "email": user.email,
            "name": user.name,
            "created_at": user.created_at,
            "avatar_url": user.avatar_url
        }
        for user in recent_users_result.scalars().all()
    ]
    
    return DashboardStatsResponse(
        overview={
            "total_users": total_users,
            "total_token_usage": total_token_usage,
            "total_conversations": total_conversations,
            "total_feedback_like": total_feedback_like,
            "total_feedback_dislike": total_feedback_dislike
        },
        user_growth=user_growth,
        top_assistants=top_assistants,
        recent_users=recent_users
    )

# --- Feedback / Messages Review ---
@router.get("/messages", response_model=Page[AdminMessageResponse], summary="List chat messages for review")
async def list_messages(
    feedback: Optional[str] = Query(None, description="Filter by feedback (like/dislike)"),
    assistant_id: Optional[uuid.UUID] = Query(None, description="Filter by assistant"),
    search: Optional[str] = Query(None, description="Search in content"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
):
    """
    List messages for admin review.
    Focuses on assistant messages, optionally filtered by feedback.
    Includes the previous message as context.
    """
    from fastapi_pagination.ext.sqlalchemy import paginate as sqlalchemy_paginate
    
    query = (
        select(Message)
        .join(Message.conversation)
        .join(Conversation.assistant)
        .outerjoin(Conversation.user)
        .where(Message.message_type == MessageTypeEnum.ASSISTANT)
        .options(
            selectinload(Message.conversation).selectinload(Conversation.assistant),
            selectinload(Message.conversation).selectinload(Conversation.user),
            selectinload(Message.user)
        )
        .order_by(desc(Message.created_at))
    )
    
    if feedback:
        query = query.where(Message.feedback == feedback)
    
    if assistant_id:
        query = query.where(Conversation.assistant_id == assistant_id)
        
    if search:
        query = query.where(Message.content.ilike(f"%{search}%"))

    # Execute main query with pagination limits manually
    # We do this to avoid early validation against response_model by fastapi-pagination
    from sqlalchemy import func
    
    # 1. Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_res = await session.execute(count_query)
    total = total_res.scalar() or 0
    
    # 2. Apply Limit/Offset
    query = query.offset((page - 1) * size).limit(size)
    result = await session.execute(query)
    messages = result.scalars().all()
    
    # Then process items
    processed_items = []
    
    for msg in messages:
        # Context: Previous message
        context_query = (
            select(Message)
            .where(Message.conversation_id == msg.conversation_id)
            .where(Message.created_at < msg.created_at)
            .order_by(desc(Message.created_at))
            .limit(1)
        )
        context_res = await session.execute(context_query)
        prev_msg = context_res.scalar_one_or_none()
        
        context_data = None
        if prev_msg:
            context_data = {
                "id": str(prev_msg.id),
                "content": prev_msg.content,
                "role": prev_msg.message_type.value,
                "created_at": prev_msg.created_at
            }
            
        # User info from conversation if not in message
        conversation_user = None
        if msg.conversation and msg.conversation.user:
            conversation_user = msg.conversation.user
            
        user_id = msg.user_id or (conversation_user.id if conversation_user else None)
        user_email = (msg.user.email if msg.user else (conversation_user.email if conversation_user else None))
        
        item = AdminMessageResponse(
            id=msg.id,
            content=msg.content,
            message_type=msg.message_type,
            feedback=msg.feedback,
            created_at=msg.created_at,
            conversation_id=msg.conversation_id,
            assistant_id=msg.conversation.assistant.id,
            assistant_name=msg.conversation.assistant.name,
            user_id=user_id,
            user_email=user_email,
            context_message=context_data,
            extra_data=msg.extra_data
        )
        processed_items.append(item)

    # Replace items
    # Create a new Page instance instead of mutating result_page to ensure validation works
    from fastapi_pagination import Page as PageModel
    return PageModel(
        items=processed_items,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )
