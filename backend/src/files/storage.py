"""
S3-compatible storage service for file upload and management.
"""
import logging
from datetime import datetime, timezone
from io import BytesIO
from typing import BinaryIO, Optional, Tuple
from uuid import UUID

import aioboto3
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config

from src.config import settings

logger = logging.getLogger(__name__)


class S3StorageService:
    """
    Service for handling file operations with S3-compatible storage.
    
    Supports AWS S3 and S3-compatible systems like MinIO, LocalStack, etc.
    Provides async operations for upload, download, delete, and presigned URLs.
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

    def _generate_file_key(self, file_type: str, file_id: UUID, filename: str) -> str:
        """
        Generate S3 object key for file storage.
        
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

    async def upload_file(
        self,
        file_data: BinaryIO,
        file_type: str,
        file_id: UUID,
        filename: str,
        content_type: str,
        file_size: int,
    ) -> str:
        """
        Upload file to S3-compatible storage.
        
        Args:
            file_data: Binary file data
            file_type: Type of file (avatar, document, etc.)
            file_id: Unique file identifier
            filename: Original filename
            content_type: MIME type of the file
            file_size: Size of the file in bytes
            
        Returns:
            S3 object key of uploaded file
            
        Raises:
            ClientError: If S3 operation fails
            NoCredentialsError: If S3 credentials are invalid
        """
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
                
                logger.info(f"File uploaded successfully: {file_key}")
                return file_key
                
        except ClientError as e:
            logger.error(f"Failed to upload file {filename}: {e}")
            raise
        except NoCredentialsError as e:
            logger.error(f"S3 credentials error: {e}")
            raise

    async def upload_public_file(
        self,
        file_data: BinaryIO,
        file_type: str,
        file_id: UUID,
        filename: str,
        content_type: str,
        file_size: int,
    ) -> Tuple[str, str]:
        """
        Upload file to S3-compatible storage and return both file_key and public_url.
        
        Args:
            file_data: Binary file data
            file_type: Type of file (avatar, document, etc.)
            file_id: Unique file identifier
            filename: Original filename
            content_type: MIME type of the file
            file_size: Size of the file in bytes
            
        Returns:
            Tuple of (file_key, public_url)
            
        Raises:
            ClientError: If S3 operation fails
            NoCredentialsError: If S3 credentials are invalid
        """
        # Upload file first
        file_key = await self.upload_file(
            file_data, file_type, file_id, filename, content_type, file_size
        )
    
        return file_key

    async def download_file(self, file_key: str) -> Tuple[BytesIO, str]:
        """
        Download file from S3-compatible storage.
        
        Args:
            file_key: S3 object key
            
        Returns:
            Tuple of (file_data, content_type)
            
        Raises:
            ClientError: If file not found or S3 operation fails
        """
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
                
                logger.info(f"File downloaded successfully: {file_key}")
                return file_data, content_type
                
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.warning(f"File not found: {file_key}")
            else:
                logger.error(f"Failed to download file {file_key}: {e}")
            raise

    async def delete_file(self, file_key: str) -> bool:
        """
        Delete file from S3-compatible storage.
        
        Args:
            file_key: S3 object key
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            async with await self._get_client() as s3_client:
                await s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=file_key
                )
                
                logger.info(f"File deleted successfully: {file_key}")
                return True
                
        except ClientError as e:
            logger.error(f"Failed to delete file {file_key}: {e}")
            return False

    async def file_exists(self, file_key: str) -> bool:
        """
        Check if file exists in S3-compatible storage.
        
        Args:
            file_key: S3 object key
            
        Returns:
            True if file exists, False otherwise
        """
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

    async def get_public_url(self, file_key: str) -> str:
        """
        Generate public URL for file access (requires bucket to have public read access).
        
        Args:
            file_key: S3 object key
            
        Returns:
            Public URL string
        """
        base_url = self.external_endpoint_url if self.external_endpoint_url else self.endpoint_url
        base_url = base_url.rstrip('/')
        return f"{base_url}/{file_key}"

    async def generate_presigned_url(
        self,
        file_key: str,
        expiration: int = 3600,
        method: str = "get_object"
    ) -> Optional[str]:
        """
        Generate presigned URL for file access.
        
        Args:
            file_key: S3 object key
            expiration: URL expiration time in seconds (default: 1 hour)
            method: S3 method (get_object, put_object, etc.)
            
        Returns:
            Presigned URL string or None if generation fails
        """
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
        """
        Get file metadata from S3-compatible storage.
        
        Args:
            file_key: S3 object key
            
        Returns:
            Dictionary containing file metadata or None if file not found
        """
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
        
        Returns:
            True if bucket exists or was created successfully, False otherwise
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


# Global storage service instance
storage_service = S3StorageService()