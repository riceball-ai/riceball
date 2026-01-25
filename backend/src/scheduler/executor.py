
import asyncio
import logging
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import async_session_maker
from src.channels.models import ChannelConfig, UserChannelBinding, ChannelProvider
from src.channels.services.telegram import TelegramChannelService
from src.channels.services.wecom import WecomChannelService

from src.assistants.models import Assistant
from src.scheduler.models import ScheduledTask
from datetime import datetime
# Assuming we will import something to run assistant (e.g. from chat.service)
from src.chat.service import LangchainChatService
from src.chat.models import MessageRole

logger = logging.getLogger(__name__)

class ChannelServiceFactory:
    @staticmethod
    def get_service(channel: ChannelConfig):
        if channel.provider == ChannelProvider.TELEGRAM:
            return TelegramChannelService(channel)
        elif channel.provider == ChannelProvider.WECOM:
            return WecomChannelService(channel)
        else:
            raise ValueError(f"Provider {channel.provider} not supported for outbound service")

async def process_incoming_message(
    channel_id: uuid.UUID,
    user_id: str, # External User ID
    text: str,
    username: Optional[str] = None
):
    """
    Background Task Executor for Webhook events.
    Running in a separate context from the HTTP request.
    """
    logger.info(f"Background processing message from {user_id} on channel {channel_id}")
    
    async with async_session_maker() as session:
        try:
            # 1. Load Channel Config
            channel = await session.get(ChannelConfig, channel_id)
            if not channel or not channel.is_active:
                logger.warning(f"Channel {channel_id} not found or inactive")
                return

            # 2. Find or Create User Binding
            # Ideally we should resolve this to an internal system user.
            # For now, we assume simple binding or anonymous usage if needed.
            # But "active push" requires knowing where to push back.
            
            # Simple Logic: Check if we have seen this external user before
            stmt = select(UserChannelBinding).where(
                UserChannelBinding.channel_config_id == channel_id,
                UserChannelBinding.external_user_id == user_id
            )
            result = await session.execute(stmt)
            binding = result.scalar_one_or_none()
            
            # If not exists, maybe create it? (Auto-registration flow)
            # This part depends on how strict we want to be.
            # Let's auto-register for now to keep it working like before.
            if not binding:
                 # TODO: Link to a real User if possible. 
                 # For now, we might fail or need a guest user strategy.
                 # Let's assume we find a user via some logic or create a guest.
                 pass

            # 3. Determine Assistant
            # If channel has specific assistant_id, use it.
            assistant: Assistant | None = None
            if channel.assistant_id:
                assistant = await session.get(Assistant, channel.assistant_id)
            
            if not assistant:
                logger.warning("No assistant configured for this channel")
                # Should we reply "Not configured"?
                return

            # 4. Run Inference (This is where RAG/Agent magic happens)
            # We reuse LangchainChatService but need to be careful about conversation state.
            
            # Create a transient chat service
            chat_service = LangchainChatService(session)
            
            # We need a conversation ID. 
            # Strategy: Maintain one conversation per External User per Channel?
            # Or create new one every time? Usually "Chat Bot" style implies persistent session.
            
            # Simple Session Management:
            # Check for last active conversation for this binding
            # (Omitting complex session logic for brevity, creating on fly or fetching latest)
            conversation_id = await _get_or_create_conversation_for_external_user(session, assistant.id, user_id, channel.provider)
            
            # Prepare generator
            # LangchainChatService.send_message usually returns a stream response (generator)
            # But it requires 'user' object for permission checks.
            # We might need to bypass auth checks or mock a user object.
            
            # Since Channel Events often don't map to a real authenticated internal user securely,
            # We pass a flag or mock user_id if the method requires it.
            # However, looking at LangchainChatService.send_message_stream signature:
            # def send_message_stream(self, conversation_id: uuid.UUID, user_id: uuid.UUID, ...)
            
            # The user_id is mainly used for permission check "get_conversation_with_model(conversation_id, user_id)".
            # If we pass user_id=None or a system ID, we need to ensure get_conversation_with_model handles it or we bypass it.
            
            # PROPOSAL: We should implement a specialized method in ChatService for System/Bot calls 
            # OR ensure our conversation fetching logic in ChatService is flexible.
            # For now, let's assume the conversation we created/fetched is accessible.
            # We might need to fetch the user_id that generated the conversation.
            
            # Strategy: use the user_id from the conversation owner.
            # (Assuming _get_or_create has returned a valid conversation ID)
            
            # Fetch conversation to get owner
            stmt_conv = select(Conversation).where(Conversation.id == conversation_id)
            conv_res = await session.execute(stmt_conv)
            conv = conv_res.scalar_one()
            
            # Call Service
            async def response_wrapper():
                async for chunk in chat_service.send_message_stream(
                    conversation_id=conversation_id,
                    user_id=conv.user_id, # Assumes conv.user_id is set. If System/None, ChatService might break.
                    content=text
                ):
                    # ChatService yields dicts like {'chunk': 'Server', 'status': 'streaming'}
                    # We need to extract the text content and yield it
                    if isinstance(chunk, dict):
                         yield chunk.get("chunk", "")
                    elif isinstance(chunk, str):
                         yield chunk

            response_generator = response_wrapper()
            
            # 5. Push Response via Channel Service
            service = ChannelServiceFactory.get_service(channel)
            await service.send_stream(user_id, response_generator)
            
        except Exception as e:
            logger.exception(f"Error processing message task: {e}")
            # Optional: Send error message back to user?


async def execute_scheduled_task(task_id: uuid.UUID):
    """
    Executor for Scheduled Tasks (Cron Jobs).
    """
    logger.info(f"Executing scheduled task {task_id}")
    async with async_session_maker() as session:
        try:
            # 1. Load Task
            task = await session.get(ScheduledTask, task_id)
            if not task or not task.is_active:
                logger.warning(f"Task {task_id} skipped (not found or inactive)")
                return
                
            # Update last run timestamp
            task.last_run_at = datetime.utcnow()
            await session.commit() # Commit early to mark run start? Or end. Let's do prompt updates.
            
            # 2. Resolve Target
            binding = await session.get(UserChannelBinding, task.target_binding_id)
            if not binding:
                logger.error(f"Task {task_id} failed: Target binding {task.target_binding_id} not found")
                return

            channel = await session.get(ChannelConfig, binding.channel_config_id)
            if not channel or not channel.is_active:
                logger.error(f"Task {task_id} failed: Channel not active or found")
                return

            # 3. Resolve Assistant
            assistant = await session.get(Assistant, task.assistant_id)
            if not assistant:
                 logger.error(f"Task {task_id} failed: Assistant {task.assistant_id} not found")
                 return
                 
            # 4. Prepare Context
            chat_service = LangchainChatService(session)
            
            # We need a conversation. 
            # Reuse/Create conversation logic
            conversation_id = await _get_or_create_conversation_for_external_user(
                session, 
                assistant.id, 
                binding.external_user_id, 
                binding.provider
            )
            
            # Need Owner User ID for ChatService
            # We use the internal user_id linked in binding
            internal_user_id = binding.user_id
            
            logger.info(f"Task {task_id}: Triggering assistant {assistant.id} for user {internal_user_id}")

            # 5. Execute & Stream
            async def response_wrapper():
                async for chunk in chat_service.send_message_stream(
                    conversation_id=conversation_id,
                    user_id=internal_user_id,
                    content=task.prompt_template
                ):
                    if isinstance(chunk, dict):
                         yield chunk.get("chunk", "")
                    elif isinstance(chunk, str):
                         yield chunk
            
            service = ChannelServiceFactory.get_service(channel)
            await service.send_stream(binding.external_user_id, response_wrapper())
            
            logger.info(f"Task {task_id} completed successfully")
            
        except Exception as e:
            logger.exception(f"Scheduled Task {task_id} failed: {e}")


async def _get_or_create_conversation_for_external_user(
    session: AsyncSession, 
    assistant_id: uuid.UUID,
    external_user_id: str,
    provider: str
) -> uuid.UUID:
    """
    Helper to manage conversation state for external users.
    """
    from src.assistants.models import Conversation
    from src.users.models import User
    
    # Check if we have an existing open conversation
    # Ideally should join with Binding -> User -> Conversations
    # But simplifying: Search conversation by unique title pattern? No that's bad.
    
    # Correct way: use UserChannelBinding to find internal user.
    stmt = select(UserChannelBinding).where(
        UserChannelBinding.external_user_id == external_user_id
        # and provider...
    )
    result = await session.execute(stmt)
    binding = result.scalar_one_or_none()
    
    internal_user_id = binding.user_id if binding else None
    
    if not internal_user_id:
        # Create a temporary guest user? Or use a dedicated "Bot User"?
        # For this refactor to work without login, we need a System User concept.
        # Let's try to find a user with email "bot@system" or similar, or create one.
        logger.info(f"External user {external_user_id} has no binding. Creating Guest User.")
        
        # Create Guest User
        new_user = User(
            email=None, 
            hashed_password="",
            is_active=True,
            is_superuser=False,
            is_verified=True,
            name=f"Guest-{external_user_id[:6]}"
        )
        session.add(new_user)
        await session.flush() # get ID
        
        # Create Binding
        new_binding = UserChannelBinding(
            user_id=new_user.id,
            external_user_id=external_user_id,
            provider=provider
        )
        session.add(new_binding)
        await session.flush()
        internal_user_id = new_user.id

    # Find latest conversation
    # We might want to "timeout" sessions after 24h?
    # For now, just create new one for every "start" command or reuse last one?
    # Simple logic: Always use the latest active one.
    
    stmt_conv = select(Conversation).where(
        Conversation.user_id == internal_user_id,
        Conversation.assistant_id == assistant_id,
        Conversation.is_pinned == False # usage as 'active' flag? No.
    ).order_by(Conversation.updated_at.desc()).limit(1)
    
    conv_res = await session.execute(stmt_conv)
    existing_conv = conv_res.scalar_one_or_none()
    
    if existing_conv:
        return existing_conv.id
        
    # Create new
    conv = Conversation(
        assistant_id=assistant_id,
        title=f"Chat via {provider}",
        user_id=internal_user_id
    )
    session.add(conv)
    await session.commit()
    return conv.id
