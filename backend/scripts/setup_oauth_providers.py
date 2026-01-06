#!/usr/bin/env python3
"""
OAuth Provider Configuration Example Script

This script demonstrates how to configure common OAuth providers (Google, GitHub, Custom SSO)
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database import async_session_maker
from src.auth.oauth_models import OAuthProvider
from src.auth.oauth_utils import token_encryption


async def create_google_provider():
    """Create Google OAuth provider configuration"""
    provider = OAuthProvider(
        name="google",
        display_name="Google",
        description="Login with Google account",
        client_id="your-google-client-id.googleusercontent.com",
        client_secret=token_encryption.encrypt("your-google-client-secret"),
        auth_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        user_info_url="https://www.googleapis.com/oauth2/v2/userinfo",
        scopes=["openid", "profile", "email"],
        user_mapping={
            "id": "id",
            "email": "email",
            "username": "name",
            "avatar": "picture"
        },
        icon_url="https://developers.google.com/identity/images/g-logo.png",
        button_color="#4285f4",
        sort_order=1,
        is_active=True
    )
    return provider


async def create_github_provider():
    """Create GitHub OAuth provider configuration"""
    provider = OAuthProvider(
        name="github",
        display_name="GitHub",
        description="Login with GitHub account",
        client_id="your-github-client-id",
        client_secret=token_encryption.encrypt("your-github-client-secret"),
        auth_url="https://github.com/login/oauth/authorize",
        token_url="https://github.com/login/oauth/access_token",
        user_info_url="https://api.github.com/user",
        scopes=["user:email"],
        user_mapping={
            "id": "id",
            "email": "email", 
            "username": "name",
            "avatar": "avatar_url"
        },
        icon_url="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png",
        button_color="#24292e",
        sort_order=2,
        is_active=True
    )
    return provider


async def create_wecom_provider():
    """Create WeCom (Enterprise WeChat) OAuth provider configuration"""
    # Note: WeCom requires special configuration in auth_url (agentid)
    # and uses a different flow (client_credentials for app token)
    provider = OAuthProvider(
        name="wecom",
        display_name="Enterprise WeChat",
        description="Login with WeCom",
        client_id="your-corp-id",  # CorpID
        client_secret=token_encryption.encrypt("your-app-secret"), # App Secret
        # Scan Login URL (Recommended)
        auth_url="https://login.work.weixin.qq.com/wwlogin/sso/login", 
        # Token URL
        token_url="https://qyapi.weixin.qq.com/cgi-bin/gettoken",
        # User Info URL
        user_info_url="https://qyapi.weixin.qq.com/cgi-bin/user/getuserinfo",
        scopes=[], # Not used for scan login
        user_mapping={
            "id": "UserId",
            "email": "email",
            "username": "name", 
            "avatar": "avatar"
        },
        icon_url="https://wwcdn.weixin.qq.com/node/wework/images/icon_3_1.c1539fc8.png",
        button_color="#2475b6",
        sort_order=4,
        is_active=False
    )
    return provider


async def setup_oauth_providers():
    """Setup OAuth providers"""
    async with async_session_maker() as session:
        # Check and create Google provider
        # ... (logic to create providers)
    print("=== Setup OAuth Providers ===")
    
    async with async_session_maker() as session:
        try:
            # Check if already exists
            from sqlalchemy import select
            
            # Google
            result = await session.execute(
                select(OAuthProvider).where(OAuthProvider.name == "google")
            )
            if not result.scalar_one_or_none():
                google_provider = await create_google_provider()
                session.add(google_provider)
                print("✅ Google OAuth provider added")
            else:
                print("⚠️ Google OAuth provider already exists")
            
            # GitHub
            result = await session.execute(
                select(OAuthProvider).where(OAuthProvider.name == "github")
            )
            if not result.scalar_one_or_none():
                github_provider = await create_github_provider()
                session.add(github_provider)
                print("✅ GitHub OAuth provider added")
            else:
                print("⚠️ GitHub OAuth provider already exists")
            
            # WeCom (Enterprise WeChat)
            result = await session.execute(
                select(OAuthProvider).where(OAuthProvider.name == "wecom")
            )
            if not result.scalar_one_or_none():
                wecom_provider = await create_wecom_provider()
                session.add(wecom_provider)
                print("✅ WeCom provider added")
            else:
                print("⚠️ WeCom provider already exists")
            
            await session.commit()
            print("\n🎉 OAuth providers configuration completed!")
            
            print("\n📝 Next steps:")
            print("1. Create applications at each OAuth provider and get client_id and client_secret")
            print("2. Login to admin panel with admin account and update provider real configuration")
            print("3. Enable required OAuth providers")
            print("4. Configure frontend page to display OAuth login buttons")
            
            print("\n🔧 API Endpoints:")
            print("- Get available providers: GET /api/v1/auth/oauth/providers")
            print("- Initiate authorization: POST /api/v1/auth/oauth/{provider_name}/authorize")
            print("- Manage providers: GET/POST/PUT/DELETE /api/v1/admin/oauth-providers")
            
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(setup_oauth_providers())