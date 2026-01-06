"""
OAuth Service Layer
"""
import uuid
import httpx
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple, Any
from urllib.parse import urlencode

from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.oauth2.rfc6749 import OAuth2Error
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from .oauth_models import OAuthProvider, OAuthUserLink, OAuthState
from .oauth_utils import token_encryption, generate_state, calculate_token_expiry, safe_get_nested_value
# Import custom provider handlers (will register automatically)
from .oauth_providers import get_provider_handler, has_custom_handler, get_token_fetcher, get_auth_url_builder
from . import oauth_providers  # Trigger registration of all provider handlers

logger = logging.getLogger(__name__)


class OAuthService:
    """OAuth Service Class"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._clients = {}  # Cache OAuth clients
    
    async def get_provider_by_name(self, name: str) -> Optional[OAuthProvider]:
        """Get OAuth provider by name"""
        result = await self.session.execute(
            select(OAuthProvider).where(
                OAuthProvider.name == name,
                OAuthProvider.is_active
            )
        )
        return result.scalar_one_or_none()
    
    async def get_oauth_client(self, provider: OAuthProvider) -> AsyncOAuth2Client:
        """Get or create OAuth client"""
        if provider.name not in self._clients:
            client = AsyncOAuth2Client(
                client_id=provider.client_id,
                client_secret=token_encryption.decrypt(provider.client_secret),
            )
            self._clients[provider.name] = client
        return self._clients[provider.name]
    
    async def create_authorization_url(
        self, 
        provider: OAuthProvider, 
        redirect_uri: str,
        extra_params: Optional[Dict[str, str]] = None,
        frontend_redirect_uri: Optional[str] = None
    ) -> Tuple[str, str]:
        """Create authorization URL
        
        Args:
            provider: OAuth provider
            redirect_uri: Backend callback URL
            extra_params: Extra authorization parameters
            frontend_redirect_uri: Frontend redirect URL (stored in state)
        
        Returns:
            Tuple[Authorization URL, state parameter]
        """
        state = generate_state()
        
        # If frontend redirect URI is provided, store it in extra_data
        extra_data = {}
        if frontend_redirect_uri:
            extra_data['frontend_redirect_uri'] = frontend_redirect_uri
        
        # Store state info in database (redirect_uri is backend callback URL)
        await self.store_oauth_state(state, provider.name, redirect_uri, extra_data)

        # Check for custom auth url builder
        custom_builder = get_auth_url_builder(provider.name)
        if custom_builder:
            logger.info(f"Using custom auth url builder for provider {provider.name}")
            return custom_builder(provider, redirect_uri, state, extra_params), state
        
        # Parse existing query parameters from auth_url
        from urllib.parse import urlparse, parse_qsl, urlunparse
        
        parsed_url = urlparse(provider.auth_url)
        existing_params = dict(parse_qsl(parsed_url.query))
        
        # Build authorization parameters (override existing if collision)
        params = existing_params.copy()
        params.update({
            'response_type': 'code',
            'client_id': provider.client_id,
            'redirect_uri': redirect_uri,
            'scope': ' '.join(provider.scopes),
            'state': state,
        })
        
        # Add extra parameters
        if extra_params:
            params.update(extra_params)
        
        # Build authorization URL (reconstruct without query first, then add)
        # Handle case where auth_url might have fragment
        url_without_query = urlunparse(parsed_url._replace(query=''))
        auth_url = f"{url_without_query}?{urlencode(params)}"
        
        # Restore fragment if it was lost (though usually auth endpoints don't have fragments, but WeCom has #wechat_redirect)
        if parsed_url.fragment:
             auth_url = f"{auth_url}#{parsed_url.fragment}"
        
        logger.info(f"Created authorization URL for provider {provider.name}")
        return auth_url, state
    
    async def handle_callback(
        self, 
        provider: OAuthProvider, 
        code: str, 
        state: str,
        redirect_uri: str
    ) -> Dict[str, Any]:
        """Handle OAuth callback
        
        Returns:
            Dictionary containing token and user_info
        """
        logger.info(f"Starting OAuth callback processing - provider: {provider.name}, "
                   f"code: {code[:20]}..., state: {state}")
        
        try:
            # Verify state
            logger.debug("Verifying OAuth state parameter")
            state_info = await self.verify_oauth_state(state, provider.name)
            if not state_info:
                error_msg = f"Invalid or expired state parameter - state: {state}, provider: {provider.name}"
                logger.error(error_msg)
                raise ValueError("Invalid or expired state parameter")
            
            logger.info(f"OAuth state verified successfully - provider: {provider.name}")
            
            client = await self.get_oauth_client(provider)
            logger.debug(f"OAuth client initialized for provider: {provider.name}")
            
            # Get access token
            logger.info(f"Fetching access token from provider: {provider.name}")
            token_data = await self.fetch_access_token(
                client, provider, code, redirect_uri
            )
            logger.info(f"Access token received successfully from provider: {provider.name}")
            
            # Get user info
            logger.info(f"Fetching user info from provider: {provider.name}")
            # Pass code to fetch_user_info if supported (e.g. for WeCom which needs code + app_token)
            user_info = await self.fetch_user_info(provider, token_data['access_token'], code=code)
            user_identifier = user_info.get('email') or user_info.get('login') or user_info.get('id')
            logger.info(f"User info received successfully from provider: {provider.name}, user: {user_identifier}")
            
            logger.info(f"OAuth callback completed successfully for provider: {provider.name}")
            return {
                'token': token_data,
                'user_info': user_info,
                'raw_user_info': user_info.get('raw_data', {}),
                'state_info': {
                    'redirect_uri': state_info.redirect_uri,  # Backend callback URL
                    'frontend_redirect_uri': state_info.extra_data.get('frontend_redirect_uri') if state_info.extra_data else None,
                    'extra_data': state_info.extra_data
                }
            }
            
        except ValueError as ve:
            # Re-raise ValueError (state validation failed etc.)
            logger.error(f"OAuth callback validation error for provider {provider.name}: {ve}")
            raise
        except Exception as e:
            logger.error(f"OAuth callback error for provider {provider.name}: {e}", exc_info=True)
            logger.error(f"OAuth callback error details - provider: {provider.name}, "
                        f"code: {code[:20] if code else 'None'}..., state: {state}")
            raise
    
    async def fetch_access_token(
        self, 
        client: AsyncOAuth2Client,
        provider: OAuthProvider, 
        code: str, 
        redirect_uri: str
    ) -> Dict[str, Any]:
        """Fetch access token"""
        # Check for custom token fetcher
        custom_fetcher = get_token_fetcher(provider.name)
        if custom_fetcher:
            logger.info(f"Using custom token fetcher for provider {provider.name}")
            return await custom_fetcher(provider, code, redirect_uri)

        token_data = {
            'grant_type': 'authorization_code',
            'client_id': provider.client_id,
            'client_secret': token_encryption.decrypt(provider.client_secret),
            'code': code,
            'redirect_uri': redirect_uri,
        }

        logger.debug(f"token_data: {token_data}")
        
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                provider.token_url,
                data=token_data,
                headers=headers
            )
            response.raise_for_status()
            
            token_response = response.json()
            
            # Check for errors
            if 'error' in token_response:
                raise OAuth2Error(token_response.get('error_description', 'Token request failed'))
            
            return token_response
    
    async def fetch_user_info(
        self, 
        provider: OAuthProvider, 
        access_token: str,
        code: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch user info
        
        Prefer using custom provider handler (e.g., GitHub), otherwise use generic logic
        """
        async with httpx.AsyncClient() as client:
            # Check for custom handler
            custom_handler = get_provider_handler(provider.name)
            
            if custom_handler:
                logger.info(f"Using custom handler for provider: {provider.name}")
                try:
                    # Support passing code for providers like WeCom
                    raw_user_data = await custom_handler(provider, access_token, client, code=code)
                except TypeError:
                    # Fallback for handlers not accepting kwargs
                    raw_user_data = await custom_handler(provider, access_token, client)
            else:
                # Generic processing logic
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Accept': 'application/json',
                }
                
                response = await client.get(provider.user_info_url, headers=headers)
                response.raise_for_status()
                raw_user_data = response.json()
            
            # Map user fields (config driven)
            mapped_user_info = self.map_user_fields(raw_user_data, provider.user_mapping)
            mapped_user_info['raw_data'] = raw_user_data
            
            return mapped_user_info
    
    def map_user_fields(self, raw_data: Dict[str, Any], field_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Map user fields"""
        mapped_data = {}
        
        for local_field, remote_field_path in field_mapping.items():
            value = safe_get_nested_value(raw_data, remote_field_path)
            if value is not None:
                mapped_data[local_field] = value
        
        return mapped_data
    
    async def store_oauth_state(
        self, 
        state: str, 
        provider_name: str, 
        redirect_uri: str,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Store OAuth state"""
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        logger.info(
            f"Storing OAuth state - state: {state}, provider: {provider_name}, "
            f"expires_at: {expires_at.isoformat()}"
        )
        logger.debug(
            f"OAuth state details - redirect_uri: {redirect_uri}, extra_data: {extra_data}"
        )
        
        oauth_state = OAuthState(
            state=state,
            provider_name=provider_name,
            redirect_uri=redirect_uri,
            expires_at=expires_at,  # Expires in 10 minutes
            extra_data=extra_data or {}
        )
        
        self.session.add(oauth_state)
        await self.session.commit()
        logger.debug("OAuth state stored successfully in database")
        
        # Verify storage success
        verify_result = await self.session.execute(
            select(OAuthState).where(OAuthState.state == state)
        )
        stored_state = verify_result.scalar_one_or_none()
        if stored_state:
            logger.debug(f"OAuth state storage verified - id: {stored_state.id}")
        else:
            logger.error(f"OAuth state storage verification failed - state not found: {state}")
    
    async def verify_oauth_state(self, state: str, provider_name: str) -> Optional[OAuthState]:
        """Verify OAuth state"""
        logger.debug(f"Verifying OAuth state - state: {state}, provider: {provider_name}")
        
        # First check if there is a matching state record in the database (ignoring expiration time)
        all_states_result = await self.session.execute(
            select(OAuthState).where(
                OAuthState.state == state,
                OAuthState.provider_name == provider_name
            )
        )
        all_matching_states = all_states_result.scalars().all()
        logger.debug(f"Found {len(all_matching_states)} state records matching state+provider")
        
        current_time = datetime.now(timezone.utc)
        for state_record in all_matching_states:
            logger.debug(
                f"State record: id={state_record.id}, expires_at={state_record.expires_at}, "
                f"current_time={current_time}, is_expired={state_record.expires_at <= current_time}"
            )
        
        # Now query for non-expired records
        result = await self.session.execute(
            select(OAuthState).where(
                OAuthState.state == state,
                OAuthState.provider_name == provider_name,
                OAuthState.expires_at > current_time
            )
        )
        
        oauth_state = result.scalar_one_or_none()
        
        if oauth_state:
            logger.info(f"OAuth state verification successful - state: {state}, provider: {provider_name}")
            # Delete used state
            await self.session.delete(oauth_state)
            await self.session.commit()
            logger.debug("OAuth state record deleted after successful verification")
        else:
            logger.warning(f"OAuth state verification failed - state: {state}, provider: {provider_name}")
            # Check if record exists but is expired
            expired_result = await self.session.execute(
                select(OAuthState).where(
                    OAuthState.state == state,
                    OAuthState.provider_name == provider_name,
                    OAuthState.expires_at <= current_time
                )
            )
            expired_state = expired_result.scalar_one_or_none()
            if expired_state:
                logger.error(
                    f"OAuth state found but expired - state: {state}, provider: {provider_name}, "
                    f"expired_at: {expired_state.expires_at}, current_time: {current_time}"
                )
            else:
                logger.error(f"OAuth state not found in database - state: {state}, provider: {provider_name}")
        
        return oauth_state
    
    async def get_user_oauth_links(self, user_id: uuid.UUID) -> list[OAuthUserLink]:
        """Get user OAuth links"""
        result = await self.session.execute(
            select(OAuthUserLink)
            .options(selectinload(OAuthUserLink.provider))
            .where(OAuthUserLink.user_id == user_id)
        )
        return result.scalars().all()
    
    async def get_oauth_link(
        self, 
        provider_id: uuid.UUID, 
        provider_user_id: str
    ) -> Optional[OAuthUserLink]:
        """Get OAuth user link"""
        result = await self.session.execute(
            select(OAuthUserLink).where(
                OAuthUserLink.provider_id == provider_id,
                OAuthUserLink.provider_user_id == provider_user_id
            )
        )
        return result.scalar_one_or_none()
    
    async def create_oauth_link(
        self,
        user_id: uuid.UUID,
        provider: OAuthProvider,
        provider_user_info: Dict[str, Any],
        token_data: Dict[str, Any]
    ) -> OAuthUserLink:
        """Create OAuth user link"""
        expires_at = None
        if 'expires_in' in token_data:
            expires_at = calculate_token_expiry(token_data['expires_in'])
        
        oauth_link = OAuthUserLink(
            user_id=user_id,
            provider_id=provider.id,
            provider_user_id=str(provider_user_info.get('id')),
            provider_username=provider_user_info.get('username'),
            provider_email=provider_user_info.get('email'),
            provider_avatar=provider_user_info.get('avatar'),
            access_token=token_encryption.encrypt(token_data.get('access_token', '')),
            refresh_token=token_encryption.encrypt(token_data.get('refresh_token', '')),
            token_expires_at=expires_at,
            raw_user_info=provider_user_info.get('raw_data', {}),
            linked_at=datetime.now(timezone.utc)
        )
        
        self.session.add(oauth_link)
        await self.session.commit()
        await self.session.refresh(oauth_link)
        
        return oauth_link
    
    async def update_oauth_link_token(
        self, 
        oauth_link: OAuthUserLink, 
        token_data: Dict[str, Any]
    ) -> None:
        """Update OAuth link token info"""
        oauth_link.access_token = token_encryption.encrypt(token_data.get('access_token', ''))
        if 'refresh_token' in token_data:
            oauth_link.refresh_token = token_encryption.encrypt(token_data['refresh_token'])
        
        if 'expires_in' in token_data:
            oauth_link.token_expires_at = calculate_token_expiry(token_data['expires_in'])
        
        oauth_link.last_login_at = datetime.now(timezone.utc)
        
        await self.session.commit()
    
    async def unlink_oauth_provider(self, user_id: uuid.UUID, provider_id: uuid.UUID) -> bool:
        """Unlink OAuth provider"""
        result = await self.session.execute(
            select(OAuthUserLink).where(
                OAuthUserLink.user_id == user_id,
                OAuthUserLink.provider_id == provider_id
            )
        )
        
        oauth_link = result.scalar_one_or_none()
        if oauth_link:
            await self.session.delete(oauth_link)
            await self.session.commit()
            return True
        
        return False
    
    async def cleanup_expired_states(self) -> None:
        """Cleanup expired state records"""
        await self.session.execute(
            delete(OAuthState).where(OAuthState.expires_at < datetime.now(timezone.utc))
        )
        await self.session.commit()


def get_oauth_service(session: AsyncSession) -> OAuthService:
    """Get OAuth service instance"""
    return OAuthService(session)