
import asyncio
import logging
import uuid
from typing import Optional, AsyncGenerator
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.database import async_session_maker
from src.channels.models import ChannelConfig, UserChannelBinding, ChannelProvider
from src.channels.services.telegram import TelegramChannelService
from src.channels.services.wecom import WecomChannelService
from src.channels.services.wecom_smart_bot import WecomSmartBotChannelService
from src.channels.services.wecom_webhook import WecomWebhookChannelService

from src.scheduler.models import ScheduledTask, ScheduledTaskExecution
from src.assistants.models import Assistant
from src.ai_models.models import Model
from src.chat.engine import AIEngine

logger = logging.getLogger(__name__)

# Remove _get_active_conversation and _stream_response_generator helpers if not used elsewhere, or keep them.
# I will keep _stream_response_generator but modify it or create a new one for AIEngine events.

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
            raise NotImplementedError(f"Provider {channel.provider} not supported for task execution")

async def _ai_engine_stream_adapter(
    ai_engine: AIEngine,
    assistant: Assistant,
    prompt: str,
    context_id: uuid.UUID,
    user_id: uuid.UUID
) -> AsyncGenerator[str, None]:
    """
    Adapts AIEngine event stream to simple text stream for ChannelService.
    Also captures the full content for logging.
    """
    messages = [{"role": "user", "content": prompt}]
    
    async for event in ai_engine.generate_stream(
        assistant=assistant,
        messages=messages,
        context_id=context_id,
        user_id=user_id
    ):
        if event["type"] == "content_chunk":
             content = event["data"].get("content", "")
             if content:
                 yield content
        elif event["type"] == "error":
             yield f"\n[System Error: {event['data'].get('error')}]"

async def execute_scheduled_task(task_id: uuid.UUID):
    """
    Executor for Scheduled Tasks (Cron Jobs).
    """
    logger.info(f"Executing scheduled task {task_id}")
    async with async_session_maker() as session:
        execution_record = None
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

            stmt = select(Assistant).options(
                selectinload(Assistant.model).selectinload(Model.provider)
            ).where(Assistant.id == task.assistant_id)
            result = await session.execute(stmt)
            assistant = result.scalar_one_or_none()

            if not assistant:
                 logger.error(f"Task {task_id} failed: Assistant unavailable")
                 return
                 
            # Create Execution Record
            execution_record = ScheduledTaskExecution(
                task_id=task.id,
                status="RUNNING",
                started_at=datetime.utcnow()
            )
            session.add(execution_record)
            await session.commit()
            await session.refresh(execution_record)

            # 2. Execution Engine
            ai_engine = AIEngine(session)
            service = ChannelServiceFactory.get_service(channel)
            
            # We need to capture the full response for the log
            full_response = []
            
            async def _capture_and_yield():
                async for chunk in _ai_engine_stream_adapter(
                    ai_engine, 
                    assistant, 
                    task.prompt_template,
                    context_id=execution_record.task_id, # Use task_id as context (shared context for task) or execution_id?
                    # Using execution_id (UUID) is better for separation if we want per-run context (unlikely for now)
                    # Using task_id allows *some* continuity if we ever implement task memory.
                    user_id=task.owner_id
                ):
                    full_response.append(chunk)
                    yield chunk

            # 3. Stream & Send
            start_time = datetime.utcnow()
            await service.send_stream(task.target_identifier, _capture_and_yield())
            
            # 4. Finalize Record
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            execution_record.status = "COMPLETED"
            execution_record.completed_at = end_time
            execution_record.duration = f"{duration:.2f}s"
            execution_record.result_summary = "".join(full_response)
            
            # Deactivate if it was a one-time task
            if task.cron_expression.startswith("ONCE:"):
                task.is_active = False
                logger.info(f"One-time task {task_id} completed and deactivated.")

            await session.commit()
            logger.info(f"Task {task_id} completed. Duration: {duration}s")
            
        except Exception as e:
            logger.exception(f"Scheduled Task {task_id} failed: {e}")
            if execution_record:
                execution_record.status = "FAILED"
                execution_record.error_message = str(e)
                execution_record.completed_at = datetime.utcnow()
                await session.commit()

async def process_incoming_message(
    channel_id: uuid.UUID, 
    user_id: str, 
    text: str, 
    stream_id: Optional[str] = None
):
    """
    Process incoming message from a channel (webhook).
    This mimics what execute_scheduled_task does but triggered by an event.
    """
    logging.info(f"Processing incoming message for channel {channel_id} user {user_id}")
    # Implementation depends on logic...
    pass

