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


class ChannelConfig(Base):
    """
    Configuration for external communication channels (Telegram Bot, WeCom App, etc).
    Now decoupled from specific assistants (though can be linked via assistant_id for legacy/simple binding).
    """
    __tablename__ = "channel_configs"

    # id, created_at, updated_at are inherited from Base
    
    # Owner of this configuration (System Admin or specific User)
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    # Optional: Primary Assistant linked to this channel (for defining the "Inbox" behavior)
    # If null, this channel might only be used for outbound notifications or routed dynamically.
    assistant_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("assistants.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Platform type (telegram, discord, etc.)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    
    # User-friendly name (e.g., "Customer Support Bot")
    name: Mapped[str] = mapped_column(String, nullable=False)
    
    # Encrypted credentials (token, secret, etc.)
    credentials: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default={})
    
    # General behaviour settings & metadata
    settings: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default={})
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default={})
    
    # Is this channel active?
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class UserChannelBinding(Base):
    """
    Mapping between external channel users (e.g. WeCom UserID) and internal System Users.
    Essential for PUSH notifications (finding the target).
    Originally named ChannelIdentity.
    """
    __tablename__ = "user_channel_bindings"

    # Link to internal user
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Link to specific channel config context
    channel_config_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("channel_configs.id", ondelete="SET NULL"), nullable=True)
    
    # External Identity Info
    provider: Mapped[str] = mapped_column(String, nullable=False) # e.g. "wecom"
    external_user_id: Mapped[str] = mapped_column(String, nullable=False, index=True) # e.g. "Wu234..." (OpenID/ChatID)
    
    # Extra data (nickname, avatar, raw profile data etc.)
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default={})
    
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('provider', 'external_user_id', name='uq_provider_external_user'),
        # Note: We might want a unique constraint on (channel_config_id, external_user_id) too, 
        # but 'provider' + 'external_user_id' is usually globally unique enough for most platforms (except maybe Slack team IDs).
    )

