"""
Document content extraction service for RAG system.
"""
import logging
import mimetypes
import os
from io import BytesIO
from pathlib import Path
from typing import Tuple, Optional

from fastapi import HTTPException
from src.files.service import FileService

logger = logging.getLogger(__name__)


class DocumentContentExtractor:
    """Document content extractor"""
    
    def __init__(self, file_service: FileService):
        self.file_service = file_service
        
    async def extract_from_file_path(
        self, 
        file_path: str, 
        filename: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Extract document content and title from file path
        
        Args:
            file_path: File storage path (S3 key)
            filename: Original filename (optional, used to infer file type)
            
        Returns:
            Tuple[title, content]: Document title and content
            
        Raises:
            HTTPException: If file does not exist or extraction fails
        """
        try:
            # Download file from storage service
            file_data, content_type = await self._download_file_from_storage(file_path)
            
            # If filename is not provided, try to infer from file_path
            if not filename:
                filename = os.path.basename(file_path)
            
            # Extract content by content type
            content = await self._extract_content_by_type(file_data, content_type, filename)
            
            # Extract title from filename (remove extension)
            title = self._extract_title_from_filename(filename)
            
            return title, content
            
        except Exception as e:
            logger.error(f"Failed to extract content from file {file_path}: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to extract content from file: {str(e)}"
            )
    
    async def _download_file_from_storage(self, file_path: str) -> Tuple[BytesIO, str]:
        """Download file from storage service"""
        try:
            from src.files.storage import storage_service
            return await storage_service.download_file(file_path)
        except Exception as e:
            logger.error(f"Failed to download file from storage: {e}")
            raise HTTPException(
                status_code=404,
                detail="File not found in storage"
            )
    
    async def _extract_content_by_type(
        self, 
        file_data: BytesIO, 
        content_type: str, 
        filename: str
    ) -> str:
        """Extract content by file type"""
        
        # Reset file pointer
        file_data.seek(0)
        
        # Prefer content_type, if undetermined infer from file extension
        if not content_type or content_type == "application/octet-stream":
            content_type, _ = mimetypes.guess_type(filename)
        
        if not content_type:
            # If still undetermined, try to infer from extension
            ext = Path(filename).suffix.lower()
            content_type = self._get_content_type_from_extension(ext)
        
        logger.info(f"Extracting content for file {filename} with content type: {content_type}")
        
        # Use markitdown for unified document processing
        try:
            from markitdown import MarkItDown
            
            # Save file to temporary location
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as temp_file:
                file_data.seek(0)
                temp_file.write(file_data.read())
                temp_file_path = temp_file.name
            
            try:
                md = MarkItDown()
                result = md.convert(temp_file_path)
                content = result.text_content
                
                if not content.strip():
                    raise ValueError("No text content extracted from file")
                
                return content.strip()
            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)
                
        except ImportError:
            logger.warning("markitdown not available, falling back to basic extraction")
            # If markitdown is not available, fallback to basic text extraction
            return await self._extract_text_content(file_data)
        except Exception as e:
            logger.warning(f"markitdown extraction failed: {e}, falling back to basic extraction")
            # If markitdown fails, fallback to basic text extraction
            return await self._extract_text_content(file_data)
    
    def _get_content_type_from_extension(self, ext: str) -> str:
        """Infer content type from file extension"""
        ext_mapping = {
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xls": "application/vnd.ms-excel",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        return ext_mapping.get(ext, "text/plain")
    
    async def _extract_text_content(self, file_data: BytesIO) -> str:
        """Extract plain text content"""
        try:
            # Try multiple encodings
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
            
            for encoding in encodings:
                try:
                    file_data.seek(0)
                    content = file_data.read().decode(encoding)
                    logger.info(f"Successfully decoded text with encoding: {encoding}")
                    return content.strip()
                except UnicodeDecodeError:
                    continue
            
            # If all encodings fail, use error handling
            file_data.seek(0)
            content = file_data.read().decode('utf-8', errors='ignore')
            logger.warning("Fallback to utf-8 with error handling")
            return content.strip()
            
        except Exception as e:
            logger.error(f"Failed to extract text content: {e}")
            raise HTTPException(
                status_code=400,
                detail="Failed to extract text content"
            )
    
    def _extract_title_from_filename(self, filename: str) -> str:
        if not filename:
            return "Untitled Document"
        
        title = Path(filename).stem
        
        title = title.replace('_', ' ').replace('-', ' ')
        
        title = ' '.join(word.capitalize() for word in title.split())
        
        return title or "Untitled Document"