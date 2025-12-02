from typing import Optional, TYPE_CHECKING
from datetime import datetime
import uuid
from fastapi_users_db_sqlalchemy import (
    SQLAlchemyBaseUserTableUUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime

from src.models import Base

if TYPE_CHECKING:
    from src.auth.refresh_token_models import RefreshToken


class User(Base, SQLAlchemyBaseUserTableUUID):
    __tablename__ = "users"
    
    # Override base class email field, set to nullable
    email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True, unique=True)
    
    name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # User language preference (en, zh, etc.)
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, default='en')
    
    # Email sending rate limit timestamp
    last_verification_email_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_password_reset_email_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Refresh Token relationship
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan"
    )