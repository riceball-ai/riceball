import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from fastapi_users_db_sqlalchemy.generics import GUID

from src.models import Base

class ScheduledTask(Base):
    """
    Scheduled Task Definition
    """
    __tablename__ = "scheduled_tasks"

    # Inherits id, created_at, updated_at from Base

    owner_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Trigger Config
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. "0 8 * * *"
    
    # Task Payload
    assistant_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("assistants.id", ondelete="RESTRICT"), nullable=False)
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Target / Output
    # Refactored: Generic Channel + Target ID
    channel_config_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("channel_configs.id", ondelete="CASCADE"), nullable=False)
    target_identifier: Mapped[str] = mapped_column(String(255), nullable=False) # e.g. WeCom ChatID, UserID, TG ChatID
    
    # State
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class ScheduledTaskExecution(Base):
    """
    Log of scheduled task executions
    """
    __tablename__ = "scheduled_task_executions"

    task_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("scheduled_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    
    status: Mapped[str] = mapped_column(String(50), default="PENDING") # PENDING, RUNNING, COMPLETED, FAILED
    
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    duration: Mapped[Optional[float]] = mapped_column(String(50), nullable=True) # Stored as float seconds or string "1.2s"
    
    # We store the final text result here. 
    # If the response is huge, consider truncation or separate storage.
    result_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

