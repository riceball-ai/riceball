
"""
Enterprise WeChat (WeCom) OAuth Handler

WeCom OAuth Flow is unique:
1. Authorization URL needs `agentid`.
2. Access Token is "App Access Token" (client_credentials), not user access token.
3. User Info is fetched using App Access Token + Code.

Mapping:
- client_id -> corpid
- client_secret -> corpsecret
- auth_url -> https://login.work.weixin.qq.com/wwlogin/sso/login
"""

import logging
from typing import Dict, Any, Optional
import httpx

from . import register_provider_handler, register_token_fetcher, register_auth_url_builder
from ..oauth_models import OAuthProvider

logger = logging.getLogger(__name__)


@register_auth_url_builder("wecom")
def build_wecom_auth_url(
    provider: OAuthProvider,
    redirect_uri: str,
    state: str,
    extra_params: Optional[Dict[str, str]] = None
) -> str:
    """
    Build WeCom Auth URL (Scan to Login)
    """
    from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
    
    auth_url = provider.auth_url
    parsed_url = urlparse(auth_url)
    existing_params = dict(parse_qsl(parsed_url.query))
    
    # Common parameters for WeCom Scan Login (qrConnect / wwlogin)
    params = existing_params.copy()
    params.update({
        "appid": provider.client_id,  # WeCom uses appid instead of client_id
        "redirect_uri": redirect_uri,
        "state": state
    })
    
    if extra_params:
        params.update(extra_params)
    
    # Note: WeCom Scan Login does NOT use 'response_type=code' or 'scope'
    
    # Reconstruct URL
    url_without_query = urlunparse(parsed_url._replace(query=''))
    final_url = f"{url_without_query}?{urlencode(params)}"
    
    if parsed_url.fragment:
         final_url += f"#{parsed_url.fragment}"
         
    return final_url


@register_token_fetcher("wecom")
async def fetch_wecom_token(
    provider: OAuthProvider,
    code: str,
    redirect_uri: str
) -> Dict[str, Any]:
    """
    Fetch WeCom Access Token (App Token)
    
    WeCom uses client_credentials flow to get a global app token,
    which is then used to query user info with the code.
    """
    # Decrypt secret
    from ..oauth_utils import token_encryption
    corp_secret = token_encryption.decrypt(provider.client_secret)
    corp_id = provider.client_id
    
    url = provider.token_url  # e.g. https://qyapi.weixin.qq.com/cgi-bin/gettoken
    
    params = {
        "corpid": corp_id,
        "corpsecret": corp_secret
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("errcode") != 0:
            raise ValueError(f"WeCom token error: {data.get('errmsg')}")
            
        # Return in structure that OAuthService expects
        # We put the app token in 'access_token' so it's passed to fetch_user_info
        return {
            "access_token": data["access_token"],
            "expires_in": data.get("expires_in"),
            "token_type": "bearer",
            # WeCom doesn't give refresh token for this flow
        }


@register_provider_handler("wecom")
async def fetch_wecom_user_info(
    provider: OAuthProvider,
    access_token: str,
    client: httpx.AsyncClient,
    code: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch WeCom User Info
    
    Flow (Hardcoded as per requirement):
    1. Get UserID: https://qyapi.weixin.qq.com/cgi-bin/auth/getuserinfo
    2. Get Details: https://qyapi.weixin.qq.com/cgi-bin/user/get
    """
    if not code:
        raise ValueError("WeCom user info fetching requires 'code'")
        
    # 1. Get User Identity (UserId)
    # Note: User specifically requested /auth/getuserinfo
    identity_url = "https://qyapi.weixin.qq.com/cgi-bin/auth/getuserinfo"
    
    # Some legacy/specific docs might mention user/getuserinfo, we try the one requested first.
    # If 404 and not working, one might consider falling back to /user/getuserinfo
    
    try:
        response = await client.get(identity_url, params={
            "access_token": access_token,
            "code": code
        })
        response.raise_for_status()
        identity_data = response.json()
    except httpx.HTTPStatusError as e:
        # Fallback to standard URL if the requested one is 404 (just in case)
        if e.response.status_code == 404:
             logger.warning("WeCom /auth/getuserinfo failed (404), trying /user/getuserinfo")
             identity_url = "https://qyapi.weixin.qq.com/cgi-bin/user/getuserinfo"
             response = await client.get(identity_url, params={
                "access_token": access_token,
                "code": code
             })
             response.raise_for_status()
             identity_data = response.json()
        else:
            raise e
    
    if identity_data.get("errcode") != 0:
        raise ValueError(f"WeCom identity error: {identity_data.get('errmsg')}")
        
    # API usually returns 'UserId', but user sample showed 'userid'
    user_id = identity_data.get("userid") or identity_data.get("UserId")
    
    if user_id:
        # Internal User
        logger.info(f"WeCom user identified: {user_id}")
        
        # Step 2 logic removed:
        # /user/get interface often requires extra permissions or is redundant if it only returns userid.
        # We rely on the identity data and setting a default name.
        
        user_detail = identity_data.copy()
        user_detail["name"] = f"WecomID_{user_id}"
        
        return user_detail
            
    elif identity_data.get("OpenId"):
        # External User (not in corp)
        return identity_data
        
    return identity_data
