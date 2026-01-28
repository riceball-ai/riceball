import uuid
from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_async_session
from src.channels.service import ChannelService
try:
    from src.scheduler.executor import process_incoming_message
except ImportError:
    # If circular import or other issue, define a placeholder or handle gracefully
    # This might happen if executor imports something that imports this router
    async def process_incoming_message(*args, **kwargs):
        pass  # Placeholder

router = APIRouter(prefix="/channels")


@router.api_route("/webhook/{channel_id}", methods=["GET", "POST"])
async def channel_webhook(
    channel_id: uuid.UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session),
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
        result = await service.handle_webhook(channel_id, request)

        # 1. Handle Response Object directly (Handshake)
        # Note: service.handle_webhook might return a dict or Response.
        from starlette.responses import Response as StarletteResponse

        if isinstance(result, StarletteResponse):
            return result

        if isinstance(result, dict):
            # 2. Check for Async Task Payload
            if result.get("async_task_payload"):
                payload = result["async_task_payload"]
                background_tasks.add_task(
                    process_incoming_message,
                    channel_id=channel_id,
                    user_id=payload["user_id"],
                    text=payload["content"],
                    stream_id=payload.get("stream_id"),
                )

            # 3. Check for Direct Response (Stream Poll or Init)
            if result.get("direct_response"):
                return result["direct_response"]

            # 4. If processed async but no direct response, return generic status
            if result.get("async_task_payload"):
                return {"status": "processing"}

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise
