import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.assistants.models import (
    Conversation,
    ConversationShare,
    ConversationShareScopeEnum,
    ConversationShareStatusEnum,
    Message,
    MessageTypeEnum
)
from src.users.models import User


class ConversationShareService:
    """Service layer for creating and retrieving conversation share links"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_share(
        self,
        *,
        conversation_id: uuid.UUID,
        user: User,
        scope: ConversationShareScopeEnum,
        start_message_id: Optional[uuid.UUID] = None,
        end_message_id: Optional[uuid.UUID] = None
    ) -> ConversationShare:
        conversation = await self._get_conversation(conversation_id, user.id)
        if not conversation:
            raise ValueError("Conversation not found or access denied")

        if scope == ConversationShareScopeEnum.CONVERSATION:
            share = await self._get_existing_conversation_share(conversation_id)
            if share:
                return share
            return await self._create_new_share(
                conversation_id=conversation_id,
                created_by=user.id,
                scope=scope
            )

        if scope == ConversationShareScopeEnum.MESSAGE:
            if not start_message_id or not end_message_id:
                raise ValueError("start_message_id and end_message_id are required for message shares")

            start_message, end_message = await self._validate_message_pair(
                conversation_id=conversation_id,
                start_message_id=start_message_id,
                end_message_id=end_message_id
            )

            existing_share = await self._get_existing_message_share(
                conversation_id=conversation_id,
                start_message_id=start_message.id,
                end_message_id=end_message.id
            )
            if existing_share:
                return existing_share

            return await self._create_new_share(
                conversation_id=conversation_id,
                created_by=user.id,
                scope=scope,
                start_message_id=start_message.id,
                end_message_id=end_message.id
            )

        raise ValueError("Unsupported share scope")

    async def get_public_share(
        self,
        share_id: uuid.UUID
    ) -> Optional[tuple[ConversationShare, list[Message]]]:
        """Fetch share along with messages for public consumption"""
        result = await self.session.execute(
            select(ConversationShare)
            .options(
                selectinload(ConversationShare.conversation).selectinload(Conversation.assistant),
                selectinload(ConversationShare.start_message),
                selectinload(ConversationShare.end_message),
                selectinload(ConversationShare.creator)
            )
            .where(
                and_(
                    ConversationShare.id == share_id,
                    ConversationShare.status == ConversationShareStatusEnum.ACTIVE
                )
            )
        )
        share = result.scalar_one_or_none()
        if not share:
            return None

        messages = await self._fetch_messages_for_share(share)

        share.view_count = share.view_count + 1
        share.last_accessed_at = datetime.now(timezone.utc)
        await self.session.commit()

        return share, messages

    async def _get_conversation(
        self,
        conversation_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None
    ) -> Optional[Conversation]:
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        if user_id:
            stmt = stmt.where(Conversation.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _validate_message_pair(
        self,
        *,
        conversation_id: uuid.UUID,
        start_message_id: uuid.UUID,
        end_message_id: uuid.UUID
    ) -> tuple[Message, Message]:
        start_message = await self.session.get(Message, start_message_id)
        end_message = await self.session.get(Message, end_message_id)

        if not start_message or not end_message:
            raise ValueError("Message not found")

        if (
            start_message.conversation_id != conversation_id or
            end_message.conversation_id != conversation_id
        ):
            raise ValueError("Messages do not belong to the conversation")

        if start_message.created_at > end_message.created_at:
            raise ValueError("Start message must be earlier than end message")

        if start_message.message_type != MessageTypeEnum.USER:
            raise ValueError("Start message must be a USER message")

        if end_message.message_type != MessageTypeEnum.ASSISTANT:
            raise ValueError("End message must be an ASSISTANT message")

        return start_message, end_message

    async def _get_existing_conversation_share(
        self,
        conversation_id: uuid.UUID
    ) -> Optional[ConversationShare]:
        result = await self.session.execute(
            select(ConversationShare)
            .where(
                and_(
                    ConversationShare.conversation_id == conversation_id,
                    ConversationShare.scope == ConversationShareScopeEnum.CONVERSATION,
                    ConversationShare.status == ConversationShareStatusEnum.ACTIVE
                )
            )
        )
        return result.scalar_one_or_none()

    async def _get_existing_message_share(
        self,
        conversation_id: uuid.UUID,
        start_message_id: uuid.UUID,
        end_message_id: uuid.UUID
    ) -> Optional[ConversationShare]:
        result = await self.session.execute(
            select(ConversationShare)
            .where(
                and_(
                    ConversationShare.conversation_id == conversation_id,
                    ConversationShare.scope == ConversationShareScopeEnum.MESSAGE,
                    ConversationShare.start_message_id == start_message_id,
                    ConversationShare.end_message_id == end_message_id,
                    ConversationShare.status == ConversationShareStatusEnum.ACTIVE
                )
            )
        )
        return result.scalar_one_or_none()

    async def _create_new_share(
        self,
        *,
        conversation_id: uuid.UUID,
        created_by: uuid.UUID,
        scope: ConversationShareScopeEnum,
        start_message_id: Optional[uuid.UUID] = None,
        end_message_id: Optional[uuid.UUID] = None
    ) -> ConversationShare:
        share = ConversationShare(
            conversation_id=conversation_id,
            created_by=created_by,
            scope=scope,
            start_message_id=start_message_id,
            end_message_id=end_message_id,
            status=ConversationShareStatusEnum.ACTIVE,
            extra_data={}
        )
        self.session.add(share)
        await self.session.commit()
        await self.session.refresh(share)
        return share

    async def _fetch_messages_for_share(
        self,
        share: ConversationShare
    ) -> list[Message]:
        if share.scope == ConversationShareScopeEnum.CONVERSATION:
            result = await self.session.execute(
                select(Message)
                .where(Message.conversation_id == share.conversation_id)
                .order_by(Message.created_at.asc())
            )
            return result.scalars().all()

        if share.scope == ConversationShareScopeEnum.MESSAGE:
            stmt = (
                select(Message)
                .where(Message.id.in_([share.start_message_id, share.end_message_id]))
                .order_by(Message.created_at.asc())
            )
            result = await self.session.execute(stmt)
            messages = result.scalars().all()
            if len(messages) != 2:
                raise ValueError("Shared messages could not be loaded")
            return messages

        return []