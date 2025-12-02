"""
File management service for handling file operations and business logic.
"""
import base64
import logging
import urllib.parse
from pathlib import Path
from typing import List, Optional, BinaryIO
from uuid import UUID

from fastapi import HTTPException, UploadFile, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .models import FileRecord, FileType, FileStatus
from .storage import storage_service
from ..database import get_async_session

logger = logging.getLogger(__name__)

# File size limits (in bytes)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB
MAX_DOCUMENT_SIZE = 100 * 1024 * 1024  # 100MB

# Allowed file types
ALLOWED_IMAGE_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"
}

ALLOWED_DOCUMENT_TYPES = {
    "application/pdf", "text/plain", "text/markdown",
    "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint", "application/vnd.openxmlformats-officedocument.presentationml.presentation"
}

ALLOWED_TYPES_BY_FILE_TYPE = {
    FileType.AVATAR: ALLOWED_IMAGE_TYPES,
    FileType.DOCUMENT: ALLOWED_DOCUMENT_TYPES | ALLOWED_IMAGE_TYPES,
    FileType.IMAGE: ALLOWED_IMAGE_TYPES,  # Chat image attachments
}

SIZE_LIMITS_BY_FILE_TYPE = {
    FileType.AVATAR: MAX_AVATAR_SIZE,
    FileType.DOCUMENT: MAX_DOCUMENT_SIZE,
    FileType.IMAGE: MAX_AVATAR_SIZE,  # Same as avatar (5MB)
}


class FileService:
    """
    Service class for file management operations.
    
    Handles file validation, upload, download, and database operations.
    Integrates with S3 storage and maintains file metadata in database.
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    def _encode_filename_for_s3(self, filename: str) -> str:
        """
        Encode filename for S3 metadata to ensure ASCII compatibility.
        
        Args:
            filename: Original filename that may contain non-ASCII characters
            
        Returns:
            ASCII-safe encoded filename
        """
        try:
            # First try URL encoding
            encoded = urllib.parse.quote(filename, safe='.-_')
            # If still contains non-ASCII after URL encoding, use base64
            if not encoded.isascii():
                encoded = base64.b64encode(filename.encode('utf-8')).decode('ascii')
                encoded = f"b64_{encoded}"
            return encoded
        except Exception:
            # Fallback: use base64 encoding
            return f"b64_{base64.b64encode(filename.encode('utf-8')).decode('ascii')}"

    def _decode_filename_from_s3(self, encoded_filename: str) -> str:
        """
        Decode filename from S3 metadata.
        
        Args:
            encoded_filename: Encoded filename from S3 metadata
            
        Returns:
            Original filename
        """
        try:
            if encoded_filename.startswith('b64_'):
                # Base64 encoded
                encoded_data = encoded_filename[4:]  # Remove 'b64_' prefix
                return base64.b64decode(encoded_data).decode('utf-8')
            else:
                # URL encoded
                return urllib.parse.unquote(encoded_filename)
        except Exception:
            # If decoding fails, return as is
            return encoded_filename

    async def validate_file(
        self,
        file: UploadFile,
        file_type: FileType,
        max_size: Optional[int] = None
    ) -> None:
        """
        Validate uploaded file against type and size constraints.
        
        Args:
            file: Uploaded file to validate
            file_type: Expected file type category
            max_size: Maximum file size in bytes (optional override)
            
        Raises:
            HTTPException: If validation fails
        """
        # Check file size
        if file.size is None:
            raise HTTPException(status_code=400, detail="Cannot determine file size")
        
        size_limit = max_size or SIZE_LIMITS_BY_FILE_TYPE.get(file_type, MAX_FILE_SIZE)
        if file.size > size_limit:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {size_limit / (1024 * 1024):.1f}MB"
            )
        
        # Check content type
        allowed_types = ALLOWED_TYPES_BY_FILE_TYPE.get(file_type, set())
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported file type: {file.content_type}. "
                       f"Allowed types: {', '.join(allowed_types)}"
            )
        
        # Validate filename
        if not file.filename or len(file.filename.strip()) == 0:
            raise HTTPException(status_code=400, detail="Filename is required")
        
        # Check for dangerous file extensions
        file_extension = Path(file.filename).suffix.lower()
        dangerous_extensions = {".exe", ".bat", ".cmd", ".com", ".scr", ".js", ".vbs"}
        if file_extension in dangerous_extensions:
            raise HTTPException(
                status_code=415,
                detail=f"File extension {file_extension} is not allowed for security reasons"
            )

    async def upload_file(
        self,
        file: UploadFile,
        file_type: FileType,
        user_id: UUID,
        metadata: Optional[dict] = None
    ) -> FileRecord:
        """
        Upload file to storage and create database record.
        
        Args:
            file: File to upload
            file_type: Type of file being uploaded
            user_id: ID of user uploading the file
            metadata: Additional metadata to store
            
        Returns:
            Created FileRecord instance
            
        Raises:
            HTTPException: If upload fails or validation fails
        """
        # Validate file
        await self.validate_file(file, file_type)
        
        # Create file record
        file_record = FileRecord(
            filename=file.filename,
            content_type=file.content_type,
            file_size=file.size,
            file_type=file_type.value,  # Convert enum to string
            uploaded_by=user_id,
            file_metadata=metadata or {},
            status="uploading"  # Use string instead of enum
        )
        
        self.db.add(file_record)
        await self.db.flush()  # Get the file ID
        
        try:
            # Upload to S3
            file_content = await file.read()
            
            # Encode filename for S3 metadata to ensure ASCII compatibility
            encoded_filename = self._encode_filename_for_s3(file.filename)
            
            file_path = await storage_service.upload_public_file(
                file_data=file_content,
                file_type=file_type.value,
                file_id=file_record.id,
                filename=encoded_filename,  # Use encoded filename for S3 metadata
                content_type=file.content_type,
                file_size=file.size
            )
            
            # Update file record with S3 key and public URL
            file_record.file_path = file_path
            file_record.status = "active"  # Use string instead of enum
            
            await self.db.commit()
            logger.info(f"File uploaded successfully: {file_record.id}")
            
            return file_record
            
        except Exception as e:
            # Rollback database changes if upload fails
            await self.db.rollback()
            logger.error(f"File upload failed: {e}")
            raise HTTPException(status_code=500, detail="File upload failed")

    async def get_public_url(self, file_path: str) -> Optional[str]:
        """
        Get public URL for a file stored in S3.
        
        Args:
            file_path: Storage key/path of the file
            
        Returns:
            Public URL string or None if generation fails
        """
        try:
            return await storage_service.get_public_url(file_path)
        except Exception as e:
            logger.error(f"Failed to get public URL for {file_path}: {e}")
            return None

    async def get_file_by_id(self, file_id: UUID) -> Optional[FileRecord]:
        """
        Get file record by ID.
        
        Args:
            file_id: File identifier
            
        Returns:
            FileRecord if found, None otherwise
        """
        stmt = select(FileRecord).where(FileRecord.id == file_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_file_by_path(self, file_path: str) -> Optional[FileRecord]:
        """
        Get file record by file path.
        
        Args:
            file_path: File path/storage key
            
        Returns:
            FileRecord if found, None otherwise
        """
        stmt = select(FileRecord).where(
            FileRecord.file_path == file_path,
            FileRecord.status == FileStatus.ACTIVE
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_files(
        self,
        user_id: UUID,
        file_type: Optional[FileType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[FileRecord]:
        """
        Get files uploaded by a specific user.
        
        Args:
            user_id: User identifier
            file_type: Optional file type filter
            limit: Maximum number of files to return
            offset: Pagination offset
            
        Returns:
            List of FileRecord instances
        """
        stmt = select(FileRecord).where(
            FileRecord.uploaded_by == user_id,
            FileRecord.status == FileStatus.ACTIVE
        )
        
        if file_type:
            stmt = stmt.where(FileRecord.file_type == file_type)
        
        stmt = stmt.order_by(FileRecord.created_at.desc()).limit(limit).offset(offset)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def download_file(self, file_id: UUID) -> tuple[BinaryIO, str, str]:
        """
        Download file content from storage.
        
        Args:
            file_id: File identifier
            
        Returns:
            Tuple of (file_content, content_type, filename)
            
        Raises:
            HTTPException: If file not found or download fails
        """
        file_record = await self.get_file_by_id(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")
        
        if file_record.status != FileStatus.ACTIVE:
            raise HTTPException(status_code=410, detail="File is no longer available")
        
        try:
            file_data, content_type = await storage_service.download_file(file_record.s3_key)
            return file_data, content_type, file_record.filename
            
        except Exception as e:
            logger.error(f"File download failed for {file_id}: {e}")
            raise HTTPException(status_code=500, detail="File download failed")

    async def delete_file(self, file_id: UUID, user_id: UUID) -> bool:
        """
        Delete file from storage and mark as deleted in database.
        
        Args:
            file_id: File identifier
            user_id: ID of user requesting deletion
            
        Returns:
            True if deletion successful, False otherwise
            
        Raises:
            HTTPException: If file not found or user not authorized
        """
        file_record = await self.get_file_by_id(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check user authorization (users can only delete their own files)
        if file_record.uploaded_by != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this file")
        
        try:
            # Delete from S3
            if file_record.s3_key:
                await storage_service.delete_file(file_record.s3_key)
            
            # Mark as deleted in database
            file_record.status = FileStatus.DELETED
            await self.db.commit()
            
            logger.info(f"File deleted successfully: {file_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"File deletion failed for {file_id}: {e}")
            return False

    async def generate_download_url(
        self,
        file_id: UUID,
        expiration: int = 3600
    ) -> Optional[str]:
        """
        Generate presigned URL for file download.
        
        Args:
            file_id: File identifier
            expiration: URL expiration time in seconds
            
        Returns:
            Presigned URL string or None if generation fails
        """
        file_record = await self.get_file_by_id(file_id)
        if not file_record or file_record.status != FileStatus.ACTIVE:
            return None
        
        return await storage_service.generate_presigned_url(
            file_record.s3_key,
            expiration=expiration
        )

    async def update_file_metadata(
        self,
        file_id: UUID,
        user_id: UUID,
        metadata: dict
    ) -> Optional[FileRecord]:
        """
        Update file metadata.
        
        Args:
            file_id: File identifier
            user_id: ID of user updating metadata
            metadata: New metadata to set
            
        Returns:
            Updated FileRecord or None if not found/authorized
        """
        file_record = await self.get_file_by_id(file_id)
        if not file_record:
            return None
        
        # Check user authorization
        if file_record.uploaded_by != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to update this file")
        
        file_record.file_metadata = metadata
        await self.db.commit()
        
        return file_record


def get_file_service():
    """Dependency factory to get FileService instance."""
    async def _get_service(session: AsyncSession = Depends(get_async_session)) -> FileService:
        return FileService(session)
    return _get_service