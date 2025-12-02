"""
File upload endpoints.
"""
import json
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from src.auth.fastapi_users import current_user
from src.users.models import User
from ...models import FileType
from ...service import FileService, get_file_service

router = APIRouter()


class FileResponse(BaseModel):
    """Response model for file information."""
    id: UUID
    filename: str
    content_type: str
    file_size: int
    file_type: FileType
    file_path: Optional[str] = None
    created_at: str
    metadata: dict
    url: Optional[str] = None  # Download URL for the file
    
    class Config:
        from_attributes = True


class FileListResponse(BaseModel):
    """Response model for file list."""
    files: List[FileResponse]
    total: int


class FileUrlResponse(BaseModel):
    """Response model for file URL."""
    file_key: str
    url: Optional[str] = None
    message: Optional[str] = None


@router.post("/files/upload", response_model=FileResponse)
async def upload_file(
    file: UploadFile = File(...),
    file_type: FileType = Form(...),
    metadata: Optional[str] = Form(None),
    current_user: User = Depends(current_user),
    file_service: FileService = Depends(get_file_service()),
):
    """
    Upload a file to the system.
    
    - **file**: The file to upload
    - **file_type**: Type of file (avatar, document)
    - **metadata**: Optional JSON string with additional file metadata
    - **Returns**: File information including ID and storage details
    """
    
    # Parse metadata if provided
    parsed_metadata = {}
    if metadata:
        try:
            parsed_metadata = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid metadata JSON")
    
    # Upload file
    file_record = await file_service.upload_file(
        file=file,
        file_type=file_type,
        user_id=current_user.id,
        metadata=parsed_metadata
    )
    
    # Generate download URL for the uploaded file
    download_url = await file_service.get_public_url(
        file_path=file_record.file_path
    )
    
    return FileResponse(
        id=file_record.id,
        filename=file_record.filename,
        content_type=file_record.content_type,
        file_size=file_record.file_size,
        file_type=file_record.file_type,
        file_path=file_record.file_path,
        created_at=file_record.created_at.isoformat(),
        metadata=file_record.file_metadata,
        url=download_url
    )


@router.get("/files/url/{file_key:path}", response_model=FileUrlResponse)
async def get_file_url(
    file_key: str,
    current_user: User = Depends(current_user),
    file_service: FileService = Depends(get_file_service()),
):
    """
    Get public URL for a file by its file key (file path).
    
    - **file_key**: The file key/path (e.g., "avatars/user123/avatar.jpg")
    - **Returns**: Public URL for accessing the file
    """
    
    # Get public URL for the file
    public_url = await file_service.get_public_url(file_key)
    
    if public_url:
        return FileUrlResponse(
            file_key=file_key,
            url=public_url,
            message="URL generated successfully"
        )
    else:
        return FileUrlResponse(
            file_key=file_key,
            url=None,
            message="Failed to generate URL for the file"
        )


@router.get("/files/public-url/{file_key:path}", response_model=FileUrlResponse)
async def get_public_file_url(
    file_key: str,
    file_service: FileService = Depends(get_file_service()),
):
    """
    Get public URL for a file by its file key (file path) - No authentication required.
    
    - **file_key**: The file key/path (e.g., "avatars/user123/avatar.jpg")
    - **Returns**: Public URL for accessing the file
    
    Note: This endpoint is public and doesn't require authentication.
    Use with caution for sensitive files.
    """
    
    # Get public URL for the file
    public_url = await file_service.get_public_url(file_key)
    
    if public_url:
        return FileUrlResponse(
            file_key=file_key,
            url=public_url,
            message="URL generated successfully"
        )
    else:
        return FileUrlResponse(
            file_key=file_key,
            url=None,
            message="Failed to generate URL for the file"
        )