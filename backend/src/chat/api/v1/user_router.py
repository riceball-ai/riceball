"""
Chat API router
"""
import json
import uuid
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi_pagination import Page
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi_pagination.ext.sqlalchemy import paginate as sqlalchemy_paginate

from src.database import get_async_session
from src.auth import current_active_user
from src.users.models import User
from src.chat.service import LangchainChatService
from src.assistants.models import Conversation, Message

from .schemas import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    MessageResponse,
    GenerateTitleResponse,
    ChatRequest,
    MessageFeedbackRequest
)

router = APIRouter()
logger = logging.getLogger(__name__)



# Conversation endpoints
@router.get("/conversations", response_model=Page[ConversationResponse], summary="List conversations")
async def list_conversations(
    assistant_id: Optional[uuid.UUID] = Query(None, description="Filter by assistant"),
    status: Optional[str] = Query("ACTIVE", description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in title"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
):
    """List user's conversations with pagination and filtering"""
    query = select(Conversation).options(
        selectinload(Conversation.assistant)
    ).where(Conversation.user_id == current_user.id)
    
    # Apply filters
    if assistant_id:
        query = query.where(Conversation.assistant_id == assistant_id)
    
    if status:
        query = query.where(Conversation.status == status)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(Conversation.title.ilike(search_term))
    
    query = query.order_by(Conversation.updated_at.desc())
    
    return await sqlalchemy_paginate(session, query)


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


# Generate conversation title endpoint
@router.post("/conversations/{conversation_id}/generate-title", response_model=GenerateTitleResponse, summary="Generate conversation title")
async def generate_conversation_title(
    conversation_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
):
    """Generate a title for the conversation using AI with langchain"""
    service = LangchainChatService(session)
    
    try:
        title, model_used, updated = await service.generate_conversation_title(
            conversation_id=conversation_id,
            user_id=current_user.id
        )
        
        return GenerateTitleResponse(
            conversation_id=conversation_id,
            title=title,
            model_used=model_used,
            updated=updated
        )
        
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
    service = LangchainChatService(session)
    conversation = await service.get_conversation(conversation_id, current_user.id)
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return conversation


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
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
):
    """Delete a conversation"""
    service = LangchainChatService(session)
    success = await service.delete_conversation(conversation_id, current_user.id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {"message": "Conversation deleted successfully"}


@router.get("/conversations/{conversation_id}/messages", response_model=Page[MessageResponse], summary="Get conversation messages")
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    limit: Optional[int] = Query(50, description="Number of messages to retrieve"),
    offset: Optional[int] = Query(0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
):
    """Get messages for a conversation"""
    service = LangchainChatService(session)
    
    try:
        messages = await service.get_conversation_messages(
            conversation_id, current_user.id, limit, offset
        )
        return {
            "items": messages,
            "total": len(messages),
            "page": offset // limit + 1 if limit else 1,
            "size": limit or len(messages),
            "pages": 1
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# Chat endpoint for direct messaging with assistant (streaming by default)
@router.post("/chat", summary="Chat with an assistant (streaming)")
async def chat_with_assistant(
    chat_data: ChatRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
):
    """Send a message to an assistant and get a streaming response using langchain"""
    
    # Check user balance before allowing chat - REMOVED: Billing system no longer exists
    from src.assistants.models import AssistantStatusEnum
    
    # Use the new langchain chat service
    service = LangchainChatService(session)
    
    # Get conversation to check assistant status
    conversation = await service.get_conversation(chat_data.conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Check if assistant is active
    if conversation.assistant.status != AssistantStatusEnum.ACTIVE:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Assistant is not available",
                "assistant_status": conversation.assistant.status.value
            }
        )
    
    # Use the streaming method from the langchain service
    async def generate():
        # Convert ImageAttachment to dict format while preserving available metadata
        images = None
        if chat_data.images:
            images = [
                {
                    "data_url": img.data_url,
                    "url": img.url,
                    "alt": img.alt,
                    "mime_type": getattr(img, "mime_type", None),
                    "size": getattr(img, "size", None),
                    "file_key": getattr(img, "file_key", None),
                }
                for img in chat_data.images
            ]
        
        async for event in service.send_message_stream(
            conversation_id=chat_data.conversation_id,
            user_id=current_user.id,
            content=chat_data.content,
            images=images,
            language=chat_data.language
        ):
            yield f"data: {json.dumps(event)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable Nginx buffering
        }
    )
# Message feedback endpoint
@router.post("/messages/{message_id}/feedback", summary="Set message feedback")
async def set_message_feedback(
    message_id: uuid.UUID,
    feedback_data: MessageFeedbackRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
):
    """Set feedback for a message (like/dislike)"""
    # Verify message exists and belongs to user's conversation
    result = await session.execute(
        select(Message)
        .join(Conversation)
        .where(Message.id == message_id)
        .where(Conversation.user_id == current_user.id)
    )
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
        
    message.feedback = feedback_data.feedback
    await session.commit()
    
    return {"status": "success"}
