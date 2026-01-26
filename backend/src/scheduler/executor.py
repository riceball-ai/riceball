
import asyncio
import logging
import uuid
from typing import Optional, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import async_session_maker
from src.channels.models import ChannelConfig, UserChannelBinding, ChannelProvider
from src.channels.services.telegram import TelegramChannelService
from src.channels.services.wecom import WecomChannelService
from src.channels.services.wecom_smart_bot import WecomSmartBotChannelService
from src.channels.services.wecom_webhook import WecomWebhookChannelService

from src.assistants.models import Assistant, Conversation, ConversationStatusEnum
from src.users.models import User
from src.scheduler.models import ScheduledTask
from datetime import datetime
from src.chat.service import LangchainChatService

logger = logging.getLogger(__name__)

class ChannelServiceFactory:
    @staticmethod
    def get_service(channel: ChannelConfig):
        if channel.provider == ChannelProvider.TELEGRAM:
            return TelegramChannelService(channel)
        elif channel.provider == ChannelProvider.WECOM:
            return WecomChannelService(channel)
        elif channel.provider == ChannelProvider.WECOM_SMART_BOT:
            return WecomSmartBotChannelService(channel)
        elif channel.provider == ChannelProvider.WECOM_WEBHOOK:
            return WecomWebhookChannelService(channel)
        else:
            raise ValueError(f"Provider {channel.provider} not supported for outbound service")

async def _ensure_channel_user(
    session: AsyncSession,
    channel: ChannelConfig,
    external_user_id: str,
    username: Optional[str] = None
) -> User:
    """
    Resolve external user ID to internal User via Binding.
    Creates a Guest User if no binding exists.
    """
    # 1. Try strict match first (Same Channel)
    stmt = select(UserChannelBinding).where(
        UserChannelBinding.channel_config_id == channel.id,
        UserChannelBinding.external_user_id == external_user_id
    )
    result = await session.execute(stmt)
    binding = result.scalar_one_or_none()

    # 2. If not found, try loose match by Provider + ExternalID
    # (To handle cases where user is bound globally to provider but not this specific channel instance yet,
    #  OR to prevent Unique Constraint violation if binding exists for another channel)
    if not binding:
        provider_val = channel.provider.value if hasattr(channel.provider, "value") else channel.provider
        stmt = select(UserChannelBinding).where(
            UserChannelBinding.provider == provider_val,
            UserChannelBinding.external_user_id == external_user_id
        )
        result = await session.execute(stmt)
        binding = result.scalar_one_or_none()

    if binding:
        # If we found a binding (either specific or global), use that user.
        # Ideally we might want to update the binding to point to this channel if it was null?
        # But 'channel_config_id' implies "Source of registration".
        user = await session.get(User, binding.user_id)
        if user:
            return user
        else:
             # Zombie binding (user deleted). Clean up?
             await session.delete(binding)
             await session.flush()
             # Fall through to create new

    # Create Guest User
    logger.info(f"Creating Guest User for external_id={external_user_id} on channel={channel.id}")
    
    # Use channel provider as prefix for guest users
    prefix = str(channel.provider).capitalize() # e.g. "Wecom", "Telegram"
    
    new_user = User(
        email=None,
        hashed_password="",
        is_active=True,
        is_superuser=False,
        is_verified=True,
        name=username or f"{prefix}-{external_user_id[:6]}"
    )
    session.add(new_user)
    await session.flush()

    # Create Binding
    new_binding = UserChannelBinding(
        user_id=new_user.id,
        channel_config_id=channel.id,
        external_user_id=external_user_id,
        provider=channel.provider,
        metadata_={"username": username}
    )
    session.add(new_binding)
    await session.commit()
    
    return new_user

async def _get_active_conversation(
    session: AsyncSession,
    user_id: uuid.UUID,
    assistant_id: uuid.UUID,
    title_context: str = "Chat"
) -> Conversation:
    """
    Find or create an active conversation for the user/assistant pair.
    """
    stmt = select(Conversation).where(
        Conversation.user_id == user_id,
        Conversation.assistant_id == assistant_id,
        Conversation.status == ConversationStatusEnum.ACTIVE
    ).order_by(Conversation.updated_at.desc()).limit(1)
    
    result = await session.execute(stmt)
    existing_conv = result.scalar_one_or_none()
    
    if existing_conv:
        return existing_conv

    # Create new conversation
    conv = Conversation(
        assistant_id=assistant_id,
        title=title_context,
        user_id=user_id,
        status=ConversationStatusEnum.ACTIVE
    )
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    return conv

async def _stream_response_generator(
    chat_service: LangchainChatService,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    text: str
) -> AsyncGenerator[str, None]:
    """
    Wraps the chat service stream to yield only text content.
    """
    async for chunk in chat_service.send_message_stream(
        conversation_id=conversation_id,
        user_id=user_id,
        content=text
    ):
        if isinstance(chunk, dict):
            msg_type = chunk.get("type")
            if msg_type == "content_chunk":
                yield chunk.get("data", {}).get("content", "")
            elif "chunk" in chunk:
                yield chunk.get("chunk", "")
        elif isinstance(chunk, str):
            yield chunk

async def process_incoming_message(
    channel_id: uuid.UUID,
    user_id: str,
    text: str,
    username: Optional[str] = None,
    stream_id: Optional[str] = None
):
    """
    Background Task: Process incoming webhook message.
    1. Resolve Channel & User
    2. Invoke Assistant (Langchain)
    3. Stream response back via Channel Adapter
    """
    logger.info(f"Processing message task: channel={channel_id}, user={user_id}")
    
    async with async_session_maker() as session:
        try:
            # 1. Validation
            channel = await session.get(ChannelConfig, channel_id)
            if not channel or not channel.is_active:
                logger.warning(f"Task ignored: Channel {channel_id} inactive or missing")
                return

            if not channel.assistant_id:
                logger.warning(f"Task ignored: Channel {channel.name} has no assistant")
                return
            
            assistant = await session.get(Assistant, channel.assistant_id)
            if not assistant:
                logger.warning("Task ignored: Assistant configuration missing")
                return

            # 2. Resolve User & Conversation
            user = await _ensure_channel_user(session, channel, user_id, username)
            conversation = await _get_active_conversation(
                session, 
                user.id, 
                assistant.id, 
                title_context=f"Chat via {channel.provider}"
            )

            # 3. Execution
            chat_service = LangchainChatService(session)
            response_gen = _stream_response_generator(chat_service, conversation.id, user.id, text)
            
            # 4. Response
            service = ChannelServiceFactory.get_service(channel)
            target_id = stream_id if stream_id else user_id
            await service.send_stream(target_id, response_gen)
            
        except Exception as e:
            logger.exception(f"Error in process_incoming_message: {e}")

async def execute_scheduled_task(task_id: uuid.UUID):
    """
    Executor for Scheduled Tasks (Cron Jobs).
    """
    logger.info(f"Executing scheduled task {task_id}")
    async with async_session_maker() as session:
        try:
            # 1. Load Task & Dependencies
            task = await session.get(ScheduledTask, task_id)
            if not task or not task.is_active:
                logger.warning(f"Task {task_id} skipped")
                return
                
            task.last_run_at = datetime.utcnow()
            
            # Load Channel directly
            channel = await session.get(ChannelConfig, task.channel_config_id)
            if not channel or not channel.is_active:
                logger.error(f"Task {task_id} failed: Channel {task.channel_config_id} unavailable")
                return

            assistant = await session.get(Assistant, task.assistant_id)
            if not assistant:
                 logger.error(f"Task {task_id} failed: Assistant unavailable")
                 return
            
            await session.commit()

            # 2. Execution Context
            # Use Task Owner as the context user for this execution
            # This ensures the conversation history is linked to the user who scheduled it.
            context_user_id = task.owner_id
            
            conversation = await _get_active_conversation(
                session, 
                context_user_id,
                assistant.id, 
                title_context=f"Scheduled Task: {task.name}"
            )

            # 3. Stream & Send
            chat_service = LangchainChatService(session)
            response_gen = _stream_response_generator(chat_service, conversation.id, context_user_id, task.prompt_template)
            
            service = ChannelServiceFactory.get_service(channel)
            await service.send_stream(task.target_identifier, response_gen)
            
            logger.info(f"Task {task_id} completed. Sent to {task.target_identifier} via {channel.name}")
            
        except Exception as e:
            logger.exception(f"Scheduled Task {task_id} failed: {e}")

