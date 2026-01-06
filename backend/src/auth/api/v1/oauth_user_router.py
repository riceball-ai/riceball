"""
OAuth API Router
"""
import logging
from typing import List
from urllib.parse import urljoin

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import get_async_session
from src.config import settings
from src.auth import current_active_user
from src.users.models import User
from ...oauth_models import OAuthProvider
from ...oauth_service import get_oauth_service
from ...oauth_schemas import (
    OAuthAuthorizationRequest,
    OAuthAuthorizationResponse,
    OAuthCallbackResponse,
    OAuthProviderPublic,
    OAuthUserLinksResponse,
    OAuthUnlinkRequest,
    OAuthUnlinkResponse
)
from ...manager import get_user_manager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/oauth/providers", response_model=List[OAuthProviderPublic])
async def list_oauth_providers(
    session: AsyncSession = Depends(get_async_session)
) -> List[OAuthProviderPublic]:
    """Get list of available OAuth providers"""
    logger.info("Fetching available OAuth providers list")
    try:
        result = await session.execute(
            select(OAuthProvider)
            .where(OAuthProvider.is_active)
            .order_by(OAuthProvider.sort_order)
        )
        providers = result.scalars().all()
        logger.info(f"Found {len(providers)} active OAuth providers")
        return providers
    except Exception as e:
        logger.error(f"Error fetching OAuth providers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch OAuth providers")


@router.post("/oauth/{provider_name}/authorize", response_model=OAuthAuthorizationResponse)
async def oauth_authorize(
    provider_name: str,
    request_data: OAuthAuthorizationRequest,
    request: Request,
    session: AsyncSession = Depends(get_async_session)
) -> OAuthAuthorizationResponse:
    """Initiate OAuth authorization"""
    logger.info(f"OAuth authorization request for provider: {provider_name}")
    logger.debug(f"Authorization request data: {request_data}")
    
    try:
        oauth_service = get_oauth_service(session)
        
        # Get provider
        provider = await oauth_service.get_provider_by_name(provider_name)
        if not provider:
            logger.error(f"OAuth provider not found: {provider_name}")
            raise HTTPException(status_code=404, detail="OAuth provider not found")
        
        logger.info(f"OAuth provider found: {provider.name} (ID: {provider.id})")
        
        # Build callback URL - Use configured external URL instead of internal service URL
        if hasattr(settings, 'EXTERNAL_URL') and settings.EXTERNAL_URL:
            # Use configured external URL
            base_url = str(settings.EXTERNAL_URL).rstrip('/')
            backend_callback_uri = f"{base_url}/api/v1/oauth/{provider_name}/callback"
            logger.debug(f"Using external URL for callback: {backend_callback_uri}")
        else:
            # Fallback to request URL (might be internal service name)
            backend_callback_uri = str(request.url_for("oauth_callback", provider_name=provider_name))
            logger.debug(f"Using request URL for callback: {backend_callback_uri}")
        
        # Create authorization URL - Store frontend provided redirect_uri in state
        authorization_url, state = await oauth_service.create_authorization_url(
            provider=provider,
            redirect_uri=backend_callback_uri,
            extra_params=None,
            frontend_redirect_uri=request_data.redirect_uri  # Pass frontend redirect URI
        )
        
        logger.info(f"OAuth authorization URL created for provider: {provider_name}")
        logger.debug(f"Authorization URL: {authorization_url}")
        logger.debug(f"State parameter: {state}")
        
        return OAuthAuthorizationResponse(
            authorization_url=authorization_url,
            state=state
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"OAuth authorization error for {provider_name}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create authorization URL")


# Support both trailing slash and no trailing slash for callback
@router.get("/oauth/{provider_name}/callback/", response_model=OAuthCallbackResponse, include_in_schema=False)
@router.get("/oauth/{provider_name}/callback", response_model=OAuthCallbackResponse)
async def oauth_callback(
    provider_name: str,
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="CSRF state parameter"),
    error: str = Query(None, description="OAuth error"),
    request: Request = None,
    session: AsyncSession = Depends(get_async_session)
):
    """Handle OAuth callback"""
    logger.info(f"OAuth callback initiated for provider: {provider_name}")
    logger.debug(f"OAuth callback parameters - code: {code[:10]}..., state: {state}, error: {error}")
    
    # Check for errors
    if error:
        logger.error(f"OAuth callback received error for {provider_name}: {error}")
        raise HTTPException(status_code=400, detail=f"OAuth authorization failed: {error}")
    
    try:
        oauth_service = get_oauth_service(session)
        logger.debug(f"OAuth service initialized for provider: {provider_name}")
        
        # Get provider
        provider = await oauth_service.get_provider_by_name(provider_name)
        if not provider:
            logger.error(f"OAuth provider not found: {provider_name}")
            raise HTTPException(status_code=404, detail="OAuth provider not found")
        
        logger.info(f"OAuth provider found: {provider.name} (ID: {provider.id})")
    except Exception as e:
        logger.error(f"Error initializing OAuth service or getting provider {provider_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to initialize OAuth service")
    
    try:
        # Build callback URL - Use configured external URL instead of internal service URL
        if hasattr(settings, 'EXTERNAL_URL') and settings.EXTERNAL_URL:
            # Use configured external URL
            base_url = str(settings.EXTERNAL_URL).rstrip('/')
            backend_callback_uri = f"{base_url}/api/v1/oauth/{provider_name}/callback"
            logger.debug(f"Using external URL for callback: {backend_callback_uri}")
        else:
            # Fallback to request URL (might be internal service name)
            backend_callback_uri = str(request.url_for("oauth_callback", provider_name=provider_name))
            logger.debug(f"Using request URL for callback: {backend_callback_uri}")
        
        logger.info(f"Starting OAuth callback processing for {provider_name}")
        # Handle callback
        oauth_data = await oauth_service.handle_callback(
            provider=provider,
            code=code,
            state=state,
            redirect_uri=backend_callback_uri
        )
        logger.info(f"OAuth callback processed successfully for {provider_name}")
        logger.debug(f"OAuth user info: {oauth_data.get('user_info', {})}")
        
        # Get user manager
        logger.debug("Initializing user database and manager")
        from ...dependencies import get_user_db
        user_db_gen = get_user_db(session)
        user_db = await user_db_gen.__anext__()
        
        user_manager_gen = get_user_manager(user_db)
        user_manager = await user_manager_gen.__anext__()
        logger.debug("User database and manager initialized successfully")
        
        # Login or create user (internally checks existing OAuth link)
        logger.info(f"Starting OAuth login/create process for {provider_name}")
        user, is_new_oauth_link = await user_manager.oauth_login_or_create(
            provider=provider,
            provider_user_info=oauth_data['user_info'],
            oauth_token=oauth_data['token']
        )
        logger.info(f"OAuth user login/create successful - user ID: {user.id}, email: {user.email}, new_oauth_link: {is_new_oauth_link}")
        
        # Get frontend redirect_uri stored in state
        state_info = oauth_data.get('state_info', {})
        frontend_redirect_uri = state_info.get('frontend_redirect_uri')
        
        if not frontend_redirect_uri:
            # Fallback to default success page
            frontend_redirect_uri = f"{str(settings.FRONTEND_URL).rstrip('/')}/auth/oauth/success"
            logger.warning(f"No frontend_redirect_uri found in state, using default: {frontend_redirect_uri}")
        else:
            logger.debug(f"Using stored frontend_redirect_uri from state: {frontend_redirect_uri}")
        
        # Use AuthenticationBackend for proper login processing
        logger.debug("Processing OAuth login through authentication backend")
        
        # Use custom auth cookie setting (includes Refresh Token)
        from src.auth.auth_helpers import set_auth_cookies
        
        # Create redirect response
        redirect_response = RedirectResponse(
            url=frontend_redirect_uri,
            status_code=302
        )
        
        # Set auth cookies (Access Token + Refresh Token)
        # Note: session is already a function argument, use directly
        await set_auth_cookies(redirect_response, user, request, session)
        
        logger.info(f"OAuth login successful for provider: {provider_name}, user: {user.id}, authentication cookies set")
        
        return redirect_response
        
    except Exception as e:
        logger.error(f"OAuth callback error for {provider_name}: {str(e)}", exc_info=True)
        logger.error(f"OAuth callback error details - provider: {provider_name}, code: {code[:10] if code else None}..., state: {state}")
        
        # Redirect to frontend error page
        error_redirect_url = f"{str(settings.FRONTEND_URL).rstrip('/')}/oauth/error"
        error_message = f"OAuth callback failed: {str(e)}"
        logger.error(f"Redirecting to error page: {error_redirect_url}?error={error_message}")
        
        return RedirectResponse(
            url=f"{error_redirect_url}?error={error_message}",
            status_code=302
        )


@router.get("/oauth/user/links", response_model=OAuthUserLinksResponse)
async def get_user_oauth_links(
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
) -> OAuthUserLinksResponse:
    """Get current user's OAuth links"""
    logger.info(f"Fetching OAuth links for user: {current_user.id}")
    try:
        oauth_service = get_oauth_service(session)
        
        links = await oauth_service.get_user_oauth_links(current_user.id)
        logger.info(f"Found {len(links)} OAuth links for user: {current_user.id}")
        
        return OAuthUserLinksResponse(links=links)
    except Exception as e:
        logger.error(f"Error fetching OAuth links for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch OAuth links")


@router.post("/oauth/user/unlink", response_model=OAuthUnlinkResponse)
async def unlink_oauth_provider(
    request_data: OAuthUnlinkRequest,
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
) -> OAuthUnlinkResponse:
    """Unlink OAuth provider"""
    logger.info(f"Unlinking OAuth provider {request_data.provider_id} for user: {current_user.id}")
    try:
        oauth_service = get_oauth_service(session)
        
        success = await oauth_service.unlink_oauth_provider(
            user_id=current_user.id,
            provider_id=request_data.provider_id
        )
        
        if success:
            logger.info(f"OAuth provider {request_data.provider_id} unlinked successfully for user: {current_user.id}")
            return OAuthUnlinkResponse(
                success=True,
                message="OAuth provider unlinked successfully"
            )
        else:
            logger.warning(f"OAuth provider link not found for provider {request_data.provider_id} and user: {current_user.id}")
            return OAuthUnlinkResponse(
                success=False,
                message="OAuth provider link not found"
            )
    except Exception as e:
        logger.error(f"Error unlinking OAuth provider {request_data.provider_id} for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to unlink OAuth provider")