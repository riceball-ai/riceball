"""
OAuth API Schemas
"""
import uuid
from typing import Optional, List, Dict
from datetime import datetime

from pydantic import BaseModel, Field


class OAuthProviderBase(BaseModel):
    """OAuth Provider Base Model"""
    name: str = Field(..., max_length=100, description="Provider name (e.g., 'google', 'github')")
    display_name: str = Field(..., max_length=200, description="Display name")
    description: Optional[str] = Field(None, description="Provider description")
    
    # OAuth Configuration
    client_id: str = Field(..., max_length=500, description="OAuth client ID")
    auth_url: str = Field(..., max_length=1000, description="Authorization URL")
    token_url: str = Field(..., max_length=1000, description="Token URL")
    user_info_url: str = Field(..., max_length=1000, description="User info URL")
    
    # Configuration Options
    scopes: List[str] = Field(default=[], description="OAuth scopes")
    user_mapping: Dict[str, str] = Field(default={}, description="User field mapping")
    
    # UI Configuration
    icon_url: Optional[str] = Field(None, max_length=500, description="Icon URL")
    button_color: Optional[str] = Field(None, max_length=20, description="Button color")
    sort_order: int = Field(default=0, description="Sort order")
    is_active: bool = Field(default=True, description="Is provider active")


class OAuthProviderCreate(OAuthProviderBase):
    """Create OAuth Provider"""
    client_secret: str = Field(..., max_length=1000, description="OAuth client secret")


class OAuthProviderUpdate(BaseModel):
    """Update OAuth Provider"""
    display_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None)
    client_id: Optional[str] = Field(None, max_length=500)
    client_secret: Optional[str] = Field(None, max_length=1000)
    auth_url: Optional[str] = Field(None, max_length=1000)
    token_url: Optional[str] = Field(None, max_length=1000)
    user_info_url: Optional[str] = Field(None, max_length=1000)
    scopes: Optional[List[str]] = Field(None)
    user_mapping: Optional[Dict[str, str]] = Field(None)
    icon_url: Optional[str] = Field(None, max_length=500)
    button_color: Optional[str] = Field(None, max_length=20)
    sort_order: Optional[int] = Field(None)
    is_active: Optional[bool] = Field(None)


class OAuthProviderResponse(BaseModel):
    """OAuth Provider Response"""
    id: uuid.UUID
    name: str
    display_name: str
    description: Optional[str] = None
    client_id: str
    auth_url: str
    token_url: str
    user_info_url: str
    scopes: List[str]
    user_mapping: Dict[str, str]
    icon_url: Optional[str] = None
    button_color: Optional[str] = None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OAuthProviderPublic(BaseModel):
    """Public OAuth Provider Info (excluding sensitive info)"""
    id: uuid.UUID
    name: str
    display_name: str
    description: Optional[str] = None
    scopes: List[str]
    icon_url: Optional[str] = None
    button_color: Optional[str] = None
    sort_order: int

    class Config:
        from_attributes = True


class OAuthUserLinkResponse(BaseModel):
    """OAuth User Link Response"""
    id: uuid.UUID
    provider_id: uuid.UUID
    provider_user_id: str
    provider_username: Optional[str] = None
    provider_email: Optional[str] = None
    provider_avatar: Optional[str] = None
    linked_at: datetime
    last_login_at: Optional[datetime] = None
    
    # Provider Info
    provider: OAuthProviderPublic

    class Config:
        from_attributes = True


class OAuthAuthorizationRequest(BaseModel):
    """OAuth Authorization Request"""
    redirect_uri: str = Field(..., description="Frontend redirect URI")


class OAuthAuthorizationResponse(BaseModel):
    """OAuth Authorization Response"""
    authorization_url: str = Field(..., description="OAuth authorization URL")
    state: str = Field(..., description="CSRF protection state")


class OAuthCallbackResponse(BaseModel):
    """OAuth Callback Response"""
    success: bool
    message: str
    user_id: Optional[uuid.UUID] = None

class OAuthProvidersListResponse(BaseModel):
    """OAuth Providers List Response"""
    List[OAuthProviderPublic]


class OAuthUserLinksResponse(BaseModel):
    """User OAuth Links List Response"""
    links: List[OAuthUserLinkResponse]


class OAuthUnlinkRequest(BaseModel):
    """Unlink OAuth Request"""
    provider_id: uuid.UUID = Field(..., description="Provider ID to unlink")


class OAuthUnlinkResponse(BaseModel):
    """Unlink OAuth Response"""
    success: bool
    message: str