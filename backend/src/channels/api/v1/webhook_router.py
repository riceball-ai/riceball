import uuid
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_async_session
from src.channels.service import ChannelService

router = APIRouter(prefix="/channels")

@router.api_route("/webhook/{channel_id}", methods=["GET", "POST"])
async def channel_webhook(
    channel_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Public webhook endpoint for receiving events from third-party platforms.
    """
    # Note: No user authentication here, relies on request signature verification in adapter.
    service = ChannelService(session)
    try:
        result = await service.handle_webhook(channel_id, request)
        return result
    except HTTPException:
        raise
    except Exception as e:
        # We don't want to leak internal errors to external platforms, 
        # but we should log them.
        # Returning 500 might cause the provider to retry endlessly.
        # Depending on the error, sometimes 200 OK is safer to stop retries if it's a logic bug.
        # But for now, we let FastAPI handle it (returns 500).
        raise
