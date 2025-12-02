from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import uuid
from datetime import datetime
from ...vector_store import VectorDocument


class KnowledgeBaseCreate(BaseModel):
    """Create Knowledge Base Request"""
    name: str = Field(..., max_length=200, description="Knowledge base name")
    description: Optional[str] = Field(None, description="Knowledge base description")
    embedding_model_id: Optional[str] = Field(
        None, 
        description="Embedding model ID (UUID format)"
    )
    chunk_size: Optional[int] = Field(
        default=1000, 
        ge=100, 
        le=8000, 
        description="Document chunk size"
    )
    chunk_overlap: Optional[int] = Field(
        default=200, 
        ge=0, 
        le=1000, 
        description="Chunk overlap size"
    )


class KnowledgeBaseUpdate(BaseModel):
    """Update Knowledge Base Request"""
    name: Optional[str] = Field(None, max_length=200, description="Knowledge base name")
    description: Optional[str] = Field(None, description="Knowledge base description")
    embedding_model_id: Optional[str] = Field(None, description="Embedding model ID (UUID format)")
    chunk_size: Optional[int] = Field(
        None, 
        ge=100, 
        le=8000, 
        description="Document chunk size"
    )
    chunk_overlap: Optional[int] = Field(
        None, 
        ge=0, 
        le=1000, 
        description="Chunk overlap size"
    )


class KnowledgeBaseResponse(BaseModel):
    """Knowledge Base Response"""
    id: uuid.UUID
    name: str
    description: Optional[str]
    embedding_model_id: Optional[uuid.UUID]
    chunk_size: int
    chunk_overlap: int
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DocumentCreate(BaseModel):
    """Create Document Request"""
    title: str = Field(..., max_length=500, description="Document title")
    content: str = Field(..., min_length=1, description="Document content")
    knowledge_base_id: uuid.UUID = Field(..., description="Knowledge base ID")
    source_url: Optional[str] = Field(None, max_length=1000, description="Source URL")
    file_path: Optional[str] = Field(None, max_length=1000, description="File path")
    file_type: Optional[str] = Field(None, max_length=50, description="File type, e.g., 'pdf', 'txt', 'docx', 'md' etc.")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata")


class DocumentCreateFromFile(BaseModel):
    """Create Document From File Request"""
    file_path: str = Field(..., max_length=1000, description="File storage path")
    knowledge_base_id: uuid.UUID = Field(..., description="Knowledge base ID")
    filename: Optional[str] = Field(None, max_length=255, description="Original filename (optional, used to infer title and file type)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Extra metadata")


class DocumentResponse(BaseModel):
    """Document Response"""
    id: uuid.UUID
    title: str
    source_url: Optional[str]
    file_path: Optional[str]
    file_type: Optional[str]
    knowledge_base_id: uuid.UUID
    status: str
    doc_metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Document List Response"""
    id: uuid.UUID
    title: str
    source_url: Optional[str]
    file_path: Optional[str]
    file_type: Optional[str]
    knowledge_base_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime
    # Exclude full content to reduce response size
    
    class Config:
        from_attributes = True


class RAGQueryRequest(BaseModel):
    """RAG Query Request"""
    query: str = Field(..., min_length=1, max_length=2000, description="Query question")
    knowledge_base_id: uuid.UUID = Field(..., description="Knowledge base ID")
    k: int = Field(default=5, ge=1, le=20, description="Number of relevant documents to return")


class ChunkInfo(BaseModel):
    """Document Chunk Info"""
    content: str
    metadata: Dict[str, Any]
    score: float
    similarity: float


class RAGQueryResponse(BaseModel):
    """RAG Query Response"""
    query: str
    knowledge_base_id: uuid.UUID
    documents: List[VectorDocument]


class RAGChatRequest(BaseModel):
    """RAG Chat Request"""
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    knowledge_base_id: uuid.UUID = Field(..., description="Knowledge base ID")
    conversation_id: Optional[uuid.UUID] = Field(None, description="Conversation ID")
    k: int = Field(default=3, ge=1, le=10, description="Number of documents to retrieve")
    score_threshold: Optional[float] = Field(
        None, 
        ge=0.0, 
        le=1.0, 
        description="Similarity threshold (0-1), recommended: 0.3-0.6. Higher values are stricter, >0.7 may filter out most results"
    )


class RAGChatResponse(BaseModel):
    """RAG Chat Response"""
    message: str
    response: str
    knowledge_base_id: uuid.UUID
    conversation_id: Optional[uuid.UUID]
    relevant_chunks: List[ChunkInfo]
    

class DocumentChunkResponse(BaseModel):
    """Document Chunk Response"""
    id: uuid.UUID
    content: str
    chunk_index: int
    token_count: Optional[int]
    document_id: uuid.UUID
    chunk_metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DocumentChunkListResponse(BaseModel):
    """Document Chunk List Response"""
    id: uuid.UUID
    content: str
    chunk_index: int
    token_count: Optional[int]
    document_id: uuid.UUID
    chunk_metadata: Dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    """Error Response"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None