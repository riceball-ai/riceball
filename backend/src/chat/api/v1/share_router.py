import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import current_active_user
from src.database import get_async_session
from src.users.models import User

from src.chat.share_service import ConversationShareService
from src.files.storage import storage_service
from .schemas import (
    ConversationShareCreateRequest,
    ConversationSharePublicResponse,
    ConversationShareResponse,
    SharedMessage,
    AssistantShareInfo,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/share-links")


@router.post("", response_model=ConversationShareResponse, summary="Create or reuse a share link")
async def create_share_link(
    payload: ConversationShareCreateRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_active_user)
):
    service = ConversationShareService(session)
    try:
        share = await service.create_share(
            conversation_id=payload.conversation_id,
            user=current_user,
            scope=payload.scope,
            start_message_id=payload.start_message_id,
            end_message_id=payload.end_message_id
        )
        return share
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{share_id}", response_model=ConversationSharePublicResponse, summary="Get public share data")
async def get_share_link(
    share_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session)
):
    service = ConversationShareService(session)
    try:
        result = await service.get_public_share(share_id)
    except ValueError as exc:
        logger.exception("Failed to load share %s", share_id)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not result:
        raise HTTPException(status_code=404, detail="Share link not found")

    share, messages = result
    assistant = share.conversation.assistant if share.conversation else None
    assistant_name = assistant.name if assistant else ""
    assistant_description = assistant.description if assistant else ""
    assistant_id = assistant.id if assistant else None
    assistant_payload = None
    if assistant:
        avatar_url = None
        if assistant.avatar_file_path:
            try:
                avatar_url = await storage_service.get_public_url(assistant.avatar_file_path)
            except Exception:  # noqa: BLE001 - log and continue
                logger.warning("Failed to build public avatar URL for assistant %s", assistant.id, exc_info=True)
        assistant_payload = AssistantShareInfo(
            id=assistant.id,
            name=assistant.name,
            description=assistant.description,
            avatar_file_path=assistant.avatar_file_path,
            avatar_url=avatar_url,
            translations=assistant.translations or {},
        )

    return ConversationSharePublicResponse(
        id=share.id,
        conversation_id=share.conversation_id,
        scope=share.scope,
        assistant_id=assistant_id,
        assistant_name=assistant_name,
        assistant_description=assistant_description,
        assistant=assistant_payload,
        conversation_title=share.conversation.title if share.conversation else "",
        messages=[
            SharedMessage(
                id=message.id,
                message_type=message.message_type,
                content=message.content,
                extra_data=message.extra_data or {},
                created_at=message.created_at
            )
            for message in messages
        ],
        created_at=share.created_at
    )