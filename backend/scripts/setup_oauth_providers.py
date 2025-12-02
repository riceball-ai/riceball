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


async def create_custom_sso_provider():
    """Create custom enterprise SSO provider configuration example"""
    provider = OAuthProvider(
        name="company_sso",
        display_name="Company SSO",
        description="Login with Company SSO",
        client_id="company-sso-client-id",
        client_secret=token_encryption.encrypt("company-sso-client-secret"),
        auth_url="https://sso.company.com/oauth/authorize",
        token_url="https://sso.company.com/oauth/token",
        user_info_url="https://sso.company.com/api/userinfo",
        scopes=["openid", "profile", "email", "groups"],
        user_mapping={
            "id": "sub",  # Standard OpenID Connect User ID
            "email": "email",
            "username": "preferred_username",
            "avatar": "picture"
        },
        icon_url="https://company.com/logo.png",
        button_color="#007acc",
        sort_order=3,
        is_active=False  # Default disabled, requires admin configuration to enable
    )
    return provider


async def setup_oauth_providers():
    """Setup OAuth providers"""
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
            
            # Custom SSO
            result = await session.execute(
                select(OAuthProvider).where(OAuthProvider.name == "company_sso")
            )
            if not result.scalar_one_or_none():
                custom_provider = await create_custom_sso_provider()
                session.add(custom_provider)
                print("✅ Custom SSO provider added")
            else:
                print("⚠️ Custom SSO provider already exists")
            
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