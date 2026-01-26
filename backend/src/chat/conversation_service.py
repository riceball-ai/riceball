"""Conversation-related database operations extracted from LangchainChatService."""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.assistants.models import Assistant, Conversation, Message
from src.ai_models.models import Model


class ConversationService:
    """Encapsulates CRUD helpers for conversations and messages."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_conversation(
        self,
        *,
        assistant_id: uuid.UUID,
        user_id: uuid.UUID,
        title: Optional[str] = None,
    ) -> Conversation:
        assistant_result = await self.session.execute(
            select(Assistant).where(Assistant.id == assistant_id)
        )
        assistant = assistant_result.scalar_one_or_none()

        if not assistant:
            raise ValueError("Assistant not found")

        if assistant.owner_id != user_id and not assistant.is_public:
            raise PermissionError("Access denied to assistant")

        final_title = title or f"Chat with {assistant.name}"
        conversation = Conversation(
            title=final_title,
            assistant_id=assistant_id,
            user_id=user_id,
            status="ACTIVE",
        )

        self.session.add(conversation)
        assistant.usage_count = assistant.usage_count + 1

        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def get_conversation(
        self,
        *,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[Conversation]:
        result = await self.session.execute(
            select(Conversation)
            .options(selectinload(Conversation.assistant))
            .where(
                and_(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_conversation_with_model(
        self,
        *,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[Conversation]:
        result = await self.session.execute(
            select(Conversation)
            .options(
                selectinload(Conversation.assistant)
                .selectinload(Assistant.model)
                .selectinload(Model.provider),
                selectinload(Conversation.assistant).selectinload(Assistant.mcp_servers),
                selectinload(Conversation.user),
            )
            .where(
                and_(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_conversation_messages(
        self,
        *,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Message]:
        conversation = await self.get_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
        )
        if not conversation:
            raise ValueError("Conversation not found or access denied")

        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def delete_conversation(
        self,
        *,
        conversation_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> bool:
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        if user_id:
            stmt = stmt.where(Conversation.user_id == user_id)
            
        result = await self.session.execute(stmt)
        conversation = result.scalar_one_or_none()
        if not conversation:
            return False

        conversation.status = "DELETED"
        await self.session.commit()
        return True

    async def hard_delete_conversation(
        self,
        *,
        conversation_id: uuid.UUID,
    ) -> bool:
        """Permanently delete a conversation and its messages."""
        result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            return False

        await self.session.delete(conversation)
        await self.session.commit()
        return True

    async def archive_conversation(
        self,
        *,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        result = await self.session.execute(
            select(Conversation).where(
                and_(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id,
                )
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            return False

        conversation.status = "ARCHIVED"
        await self.session.commit()
        return True