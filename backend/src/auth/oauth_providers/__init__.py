"""
OAuth Provider Plugin System

Supports two ways:
1. Configuration driven (default): Automatically handled by user_mapping configured in database
2. Custom handler: Register dedicated logic for special providers
"""

import logging
from typing import Dict, Optional, Callable, Any
import httpx
from ..oauth_models import OAuthProvider

logger = logging.getLogger(__name__)

# Provider specific user info fetcher type
# access_token, client -> user_info
ProviderUserInfoFetcher = Callable[[OAuthProvider, str, httpx.AsyncClient], Dict[str, Any]]

# Provider specific access token fetcher type
# provider, code, redirect_uri -> Dict[str, Any] (token_data)
# Note: May handle client creation internally or return special token structure
ProviderTokenFetcher = Callable[[OAuthProvider, str, str], Dict[str, Any]]

# Provider specific auth url builder type
# provider, redirect_uri, state, extra_params -> Tuple[str, str] (auth_url, state)
# Note: Allows full customization of auth url construction (e.g. parameter names like appid vs client_id)
ProviderAuthUrlBuilder = Callable[[OAuthProvider, str, str, Optional[Dict[str, str]]], str]

# Registry: provider_name -> custom handler function
_USER_INFO_HANDLERS: Dict[str, ProviderUserInfoFetcher] = {}
_TOKEN_FETCH_HANDLERS: Dict[str, ProviderTokenFetcher] = {}
_AUTH_URL_BUILDERS: Dict[str, ProviderAuthUrlBuilder] = {}


def register_provider_handler(provider_name: str):
    """
    Decorator: Register custom OAuth provider user info handler
    """
    def decorator(func: ProviderUserInfoFetcher):
        _USER_INFO_HANDLERS[provider_name.lower()] = func
        logger.info(f"Registered OAuth user info handler: {provider_name}")
        return func
    return decorator


def register_token_fetcher(provider_name: str):
    """
    Decorator: Register custom OAuth provider token fetcher
    """
    def decorator(func: ProviderTokenFetcher):
        _TOKEN_FETCH_HANDLERS[provider_name.lower()] = func
        logger.info(f"Registered OAuth token fetcher: {provider_name}")
        return func
    return decorator


def register_auth_url_builder(provider_name: str):
    """
    Decorator: Register custom OAuth provider auth url builder
    """
    def decorator(func: ProviderAuthUrlBuilder):
        _AUTH_URL_BUILDERS[provider_name.lower()] = func
        logger.info(f"Registered OAuth auth url builder: {provider_name}")
        return func
    return decorator


def get_provider_handler(provider_name: str) -> Optional[ProviderUserInfoFetcher]:
    """Get custom user info handler for provider"""
    return _USER_INFO_HANDLERS.get(provider_name.lower())


def get_token_fetcher(provider_name: str) -> Optional[ProviderTokenFetcher]:
    """Get custom token fetcher for provider"""
    return _TOKEN_FETCH_HANDLERS.get(provider_name.lower())


def get_auth_url_builder(provider_name: str) -> Optional[ProviderAuthUrlBuilder]:
    """Get custom auth url builder for provider"""
    return _AUTH_URL_BUILDERS.get(provider_name.lower())


def has_custom_handler(provider_name: str) -> bool:
    """Check if provider has custom user info handler"""
    return provider_name.lower() in _USER_INFO_HANDLERS


# Import all provider handlers (trigger decorator registration)
from . import github  # noqa: F401, E402
from . import wecom  # noqa: F401, E402

logger.info(f"OAuth provider handlers loaded: {list(_USER_INFO_HANDLERS.keys())}")
