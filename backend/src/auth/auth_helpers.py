"""
Authentication Helper Functions
"""
import logging
from typing import Optional
from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.auth.refresh_token_service import get_refresh_token_service
from src.auth.fastapi_users import get_jwt_strategy
from src.users.models import User

logger = logging.getLogger(__name__)


async def set_auth_cookies(
    response: Response,
    user: User,
    request: Request,
    session: AsyncSession
) -> None:
    """
    Set authentication cookies (Access Token + Refresh Token)
    
    Args:
        response: FastAPI Response object
        user: User object
        request: FastAPI Request object (used to get User-Agent)
        session: Database session
    """
    # 1. Generate Access Token
    jwt_strategy = get_jwt_strategy()
    access_token = await jwt_strategy.write_token(user)
    
    # Set Access Token Cookie
    # ⭐ Access Token is sent on all paths (path="/")
    response.set_cookie(
        key="access-token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_LIFETIME_SECONDS,
        path="/"  # Carried by all API requests
    )
    
    logger.debug(f"Set access token for user {user.id}")
    
    # 2. Generate Refresh Token
    token_service = get_refresh_token_service(session)
    device_info = request.headers.get("user-agent")
    
    refresh_token, _ = await token_service.create_refresh_token(
        user_id=user.id,
        device_info=device_info
    )
    
    # Set Refresh Token Cookie
    # ⭐ Refresh Token is only sent on refresh endpoint, improving security
    # This prevents Refresh Token from being exposed in every API request
    response.set_cookie(
        key="refresh-token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_LIFETIME_SECONDS,
        path="/api/v1/auth/refresh"  # Only sent on refresh endpoint
    )
    
    logger.info(f"Set refresh token for user {user.id} (limited to refresh endpoint)")


async def clear_auth_cookies(
    response: Response,
    refresh_token: Optional[str],
    session: AsyncSession
) -> None:
    """
    Clear authentication cookies and revoke Refresh Token
    
    Args:
        response: FastAPI Response object
        refresh_token: Refresh Token (for revocation)
        session: Database session
    """
    # Clear Cookie
    # ⭐ Must specify the same path as when setting, otherwise cannot be deleted correctly
    response.delete_cookie(key="access-token", path="/")
    response.delete_cookie(key="refresh-token", path="/api/v1/auth/refresh")
    
    # Revoke Refresh Token
    if refresh_token:
        token_service = get_refresh_token_service(session)
        refresh_token_obj = await token_service.verify_refresh_token(refresh_token)
        if refresh_token_obj:
            await token_service.revoke_token(refresh_token_obj.id)
            logger.info(f"Revoked refresh token for user {refresh_token_obj.user_id}")
