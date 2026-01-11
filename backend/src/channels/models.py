from sqlalchemy import String, Boolean, JSON, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from typing import Dict, Any, Optional
import enum
import uuid
from datetime import datetime
from fastapi_users_db_sqlalchemy.generics import GUID

from src.models import Base

class ChannelProvider(str, enum.Enum):
    TELEGRAM = "telegram"
    DISCORD = "discord"
    WECOM = "wecom"
    SLACK = "slack"

class AssistantChannel(Base):
    __tablename__ = "assistant_channels"

    # id, created_at, updated_at are inherited from Base

    assistant_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("assistants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Platform type (telegram, discord, etc.)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    
    # User-friendly name (e.g., "Customer Support Bot")
    name: Mapped[str] = mapped_column(String, nullable=False)
    
    # Encrypted credentials
    credentials: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default={})
    
    # General behaviour settings
    settings: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default={})
    
    # Metadata from Provider
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default={})
    
    # Is this channel active?
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    # assistant = relationship("Assistant", back_populates="channels") 


class ChannelIdentity(Base):
    """
    Mapping between external channel users (e.g. WeCom UserID) and internal System Users.
    """
    __tablename__ = "channel_identities"

    # Link to internal user
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Optional: Link to specific channel (if identity is scoped to bot instance)
    channel_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("assistant_channels.id", ondelete="SET NULL"), nullable=True)
    
    # External Identity Info
    provider: Mapped[str] = mapped_column(String, nullable=False) # e.g. "wecom"
    identity_id: Mapped[str] = mapped_column(String, nullable=False, index=True) # e.g. "Wu234..."
    
    # Extra data (nickname, avatar, etc.)
    extra_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default={})
    
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('provider', 'identity_id', name='uq_provider_identity'),
    )
