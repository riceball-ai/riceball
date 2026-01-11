
import asyncio
import uuid
import logging
from typing import Optional, Dict, List, Any
from fastapi import Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from src.channels.models import AssistantChannel, ChannelProvider
from src.channels.schemas import ChannelCreate, ChannelUpdate
from src.channels.adapters.base import BaseChannelAdapter, IncomingMessage
from src.channels.adapters.telegram import TelegramChannelAdapter
from src.channels.adapters.wecom import WecomChannelAdapter
from src.assistants.models import Conversation, Assistant, ConversationStatusEnum
from src.chat.service import LangchainChatService 
from src.chat.models import MessageRole

logger = logging.getLogger(__name__)

class ChannelService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.chat_service = LangchainChatService(session)

    async def get_adapter(self, channel: AssistantChannel) -> BaseChannelAdapter:
        if channel.provider == ChannelProvider.TELEGRAM:
            return TelegramChannelAdapter(channel)
        elif channel.provider == ChannelProvider.WECOM:
            return WecomChannelAdapter(channel)
        else:
            raise ValueError(f"Provider {channel.provider} not supported")

    async def get_channel(self, channel_id: uuid.UUID) -> Optional[AssistantChannel]:
        stmt = select(AssistantChannel).where(AssistantChannel.id == channel_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
        
    async def create_channel(self, data: ChannelCreate) -> AssistantChannel:
        # Check if assistant exists
        assistant = await self.session.get(Assistant, data.assistant_id)
        if not assistant:
            raise HTTPException(status_code=404, detail="Assistant not found")
            
        channel = AssistantChannel(
            name=data.name,
            provider=data.provider,
            assistant_id=data.assistant_id,
            credentials=data.credentials,
            settings=data.settings,
            is_active=data.is_active,
            metadata_={} 
        )
        self.session.add(channel)
        await self.session.commit()
        await self.session.refresh(channel)
        
        # Post-creation hooks (e.g. register webhook)
        try:
             # We assume the public URL is configured in settings or we construct it
             # For now, we skip auto-registration or do it if a 'webhook_url' is provided in settings
             pass 
        except Exception as e:
            logger.error(f"Failed to initialize channel {channel.id}: {e}")
            
        return channel

    async def update_channel(self, channel_id: uuid.UUID, data: ChannelUpdate) -> AssistantChannel:
        channel = await self.get_channel(channel_id)
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")
            
        if data.name is not None:
            channel.name = data.name
        if data.is_active is not None:
            channel.is_active = data.is_active
        if data.credentials is not None:
            channel.credentials = data.credentials
        if data.settings is not None:
            channel.settings = data.settings
            
        await self.session.commit()
        await self.session.refresh(channel)
        return channel

    async def delete_channel(self, channel_id: uuid.UUID):
        channel = await self.get_channel(channel_id)
        if channel:
            await self.session.delete(channel)
            await self.session.commit()

    async def get_channels_by_assistant(self, assistant_id: uuid.UUID) -> List[AssistantChannel]:
        stmt = select(AssistantChannel).where(AssistantChannel.assistant_id == assistant_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def handle_webhook(self, channel_id: uuid.UUID, request: Request):
        logger.info(f"Handling webhook for channel {channel_id}, method: {request.method}")
        channel = await self.get_channel(channel_id)
        if not channel or not channel.is_active:
            # 404 or just ignore
            logger.warning(f"Webhook received for inactive or non-existent channel {channel_id}")
            return {"status": "ignored"}

        adapter = await self.get_adapter(channel)
        
        # Handle Handshake (GET)
        if request.method == "GET":
            handshake_resp = await adapter.handle_handshake(request)
            if handshake_resp:
                return handshake_resp
            # If no handshake response but it was a GET, might be invalid
            raise HTTPException(status_code=400, detail="Invalid handshake")

        # Parse
        logger.info("Verifying request signature...")
        # Verify
        if not await adapter.verify_request(request):
            logger.warning("Signature verification failed")
            raise HTTPException(status_code=401, detail="Invalid signature")
            
        # Parse
        logger.info("Parsing webhook body...")
        incoming = await adapter.parse_webhook_body(request)
        if not incoming:
            logger.warning("No incoming message parsed")
            return {"status": "no_content"}
            
        logger.info(f"Incoming message parsed. Is Poll={incoming.is_stream_poll}. Content len={len(incoming.content)}. SmartBot={getattr(adapter, 'is_smart_bot', False)}")
            
        # 1. Handle Stream Polling (Generic)
        if incoming.is_stream_poll:
            from src.utils.stream_buffer import stream_buffer
            
            logger.debug(f"Processing stream poll request: stream_id={incoming.stream_id}")
            state = await stream_buffer.get_state(incoming.stream_id)
            if not state:
                logger.warning(f"Stream {incoming.stream_id} not found or expired")
                return adapter.format_stream_response(incoming.stream_id, "Stream expired", True, request.query_params)
            
            logger.debug(f"Returning stream state: stream_id={incoming.stream_id}, finished={state['finished']}")
            return adapter.format_stream_response(
                incoming.stream_id, 
                state["content"], 
                state["finished"], 
                request.query_params
            )

        # 2. Initiate New Stream (If adapter supports/requires it, e.g. WeCom Smart Bot)
        if adapter.should_stream_response(incoming):
            from src.utils.stream_buffer import stream_buffer
            import uuid
            
            stream_id = str(uuid.uuid4().hex[:10])
            await stream_buffer.init_stream(stream_id)
             
            # Fire and forget processing using asyncio task
            # Warning: Passing 'self.session' to background task is dangerous as request session closes.
            # We should create a new scope or session.
            asyncio.create_task(run_stream_generation_task(channel.id, incoming, stream_id))
             
            logger.info(f"Initialized stream {stream_id} for user {incoming.user_id}. Returning initial packet.")
            resp = adapter.format_stream_response(stream_id, "Thinking...", False, request.query_params)
            return resp

        # 3. Standard / Legacy Handling (Wait for full response)
        await self._process_incoming_message(channel, adapter, incoming)
        return {"status": "ok"}
        
    async def process_stream_generation_logic(
        self, 
        channel: AssistantChannel, 
        incoming: IncomingMessage,
        stream_id: str
    ):
        """
        Core logic for stream generation, decoupled from adapter and HTTP session context.
        """
        from src.utils.stream_buffer import stream_buffer

        try:
            conversation, user_id = await self._ensure_conversation_context(channel, incoming)

            # 2. Stream Generation
            async for chunk in self.chat_service.send_message_stream(
                conversation_id=conversation.id,
                user_id=user_id,
                content=incoming.content,
            ):
                content_part = self._extract_content_from_chunk(chunk)
                if content_part:
                    await stream_buffer.append_content(stream_id, content_part)
            
            # 3. Finish
            await stream_buffer.mark_finished(stream_id)

        except Exception as e:
            logger.error(f"Stream generation failed: {e}", exc_info=True)
            await stream_buffer.append_content(stream_id, f"\n[System Error: {str(e)}]")
            await stream_buffer.mark_finished(stream_id)

    async def _process_stream_generation(
        self, 
        channel: AssistantChannel, 
        adapter: BaseChannelAdapter, 
        incoming: IncomingMessage,
        stream_id: str
    ):
        # Legacy Wrapper
        await self.process_stream_generation_logic(channel, incoming, stream_id)

    async def _process_incoming_message(
        self, 
        channel: AssistantChannel, 
        adapter: BaseChannelAdapter, 
        incoming: IncomingMessage
    ):
        try:
            conversation, user_id = await self._ensure_conversation_context(channel, incoming)

            full_response_text = ""
            async for chunk in self.chat_service.send_message_stream(
                conversation_id=conversation.id,
                user_id=user_id,
                content=incoming.content,
            ):
                text = self._extract_content_from_chunk(chunk)
                if text:
                    full_response_text += text
                    
            if full_response_text:
                logger.info(f"Accumulated response text length: {len(full_response_text)}")
                await adapter.send_text(incoming.user_id, full_response_text)
            else:
                 logger.warning("Generated response text was empty, nothing to send back.")
                
        except Exception as e:
            logger.error(f"Error processing channel message: {e}", exc_info=True)
            await adapter.send_text(incoming.user_id, "I'm sorry, I encountered an error.")

    async def _ensure_conversation_context(self, channel: AssistantChannel, incoming: IncomingMessage):
        """Find or create a conversation for the incoming message"""
        # Resolve the effective user (create a new internal user if this is a new external user)
        user = await self._get_or_create_channel_user(channel, incoming)
        
        # Now find the LAST conversation for this user and assistant
        # Note: In the future we might want session handling. For now, we resume the last one or create new.
        # But for 'chat', we usually just keep appending or start new based on time? 
        # Actually, standard bot behavior is often one long conversation or daily.
        # Let's verify _find_conversation logic. 
        
        # Wait, if we use real user_id now, we don't need to search by JSON metadata anymore!
        # We can search by `user_id` and `assistant_id` in Conversations table.
        
        conversation = await self._find_active_conversation(user.id, channel.assistant_id)
        
        if not conversation:
            provider_name = channel.provider.value if hasattr(channel.provider, "value") else channel.provider
            title = f"{incoming.username or 'User'} via {provider_name}"
            
            conversation = await self.chat_service.conversation_service.create_conversation(
                user_id=user.id,
                assistant_id=channel.assistant_id,
                title=title
            )
            # We still keep metadata for debugging or reverse lookups
            conversation.extra_data = {
                "channel_id": str(channel.id),
                "external_user_id": incoming.user_id,
                "provider": channel.provider,
                "username": incoming.username
            }
            self.session.add(conversation)
            await self.session.commit()
            
        return conversation, user.id

    async def _get_or_create_channel_user(self, channel: AssistantChannel, incoming: IncomingMessage):
        """
        Map external identity (e.g. WeCom UserId) to internal User.
        If mapped user doesn't exist, create a new 'visitor' User.
        """
        from src.channels.models import ChannelIdentity
        from src.users.models import User
        
        provider = channel.provider.value if hasattr(channel.provider, "value") else channel.provider
        external_id = incoming.user_id
        
        # 1. Lookup Identity
        stmt = select(ChannelIdentity).where(
            ChannelIdentity.provider == provider,
            ChannelIdentity.identity_id == external_id
        )
        result = await self.session.execute(stmt)
        identity = result.scalar_one_or_none()
        
        if identity:
            identity.last_seen_at = func.now()
            # Update extra data if needed (e.g. name change)
            # identity.extra_data = ...
            await self.session.commit()
            
            # Fetch User
            user = await self.session.get(User, identity.user_id)
            if user:
                return user
            else:
                 logger.warning(f"ChannelIdentity {identity.id} points to missing user {identity.user_id}")
                 # Fallthrough to recreate? Or raise error? Let's recreate.
                 await self.session.delete(identity)
                 await self.session.commit()

        # 2. Create New User & Identity
        # Use a random placeholder email or None if model allows. 
        # Our User model allows nullable email.
        
        new_user = User(
            email=None, 
            hashed_password="!", # Unusable password
            is_active=True,
            is_superuser=False,
            is_verified=True,
            name=incoming.username or f"{provider}_{external_id}"
        )
        self.session.add(new_user)
        await self.session.flush() # Get ID
        
        new_identity = ChannelIdentity(
            user_id=new_user.id,
            channel_id=channel.id,
            provider=provider,
            identity_id=external_id,
            extra_data={"username": incoming.username}
        )
        self.session.add(new_identity)
        await self.session.commit()
        
        return new_user

    async def _find_active_conversation(self, user_id: uuid.UUID, assistant_id: uuid.UUID) -> Optional[Conversation]:
        """Find the most recent conversation for this user/assistant pair"""
        stmt = select(Conversation).where(
            Conversation.user_id == user_id,
            Conversation.assistant_id == assistant_id
        ).order_by(Conversation.updated_at.desc())
        
        result = await self.session.execute(stmt)
        return result.scalars().first()

    def _extract_content_from_chunk(self, chunk: Any) -> str:
        """Extract text content from various chunk formats"""
        if isinstance(chunk, dict):
            if chunk.get("type") == "content_chunk":
                return chunk.get("data", {}).get("content", "")
        elif hasattr(chunk, "content"):
            return chunk.content or ""
        return ""

    async def _find_conversation_by_channel(self, channel_id: uuid.UUID, ext_user_id: str) -> Optional[Conversation]:
        # Implementation for PostgreSQL using JSON path operators
        # cast to string to be safe
        cid_str = str(channel_id)
        
        # This is PG specific syntax usually. 
        # For SQLite in dev, this might fail if not handled carefully.
        # We'll try a text cast approach which is safer across both.
        
        # Using SQLA functional cast
        # func.json_extract(Conversation.extra_data, '$.channel_id') == cid_str ...
        
        # Let's try to iterate recent conversations of the assistant? No, too slow.
        # Let's try the native JSON operator.
        query = select(Conversation).where(
            Conversation.extra_data['channel_id'].as_string() == cid_str,
            Conversation.extra_data['external_user_id'].as_string() == ext_user_id
        ).order_by(Conversation.updated_at.desc())
        
        result = await self.session.execute(query)
        return result.scalars().first()

    async def _process_stream_generation(
        self, 
        channel: AssistantChannel, 
        adapter: BaseChannelAdapter, 
        incoming: IncomingMessage,
        stream_id: str
    ):
        """
        Background task to generate AI response and push to stream buffer
        """
        from src.utils.stream_buffer import stream_buffer
        from src.assistants.models import Assistant
        
        try:
            # 1. Setup Context (Similar to _process_incoming_message)
            stmt = select(Assistant).where(Assistant.id == channel.assistant_id)
            res = await self.session.execute(stmt)
            assistant = res.scalar_one()
            user_id = assistant.owner_id
            
            conversation = await self._find_conversation_by_channel(channel.id, incoming.user_id)
            
            provider_name = channel.provider
            if hasattr(provider_name, "value"):
                provider_name = provider_name.value

            if not conversation:
                title = f"{incoming.username or 'User'} via {provider_name}"
                conversation = await self.chat_service.conversation_service.create_conversation(
                    user_id=user_id,
                    assistant_id=assistant.id,
                    title=title
                )
                conversation.extra_data = {
                    "channel_id": str(channel.id),
                    "external_user_id": incoming.user_id,
                    "provider": channel.provider,
                    "username": incoming.username
                }
                self.session.add(conversation)
                await self.session.commit()

            # 2. Stream Generation
            async for chunk in self.chat_service.send_message_stream(
                conversation_id=conversation.id,
                user_id=user_id,
                content=incoming.content,
            ):
                content_part = ""
                if isinstance(chunk, dict):
                    if chunk.get("type") == "content_chunk":
                        content_part = chunk.get("data", {}).get("content", "")
                elif hasattr(chunk, "content"):
                    content_part = chunk.content
                
                if content_part:
                    await stream_buffer.append_content(stream_id, content_part)
            
            # 3. Finish
            await stream_buffer.mark_finished(stream_id)

        except Exception as e:
            logger.error(f"Stream generation failed: {e}", exc_info=True)
            await stream_buffer.append_content(stream_id, f"\n[System Error: {str(e)}]")
            await stream_buffer.mark_finished(stream_id)

async def run_stream_generation_task(channel_id: uuid.UUID, incoming: IncomingMessage, stream_id: str):
    """
    Standalone task runner for background stream generation.
    Creates its own database session to avoid 'Session is closed' errors.
    """
    from src.database import async_session_maker
    
    async with async_session_maker() as session:
        service = ChannelService(session)
        channel = await service.get_channel(channel_id)
        if not channel:
            logger.error(f"Channel {channel_id} not found in background task")
            from src.utils.stream_buffer import stream_buffer
            await stream_buffer.append_content(stream_id, "[System Error: Channel context lost]")
            await stream_buffer.mark_finished(stream_id)
            return

        # Reuse the logic method
        await service.process_stream_generation_logic(channel, incoming, stream_id)
