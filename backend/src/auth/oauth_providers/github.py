"""
GitHub OAuth Custom Handler

GitHub API Features:
1. /user endpoint does not return email by default (even with user:email scope)
2. Need to call /user/emails separately to get email list
3. Email list may contain multiple, need to select primary + verified one
"""

import logging
from typing import Dict, Any
import httpx

from . import register_provider_handler
from ..oauth_models import OAuthProvider

logger = logging.getLogger(__name__)


@register_provider_handler("github")
async def fetch_github_user_info(
    provider: OAuthProvider,
    access_token: str,
    client: httpx.AsyncClient
) -> Dict[str, Any]:
    """
    Fetch GitHub user info
    
    Args:
        provider: OAuth provider configuration
        access_token: Access token
        client: HTTP client
        
    Returns:
        Dictionary containing user info, ensuring email field is included
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 1. Get basic user info
    user_response = await client.get(provider.user_info_url, headers=headers)
    user_response.raise_for_status()
    user_info = user_response.json()
    
    logger.debug(f"GitHub user info: {user_info}")
    
    # 2. If email is missing in basic info, try fetching from /user/emails
    if not user_info.get("email"):
        logger.info("GitHub user info missing email, fetching from /user/emails")
        try:
            emails_response = await client.get(
                "https://api.github.com/user/emails",
                headers=headers
            )
            emails_response.raise_for_status()
            emails = emails_response.json()
            
            logger.debug(f"GitHub user emails: {emails}")
            
            # Find primary and verified email
            primary_email = next(
                (e for e in emails if e.get("primary") and e.get("verified")),
                None
            )
            
            if primary_email:
                user_info["email"] = primary_email["email"]
                logger.info(f"Found primary verified email: {primary_email['email']}")
            else:
                # If no primary + verified, try finding any verified one
                verified_email = next(
                    (e for e in emails if e.get("verified")),
                    None
                )
                if verified_email:
                    user_info["email"] = verified_email["email"]
                    logger.info(f"Found verified email: {verified_email['email']}")
                else:
                    logger.warning("No verified email found for GitHub user")
                    
        except Exception as e:
            logger.error(f"Failed to fetch GitHub user emails: {e}")
    
    return user_info
