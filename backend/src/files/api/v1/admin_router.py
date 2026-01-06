"""
FastAPI router for file upload and management endpoints.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
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
    file_path: str
    uploaded_by: UUID
    url: Optional[str] = None
    
    class Config:
        from_attributes = True


class FileListResponse(BaseModel):
    """Response model for file list."""
    items: List[FileResponse]
    total: int


@router.post("/files/upload", response_model=FileResponse)
async def upload_file(
    file: UploadFile = File(...),
    file_type: FileType = Form(...),
    metadata: Optional[str] = Form(None),
    current_user: User = Depends(current_user),
    file_service: FileService = Depends(get_file_service()),
):
    """
    Upload a file (Admin).
    
    - **file**: The file to upload
    - **file_type**: Type of file (avatar, document)
    - **metadata**: Optional JSON string with additional file metadata
    - **Returns**: File information including ID and storage details
    """
    import json
    
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
        uploaded_by=file_record.uploaded_by,
        created_at=file_record.created_at.isoformat(),
        metadata=file_record.file_metadata,
        url=download_url
    )


@router.get("/files/{file_id}", response_model=FileResponse)
async def get_file_info(
    file_id: UUID,
    current_user: User = Depends(current_user),
    file_service: FileService = Depends(get_file_service()),
):
    """
    Get file information by ID.
    
    - **file_id**: Unique file identifier
    - **Returns**: File metadata and information
    """
    file_record = await file_service.get_file_by_id(file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        id=file_record.id,
        filename=file_record.filename,
        content_type=file_record.content_type,
        file_size=file_record.file_size,
        file_type=file_record.file_type,
        uploaded_by=file_record.uploaded_by,
        created_at=file_record.created_at.isoformat(),
        metadata=file_record.file_metadata
    )


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: UUID,
    current_user: User = Depends(current_user),
    file_service: FileService = Depends(get_file_service()),
):
    """
    Download file content.
    
    - **file_id**: Unique file identifier
    - **Returns**: File content as streaming response
    """
    try:
        file_data, content_type, filename = await file_service.download_file(file_id)
        
        return StreamingResponse(
            file_data,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\""
            }
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Download failed")


@router.get("/files/{file_id}/url")
async def get_download_url(
    file_id: UUID,
    expiration: int = 3600,
    current_user: User = Depends(current_user),
    file_service: FileService = Depends(get_file_service()),
):
    """
    Get presigned download URL for file.
    
    - **file_id**: Unique file identifier
    - **expiration**: URL expiration time in seconds (default: 1 hour)
    - **Returns**: Presigned URL for direct file access
    """
    url = await file_service.generate_download_url(file_id, expiration)
    if not url:
        raise HTTPException(status_code=404, detail="File not found or URL generation failed")
    
    return {"download_url": url, "expiration": expiration}


@router.get("/files", response_model=FileListResponse)
async def list_files(
    file_type: Optional[FileType] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(current_user),
    file_service: FileService = Depends(get_file_service()),
):
    """
    List all files (Admin).
    
    - **file_type**: Optional filter by file type
    - **limit**: Maximum number of files to return (default: 50, max: 100)
    - **offset**: Pagination offset (default: 0)
    - **Returns**: List of all files
    """
    # Limit the maximum number of files that can be requested
    limit = min(limit, 100)
    
    files = await file_service.get_all_files(
        file_type=file_type,
        limit=limit,
        offset=offset
    )
    
    file_responses = []
    for file_record in files:
        # Generate download URL for each file
        download_url = await file_service.get_public_url(
            file_path=file_record.file_path
        )
        
        file_responses.append(
            FileResponse(
                id=file_record.id,
                filename=file_record.filename,
                content_type=file_record.content_type,
                file_size=file_record.file_size,
                file_type=file_record.file_type,
                file_path=file_record.file_path,
                uploaded_by=file_record.uploaded_by,
                created_at=file_record.created_at.isoformat(),
                metadata=file_record.file_metadata,
                url=download_url
            )
        )
    
    return FileListResponse(items=file_responses, total=len(file_responses))


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: UUID,
    current_user: User = Depends(current_user),
    file_service: FileService = Depends(get_file_service()),
):
    """
    Delete a file.
    
    - **file_id**: Unique file identifier
    - **Returns**: Success confirmation
    """
    success = await file_service.delete_file(file_id, current_user.id)
    if not success:
        raise HTTPException(status_code=500, detail="File deletion failed")
    
    return {"message": "File deleted successfully"}


@router.put("/files/{file_id}/metadata", response_model=FileResponse)
async def update_file_metadata(
    file_id: UUID,
    metadata: dict,
    current_user: User = Depends(current_user),
    file_service: FileService = Depends(get_file_service()),
):
    """
    Update file metadata.
    
    - **file_id**: Unique file identifier
    - **metadata**: New metadata to set
    - **Returns**: Updated file information
    """
    file_record = await file_service.update_file_metadata(
        file_id=file_id,
        user_id=current_user.id,
        metadata=metadata
    )
    
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        id=file_record.id,
        filename=file_record.filename,
        content_type=file_record.content_type,
        file_size=file_record.file_size,
        file_type=file_record.file_type,
        uploaded_by=file_record.uploaded_by,
        created_at=file_record.created_at.isoformat(),
        metadata=file_record.file_metadata
    )