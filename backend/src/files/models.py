"""
File management models for storing file metadata and tracking uploads.
"""
import enum
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey, Integer, Enum as SQLEnum, JSON

from ..models import Base


class FileType(enum.Enum):
    """File type enumeration for categorizing uploaded files."""
    AVATAR = "avatar"
    DOCUMENT = "document"
    IMAGE = "image"  # For chat image attachments

class FileStatus(enum.Enum):
    """File processing status enumeration."""
    UPLOADING = "uploading"
    ACTIVE = "active"
    PROCESSING = "processing"
    ERROR = "error"
    DELETED = "deleted"


class FileRecord(Base):
    """
    Model for storing file metadata and tracking uploads.
    
    This model stores essential information about uploaded files including
    their storage location, metadata, and relationships to users.
    """
    __tablename__ = "file_records"
    
    # Original filename as uploaded by user
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # MIME type of the file
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # File size in bytes
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # File type category (stored as string for flexibility)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Storage key/path
    file_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    
    # File processing status
    status: Mapped[str] = mapped_column(String(50), default="uploading", nullable=False)
    
    # User who uploaded the file
    uploaded_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Additional metadata as JSON
    file_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # File hash for deduplication and integrity checking
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    
    # Expiration date for temporary files (optional)
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # Note: Relationship to user is handled via foreign key
    # uploader relationship defined elsewhere to avoid circular imports
    
    def __repr__(self):
        return f"<FileRecord(filename='{self.filename}', type='{self.file_type}')>"
    
    @property
    def is_image(self) -> bool:
        """Check if the file is an image based on content type."""
        return self.content_type.startswith('image/')
    
    @property
    def is_expired(self) -> bool:
        """Check if the file has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def size_mb(self) -> float:
        """Get file size in megabytes."""
        return self.file_size / (1024 * 1024)