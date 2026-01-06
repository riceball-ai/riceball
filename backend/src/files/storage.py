"""
Storage service for file upload and management.
Supports S3-compatible storage and local file system storage.
"""
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Optional, Tuple
from uuid import UUID

import aioboto3
import aiofiles
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config

from src.config import settings, StorageType

logger = logging.getLogger(__name__)



class BaseStorageService(ABC):
    """Abstract base class for storage services."""

    def _generate_file_key(self, file_type: str, file_id: UUID, filename: str) -> str:
        """
        Generate object key/path for file storage.
        
        Format: {file_type}/{year}/{month}/{day}/{file_id}.{ext}
        This provides organized storage with date-based partitioning.
        """
        now = datetime.now(timezone.utc)
        year = now.strftime("%Y")
        month = now.strftime("%m")
        day = now.strftime("%d")
        
        # Extract file extension from original filename
        file_ext = filename.split('.')[-1] if '.' in filename else ''
        file_name = f"{file_id}.{file_ext}" if file_ext else str(file_id)
        
        return f"{file_type}/{year}/{month}/{day}/{file_name}"

    @abstractmethod
    async def upload_file(
        self,
        file_data: BinaryIO | bytes,
        file_type: str,
        file_id: UUID,
        filename: str,
        content_type: str,
        file_size: int,
    ) -> str:
        pass

    @abstractmethod
    async def download_file(self, file_key: str) -> Tuple[BytesIO, str]:
        pass

    @abstractmethod
    async def delete_file(self, file_key: str) -> bool:
        pass

    @abstractmethod
    async def file_exists(self, file_key: str) -> bool:
        pass

    @abstractmethod
    def get_public_url_sync(self, file_key: str) -> str:
        """Synchronous version of get_public_url for use in Pydantic models."""
        pass

    @abstractmethod
    async def get_public_url(self, file_key: str) -> str:
        pass

    @abstractmethod
    async def generate_presigned_url(
        self,
        file_key: str,
        expiration: int = 3600,
        method: str = "get_object"
    ) -> Optional[str]:
        pass

    @abstractmethod
    async def get_file_metadata(self, file_key: str) -> Optional[dict]:
        pass
    
    async def upload_public_file(
        self,
        file_data: BinaryIO | bytes,
        file_type: str,
        file_id: UUID,
        filename: str,
        content_type: str,
        file_size: int,
    ) -> str:
        """
        Upload file and return file_key.
        """
        return await self.upload_file(
            file_data, file_type, file_id, filename, content_type, file_size
        )


class S3StorageService(BaseStorageService):
    """
    Service for handling file operations with S3-compatible storage.
    """
    
    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME
        self.region = settings.S3_REGION
        self.endpoint_url = settings.S3_ENDPOINT_URL
        self.external_endpoint_url = settings.S3_EXTERNAL_ENDPOINT_URL
        
        # Session configuration for S3-compatible storage
        self.session_config = {
            "aws_access_key_id": settings.S3_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.S3_SECRET_ACCESS_KEY.get_secret_value(),
            "region_name": self.region,
        }

    async def _get_client(self, endpoint_url: Optional[str] = None):
        """Get async S3 client with proper configuration."""
        session = aioboto3.Session(**self.session_config)
        
        # Client configuration - endpoint_url should be passed here, not to Session
        client_config = {}
        resolved_endpoint = endpoint_url if endpoint_url else self.endpoint_url
        if resolved_endpoint:
            client_config["endpoint_url"] = resolved_endpoint
            client_config["use_ssl"] = settings.S3_USE_SSL

            addressing_style = (settings.S3_ADDRESSING_STYLE or "path").lower()
            signature_version = settings.S3_SIGNATURE_VERSION or "s3v4"

            client_config["config"] = Config(
                s3={
                    "addressing_style": addressing_style,
                },
                signature_version=signature_version,
                # https://github.com/boto/boto3/issues/4400#issuecomment-2600742103
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required"
            )
            
        return session.client("s3", **client_config)

    async def upload_file(
        self,
        file_data: BinaryIO | bytes,
        file_type: str,
        file_id: UUID,
        filename: str,
        content_type: str,
        file_size: int,
    ) -> str:
        file_key = self._generate_file_key(file_type, file_id, filename)
        
        try:
            async with await self._get_client() as s3_client:
                # Upload file with metadata
                await s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=file_key,
                    Body=file_data,
                    ContentType=content_type,
                    ContentLength=file_size,
                    Metadata={
                        "file-id": str(file_id),
                        "file-type": file_type,
                        "original-filename": filename,
                        "upload-timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                
                logger.info(f"File uploaded successfully to S3: {file_key}")
                return file_key
                
        except ClientError as e:
            logger.error(f"Failed to upload file {filename}: {e}")
            raise
        except NoCredentialsError as e:
            logger.error(f"S3 credentials error: {e}")
            raise

    async def download_file(self, file_key: str) -> Tuple[BytesIO, str]:
        try:
            async with await self._get_client() as s3_client:
                response = await s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=file_key
                )
                
                # Read file data
                file_data = BytesIO()
                async for chunk in response["Body"]:
                    file_data.write(chunk)
                file_data.seek(0)
                
                content_type = response.get("ContentType", "application/octet-stream")
                
                logger.info(f"File downloaded successfully from S3: {file_key}")
                return file_data, content_type
                
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.warning(f"File not found in S3: {file_key}")
            else:
                logger.error(f"Failed to download file {file_key}: {e}")
            raise

    async def delete_file(self, file_key: str) -> bool:
        try:
            async with await self._get_client() as s3_client:
                await s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=file_key
                )
                
                logger.info(f"File deleted successfully from S3: {file_key}")
                return True
                
        except ClientError as e:
            logger.error(f"Failed to delete file {file_key}: {e}")
            return False

    async def file_exists(self, file_key: str) -> bool:
        try:
            async with await self._get_client() as s3_client:
                await s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=file_key
                )
                return True
                
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            logger.error(f"Error checking file existence {file_key}: {e}")
            return False

    def get_public_url_sync(self, file_key: str) -> str:
        base_url = self.external_endpoint_url if self.external_endpoint_url else self.endpoint_url
        base_url = base_url.rstrip('/')
        return f"{base_url}/{file_key}"

    async def get_public_url(self, file_key: str) -> str:
        return self.get_public_url_sync(file_key)

    async def generate_presigned_url(
        self,
        file_key: str,
        expiration: int = 3600,
        method: str = "get_object"
    ) -> Optional[str]:
        try:
            async with await self._get_client(endpoint_url=self.external_endpoint_url) as s3_client:
                url = await s3_client.generate_presigned_url(
                    method,
                    Params={"Bucket": self.bucket_name, "Key": file_key},
                    ExpiresIn=expiration
                )
                
                logger.info(f"Presigned URL generated for: {file_key}")
                return url
                
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {file_key}: {e}")
            return None

    async def get_file_metadata(self, file_key: str) -> Optional[dict]:
        try:
            async with await self._get_client() as s3_client:
                response = await s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=file_key
                )
                
                return {
                    "size": response.get("ContentLength", 0),
                    "content_type": response.get("ContentType", ""),
                    "last_modified": response.get("LastModified"),
                    "etag": response.get("ETag", "").strip('"'),
                    "metadata": response.get("Metadata", {}),
                }
                
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                logger.warning(f"File not found: {file_key}")
            else:
                logger.error(f"Failed to get metadata for {file_key}: {e}")
            return None
            
    async def create_bucket_if_not_exists(self) -> bool:
        """
        Create S3 bucket if it doesn't exist.
        """
        try:
            async with await self._get_client() as s3_client:
                # Check if bucket exists
                try:
                    await s3_client.head_bucket(Bucket=self.bucket_name)
                    logger.info(f"Bucket {self.bucket_name} already exists")
                    return True
                except ClientError as e:
                    if e.response["Error"]["Code"] != "404":
                        raise
                
                # Create bucket
                create_params = {"Bucket": self.bucket_name}
                
                # Add location constraint for regions other than us-east-1
                if self.region and self.region != "us-east-1":
                    create_params["CreateBucketConfiguration"] = {
                        "LocationConstraint": self.region
                    }
                
                await s3_client.create_bucket(**create_params)
                logger.info(f"Bucket {self.bucket_name} created successfully")
                return True
                
        except ClientError as e:
            logger.error(f"Failed to create bucket {self.bucket_name}: {e}")
            return False


class FileSystemStorageService(BaseStorageService):
    """
    Service for handling file operations with local file system.
    """
    
    def __init__(self):
        self.base_path = settings.LOCAL_STORAGE_PATH or (settings.STORAGE_DIR / "files")
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized FileSystemStorageService at {self.base_path}")

    def _get_full_path(self, file_key: str) -> Path:
        return self.base_path / file_key

    async def upload_file(
        self,
        file_data: BinaryIO | bytes,
        file_type: str,
        file_id: UUID,
        filename: str,
        content_type: str,
        file_size: int,
    ) -> str:
        file_key = self._generate_file_key(file_type, file_id, filename)
        full_path = self._get_full_path(file_key)
        
        # Ensure directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            async with aiofiles.open(full_path, 'wb') as f:
                if isinstance(file_data, bytes):
                    await f.write(file_data)
                else:
                    await f.write(file_data.read())
            
            logger.info(f"File uploaded successfully to local storage: {file_key}")
            return file_key
        except Exception as e:
            logger.error(f"Failed to upload file {filename} to local storage: {e}")
            raise

    async def download_file(self, file_key: str) -> Tuple[BytesIO, str]:
        full_path = self._get_full_path(file_key)
        
        if not full_path.exists():
            logger.warning(f"File not found in local storage: {file_key}")
            raise FileNotFoundError(f"File not found: {file_key}")
            
        try:
            async with aiofiles.open(full_path, 'rb') as f:
                content = await f.read()
                
            # Simple content type guessing or default
            # In a real app, we might store metadata in a sidecar file or DB
            content_type = "application/octet-stream" 
            
            return BytesIO(content), content_type
        except Exception as e:
            logger.error(f"Failed to download file {file_key} from local storage: {e}")
            raise

    async def delete_file(self, file_key: str) -> bool:
        full_path = self._get_full_path(file_key)
        
        try:
            if full_path.exists():
                os.remove(full_path)
                logger.info(f"File deleted successfully from local storage: {file_key}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete file {file_key} from local storage: {e}")
            return False

    async def file_exists(self, file_key: str) -> bool:
        return self._get_full_path(file_key).exists()

    def get_public_url_sync(self, file_key: str) -> str:
        # Assuming we mount the static files at /static/files
        # This needs to be coordinated with main.py
        base_url = str(settings.EXTERNAL_URL or settings.FRONTEND_URL).rstrip('/')
        return f"{base_url}/api/v1/files/static/{file_key}"

    async def get_public_url(self, file_key: str) -> str:
        return self.get_public_url_sync(file_key)

    async def generate_presigned_url(
        self,
        file_key: str,
        expiration: int = 3600,
        method: str = "get_object"
    ) -> Optional[str]:
        # For local storage, we just return the public URL
        return await self.get_public_url(file_key)

    async def get_file_metadata(self, file_key: str) -> Optional[dict]:
        full_path = self._get_full_path(file_key)
        
        if not full_path.exists():
            return None
            
        stat = full_path.stat()
        return {
            "size": stat.st_size,
            "content_type": "application/octet-stream", # Placeholder
            "last_modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            "etag": "",
            "metadata": {},
        }


def get_storage_service() -> BaseStorageService:
    if settings.STORAGE_TYPE == StorageType.LOCAL:
        return FileSystemStorageService()
    return S3StorageService()

# Global storage service instance
storage_service = get_storage_service()