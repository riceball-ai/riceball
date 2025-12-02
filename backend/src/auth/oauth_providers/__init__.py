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
ProviderUserInfoFetcher = Callable[[OAuthProvider, str, httpx.AsyncClient], Dict[str, Any]]

# Registry: provider_name -> custom handler function
_PROVIDER_HANDLERS: Dict[str, ProviderUserInfoFetcher] = {}


def register_provider_handler(provider_name: str):
    """
    Decorator: Register custom OAuth provider handler
    
    Usage:
        @register_provider_handler("github")
        async def fetch_github_user_info(provider, access_token, client):
            ...
    """
    def decorator(func: ProviderUserInfoFetcher):
        _PROVIDER_HANDLERS[provider_name.lower()] = func
        logger.info(f"Registered OAuth provider handler: {provider_name}")
        return func
    return decorator


def get_provider_handler(provider_name: str) -> Optional[ProviderUserInfoFetcher]:
    """Get custom handler for provider (if exists)"""
    return _PROVIDER_HANDLERS.get(provider_name.lower())


def has_custom_handler(provider_name: str) -> bool:
    """Check if provider has custom handler"""
    return provider_name.lower() in _PROVIDER_HANDLERS


# Import all provider handlers (trigger decorator registration)
from . import github  # noqa: F401, E402

logger.info(f"OAuth provider handlers loaded: {list(_PROVIDER_HANDLERS.keys())}")
