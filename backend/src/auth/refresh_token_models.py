"""
Refresh Token Data Model
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from fastapi_users_db_sqlalchemy.generics import GUID

from src.models import Base


class RefreshToken(Base):
    """Refresh Token Table"""
    
    __tablename__ = "refresh_tokens"
    
    # Token value (hashed)
    token: Mapped[str] = mapped_column(
        String(500),
        unique=True,
        nullable=False,
        index=True
    )
    
    # Associated User ID
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Token expiration time
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    
    # Is revoked
    revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    
    # Device info (User-Agent)
    device_info: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    
    # Associated User object
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")  # type: ignore
    
    # Index optimization
    __table_args__ = (
        Index('idx_refresh_token_user_expires', 'user_id', 'expires_at'),
        Index('idx_refresh_token_active', 'user_id', 'revoked', 'expires_at'),
    )
    
    def __repr__(self) -> str:
        return f"<RefreshToken(user_id={self.user_id}, expires_at={self.expires_at}, revoked={self.revoked})>"
