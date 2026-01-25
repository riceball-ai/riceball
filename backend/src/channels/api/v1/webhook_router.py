import uuid
from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_async_session
from src.channels.service import ChannelService
from src.scheduler.executor import process_incoming_message

router = APIRouter(prefix="/channels")

@router.api_route("/webhook/{channel_id}", methods=["GET", "POST"])
async def channel_webhook(
    channel_id: uuid.UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Public webhook endpoint for receiving events from third-party platforms.
    Now operating in ASYNC mode:
    1. Verify signature
    2. Enqueue background task
    3. Return 200 OK immediately
    """
    service = ChannelService(session)
    try:
        # Pre-process: Verify signature and parse body in Sync
        # We need check if it is a Handshake (GET/special POST)
        # If Handshake, we must return response immediately.
        
        # NOTE: service.handle_webhook contains logic for both Handshake and Message parsing.
        # We need to refactor or peek into it.
        # Current implementation of handle_webhook executes logic.
        # We need to separate "Validation/Handshake" from "Execution".
        
        # Let's delegate to service, but service needs to be smart enough:
        # If it returns a "message" object, we spawn background task.
        # If it returns a "response" (handshake), we return it.
        
        result = await service.handle_webhook(channel_id, request)
        
        # If result contains an 'incoming_message' equivalent or indicator to process async
        if isinstance(result, dict) and result.get("async_task_payload"):
             payload = result["async_task_payload"]
             background_tasks.add_task(
                 process_incoming_message,
                 channel_id=channel_id,
                 user_id=payload["user_id"],
                 text=payload["content"]
             )
             return {"status": "processing"}
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise
