from typing import Optional
from datetime import datetime
import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, Boolean, ForeignKey
from fastapi_users_db_sqlalchemy.generics import GUID

from src.models import Base

class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Store only hash of the key for security
    hashed_key: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    # Store prefix to display to user (e.g. sk-xxxx)
    prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationship to User
    user = relationship("User", backref="api_keys", lazy="selectin")
