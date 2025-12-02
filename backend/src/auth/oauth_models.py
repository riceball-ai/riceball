"""
OAuth Related Data Models
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, Text, JSON, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from fastapi_users_db_sqlalchemy.generics import GUID

from src.models import Base


class OAuthProvider(Base):
    """OAuth Provider Configuration"""
    __tablename__ = "oauth_providers"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)  # google, github, custom_sso
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # OAuth Configuration
    client_id: Mapped[str] = mapped_column(String(500), nullable=False)
    client_secret: Mapped[str] = mapped_column(String(1000), nullable=False)  # Encrypted storage
    auth_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    token_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    user_info_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    
    # Configuration Options
    scopes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)  # ["openid", "profile", "email"]
    user_mapping: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)  # Field mapping configuration
    
    # Status and Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    icon_url: Mapped[Optional[str]] = mapped_column(String(500))  # Icon URL
    button_color: Mapped[Optional[str]] = mapped_column(String(20))  # Button color
    sort_order: Mapped[int] = mapped_column(default=0)  # Sort order
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user_links = relationship("OAuthUserLink", back_populates="provider", cascade="all, delete-orphan")


class OAuthUserLink(Base):
    """OAuth User Link"""
    __tablename__ = "oauth_user_links"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    
    # Link user and provider
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("oauth_providers.id", ondelete="CASCADE"), nullable=False)
    
    # Third-party user info
    provider_user_id: Mapped[str] = mapped_column(String(500), nullable=False)  # Third-party user ID
    provider_username: Mapped[Optional[str]] = mapped_column(String(200))
    provider_email: Mapped[Optional[str]] = mapped_column(String(320))
    provider_avatar: Mapped[Optional[str]] = mapped_column(String(1000))
    
    # Token Info
    access_token: Mapped[Optional[str]] = mapped_column(Text)  # Encrypted storage
    refresh_token: Mapped[Optional[str]] = mapped_column(Text)  # Encrypted storage
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Metadata
    raw_user_info: Mapped[Optional[dict]] = mapped_column(JSON)  # Store raw user info
    
    # Timestamps
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", backref="oauth_links")
    provider = relationship("OAuthProvider", back_populates="user_links")
    
    # Constraints: Same user cannot link same provider multiple times
    __table_args__ = (
        UniqueConstraint('user_id', 'provider_id', name='unique_user_provider'),
        UniqueConstraint('provider_id', 'provider_user_id', name='unique_provider_user'),
    )


class OAuthState(Base):
    """OAuth State Management (for CSRF protection)"""
    __tablename__ = "oauth_states"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    state: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    redirect_uri: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Optional extra data
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON)