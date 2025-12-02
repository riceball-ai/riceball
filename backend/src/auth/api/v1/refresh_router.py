"""
Token Refresh API Router
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from src.database import get_async_session
from src.config import settings
from src.auth.refresh_token_service import get_refresh_token_service
from src.auth.fastapi_users import get_jwt_strategy
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


class RefreshResponse(BaseModel):
    """Refresh Token Response"""
    access_token: str
    token_type: str = "bearer"


class LogoutAllResponse(BaseModel):
    """Logout All Devices Response"""
    success: bool
    message: str
    revoked_count: int


@router.post("/auth/refresh", response_model=RefreshResponse)
async def refresh_access_token(
    request: Request,
    response: Response,
    refresh_token: Optional[str] = Cookie(None, alias="refresh-token"),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Refresh Access Token
    
    Use Refresh Token to get new Access Token
    If Token Rotation is enabled, also returns new Refresh Token
    """
    if not refresh_token:
        logger.warning("Refresh token missing in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing"
        )
    
    # Verify Refresh Token
    token_service = get_refresh_token_service(session)
    refresh_token_obj = await token_service.verify_refresh_token(refresh_token)
    
    if not refresh_token_obj:
        logger.warning("Invalid or expired refresh token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    logger.info(f"Refreshing tokens for user {refresh_token_obj.user_id}")
    
    # Generate new Access Token
    from src.auth.dependencies import get_user_db
    
    user_db_gen = get_user_db(session)
    user_db = await user_db_gen.__anext__()
    
    user = await user_db.get(refresh_token_obj.user_id)
    if not user or not user.is_active:
        logger.error(f"User {refresh_token_obj.user_id} not found or inactive")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Use JWT Strategy to generate new Access Token
    jwt_strategy = get_jwt_strategy()
    access_token = await jwt_strategy.write_token(user)
    
    # Set Access Token Cookie
    # ⭐ Access Token is available on all paths
    response.set_cookie(
        key="access-token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_LIFETIME_SECONDS,
        path="/"  # All paths
    )
    
    # Token Rotation (Optional)
    if settings.REFRESH_TOKEN_ROTATION_ENABLED:
        # Get device info
        device_info = request.headers.get("user-agent")
        
        # Rotate Refresh Token
        new_refresh_token, _ = await token_service.rotate_token(
            old_token=refresh_token_obj,
            device_info=device_info
        )
        
        # Set new Refresh Token Cookie
        # ⭐ Refresh Token is only available on refresh endpoint, improving security
        response.set_cookie(
            key="refresh-token",
            value=new_refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=settings.REFRESH_TOKEN_LIFETIME_SECONDS,
            path="/api/v1/auth/refresh"  # Refresh endpoint only
        )
        
        logger.info(f"Rotated refresh token for user {user.id}")
    
    logger.info(f"Tokens refreshed successfully for user {user.id}")
    
    return RefreshResponse(
        access_token=access_token,
        token_type="bearer"
    )


@router.post("/auth/logout-all", response_model=LogoutAllResponse)
async def logout_all_devices(
    request: Request,
    response: Response,
    refresh_token: Optional[str] = Cookie(None, alias="refresh-token"),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Logout all devices
    
    Revoke all Refresh Tokens for user
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing"
        )
    
    # Verify current Refresh Token
    token_service = get_refresh_token_service(session)
    refresh_token_obj = await token_service.verify_refresh_token(refresh_token)
    
    if not refresh_token_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Revoke all tokens
    revoked_count = await token_service.revoke_all_user_tokens(refresh_token_obj.user_id)
    
    # Clear current session cookies
    # ⭐ Must specify same path as when set
    response.delete_cookie(key="access-token", path="/")
    response.delete_cookie(key="refresh-token", path="/api/v1/auth/refresh")
    
    logger.info(f"Logged out all devices for user {refresh_token_obj.user_id}, revoked {revoked_count} tokens")
    
    return LogoutAllResponse(
        success=True,
        message="Logged out from all devices",
        revoked_count=revoked_count
    )
