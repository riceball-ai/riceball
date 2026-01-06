
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
    
    Requires:
    1. access_token (App Token)
    2. code (from callback)
    """
    if not code:
        raise ValueError("WeCom user info fetching requires 'code'")
        
    # 1. Get User Identity (UserId) using code and app token
    # https://qyapi.weixin.qq.com/cgi-bin/user/getuserinfo?access_token=ACCESS_TOKEN&code=CODE
    
    # Construct URL manually or use provider.user_info_url if it points to getuserinfo
    base_url = provider.user_info_url
    
    response = await client.get(base_url, params={
        "access_token": access_token,
        "code": code
    })
    response.raise_for_status()
    identity_data = response.json()
    
    if identity_data.get("errcode") != 0:
        raise ValueError(f"WeCom identity error: {identity_data.get('errmsg')}")
        
    user_id = identity_data.get("UserId")
    
    if user_id:
        # Internal User
        logger.info(f"WeCom user identified: {user_id}")
        
        # 2. Get User Details
        # https://qyapi.weixin.qq.com/cgi-bin/user/get?access_token=ACCESS_TOKEN&userid=USERID
        # We assume we can construct this URL based on the base URL logic or hardcode
        # Typically base_url is .../getuserinfo. We need .../user/get
        
        detail_url = base_url.replace("getuserinfo", "get")
        if detail_url == base_url:
             # Fallback if URL structure doesn't match expectation
             detail_url = "https://qyapi.weixin.qq.com/cgi-bin/user/get"
             
        detail_response = await client.get(detail_url, params={
            "access_token": access_token,
            "userid": user_id
        })
        detail_response.raise_for_status()
        user_detail = detail_response.json()
        
        if user_detail.get("errcode") == 0:
            # Merge identity info (like DeviceId) with user details
            user_detail.update(identity_data)
            return user_detail
        else:
            logger.warning(f"Failed to fetch WeCom user details: {user_detail.get('errmsg')}")
            return identity_data
            
    elif identity_data.get("OpenId"):
        # External User (not in corp)
        return identity_data
        
    return identity_data
