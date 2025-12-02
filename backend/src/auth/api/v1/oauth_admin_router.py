"""
OAuth Admin API Router
"""
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate as sqlalchemy_paginate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import get_async_session
from src.auth import current_superuser
from src.users.models import User
from ...oauth_models import OAuthProvider
from ...oauth_service import get_oauth_service
from ...oauth_utils import token_encryption
from ...oauth_schemas import (
    OAuthProviderCreate,
    OAuthProviderUpdate, 
    OAuthProviderResponse
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/oauth-providers", response_model=Page[OAuthProviderResponse])
async def list_oauth_providers(
    search: Optional[str] = Query(None, description="Search in name or display_name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session)
) -> Page[OAuthProviderResponse]:
    """List all OAuth providers (Admin) - Supports pagination and search"""
    query = select(OAuthProvider).order_by(OAuthProvider.sort_order, OAuthProvider.display_name)
    
    # Apply search filter
    if search:
        search_term = f"%{search}%"
        query = query.where(
            (OAuthProvider.name.ilike(search_term)) |
            (OAuthProvider.display_name.ilike(search_term))
        )
    
    # Apply status filter
    if is_active is not None:
        query = query.where(OAuthProvider.is_active == is_active)
    
    return await sqlalchemy_paginate(session, query)


@router.post("/oauth-providers", response_model=OAuthProviderResponse)
async def create_oauth_provider(
    provider_data: OAuthProviderCreate,
    current_user: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session)
) -> OAuthProviderResponse:
    """Create OAuth provider (Admin)"""
    
    # Check if name already exists
    result = await session.execute(
        select(OAuthProvider).where(OAuthProvider.name == provider_data.name)
    )
    
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400, 
            detail=f"OAuth provider with name '{provider_data.name}' already exists"
        )
    
    # Encrypt client secret
    encrypted_secret = token_encryption.encrypt(provider_data.client_secret)
    
    # Create provider
    provider = OAuthProvider(
        name=provider_data.name,
        display_name=provider_data.display_name,
        description=provider_data.description,
        client_id=provider_data.client_id,
        client_secret=encrypted_secret,
        auth_url=provider_data.auth_url,
        token_url=provider_data.token_url,
        user_info_url=provider_data.user_info_url,
        scopes=provider_data.scopes,
        user_mapping=provider_data.user_mapping,
        icon_url=provider_data.icon_url,
        button_color=provider_data.button_color,
        sort_order=provider_data.sort_order,
        is_active=provider_data.is_active
    )
    
    session.add(provider)
    await session.commit()
    await session.refresh(provider)
    
    logger.info(f"Created OAuth provider: {provider.name}")
    return OAuthProviderResponse.model_validate(provider)


@router.get("/oauth-providers/{provider_id}", response_model=OAuthProviderResponse)
async def get_oauth_provider(
    provider_id: uuid.UUID,
    current_user: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session)
) -> OAuthProviderResponse:
    """Get specific OAuth provider (Admin)"""
    result = await session.execute(
        select(OAuthProvider).where(OAuthProvider.id == provider_id)
    )
    
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="OAuth provider not found")
    
    return provider


@router.put("/oauth-providers/{provider_id}", response_model=OAuthProviderResponse)
async def update_oauth_provider(
    provider_id: uuid.UUID,
    provider_data: OAuthProviderUpdate,
    current_user: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session)
) -> OAuthProviderResponse:
    """Update OAuth provider (Admin)"""
    result = await session.execute(
        select(OAuthProvider).where(OAuthProvider.id == provider_id)
    )
    
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="OAuth provider not found")
    
    # Update fields
    update_data = provider_data.model_dump(exclude_unset=True)
    
    # If client_secret is empty (None or empty string), remove from update data, keep original value
    if 'client_secret' in update_data:
        client_secret = update_data['client_secret']
        if client_secret is None or client_secret == '':
            # Remove empty client_secret, do not update this field
            update_data.pop('client_secret')
        else:
            # Only encrypt and update when client_secret is not empty
            update_data['client_secret'] = token_encryption.encrypt(client_secret)
    
    for field, value in update_data.items():
        setattr(provider, field, value)
    
    await session.commit()
    await session.refresh(provider)
    
    logger.info(f"Updated OAuth provider: {provider.name}")
    return OAuthProviderResponse.model_validate(provider)


@router.delete("/oauth-providers/{provider_id}")
async def delete_oauth_provider(
    provider_id: uuid.UUID,
    current_user: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session)
) -> dict:
    """Delete OAuth provider (Admin)"""
    result = await session.execute(
        select(OAuthProvider).where(OAuthProvider.id == provider_id)
    )
    
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="OAuth provider not found")
    
    # Delete provider (cascade delete user links)
    await session.delete(provider)
    await session.commit()
    
    logger.info(f"Deleted OAuth provider: {provider.name}")
    return {"message": "OAuth provider deleted successfully"}


@router.post("/oauth-providers/{provider_id}/test")
async def test_oauth_provider(
    provider_id: uuid.UUID,
    current_user: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session)
) -> dict:
    """Test OAuth provider configuration (Admin)"""
    result = await session.execute(
        select(OAuthProvider).where(OAuthProvider.id == provider_id)
    )
    
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="OAuth provider not found")
    
    oauth_service = get_oauth_service(session)
    
    try:
        # Test creating authorization URL
        test_redirect_uri = "http://localhost:8000/test"
        auth_url, state = await oauth_service.create_authorization_url(
            provider=provider,
            redirect_uri=test_redirect_uri
        )
        
        return {
            "success": True,
            "message": "OAuth provider configuration is valid",
            "test_authorization_url": auth_url
        }
        
    except Exception as e:
        logger.error(f"OAuth provider test failed for {provider.name}: {e}")
        return {
            "success": False,
            "message": f"OAuth provider test failed: {str(e)}"
        }


@router.get("/oauth-providers/{provider_id}/stats")
async def get_oauth_provider_stats(
    provider_id: uuid.UUID,
    current_user: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session)
) -> dict:
    """Get OAuth provider statistics (Admin)"""
    from ...oauth_models import OAuthUserLink
    
    result = await session.execute(
        select(OAuthProvider).where(OAuthProvider.id == provider_id)
    )
    
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="OAuth provider not found")
    
    # Count linked users
    from sqlalchemy import func
    result = await session.execute(
        select(func.count(OAuthUserLink.id)).where(OAuthUserLink.provider_id == provider_id)
    )
    linked_users_count = result.scalar()
    
    # Recent login statistics (last 30 days)
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    result = await session.execute(
        select(func.count(OAuthUserLink.id)).where(
            OAuthUserLink.provider_id == provider_id,
            OAuthUserLink.last_login_at >= thirty_days_ago
        )
    )
    recent_logins = result.scalar()
    
    return {
        "provider_name": provider.name,
        "linked_users_count": linked_users_count,
        "recent_logins_30_days": recent_logins,
        "is_active": provider.is_active
    }