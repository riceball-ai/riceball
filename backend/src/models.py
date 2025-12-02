import uuid
from datetime import datetime

from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column
)
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy import DateTime, func, MetaData
from fastapi_users_db_sqlalchemy.generics import GUID


# Define naming convention
metadata = MetaData(naming_convention={
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s", 
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
})


class Base(AsyncAttrs, DeclarativeBase):
    """Base model class containing common fields for all tables"""
    
    metadata = metadata
    
    # Primary key using UUID
    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    # Created timestamp, automatically set when inserting records
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False
    )
    
    # Updated timestamp, automatically set when inserting and updating records
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False
    )