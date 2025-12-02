import uuid
from typing import Optional, Dict, Any, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import Base

if TYPE_CHECKING:
    from src.ai_models.models import Model


class KnowledgeBase(Base):
    """Knowledge Base Table"""
    __tablename__ = "knowledge_bases"
    
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Configuration
    embedding_model_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("models.id", ondelete="SET NULL"),
        nullable=True
    )
    chunk_size: Mapped[int] = mapped_column(Integer, default=1000)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=200)
    
    # Embedding configuration (optional, stores model-specific parameters)
    embedding_config: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Associated user
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    
    # Relationships
    embedding_model: Mapped[Optional["Model"]] = relationship(
        "Model", 
        foreign_keys=[embedding_model_id],
        post_update=True
    )


class Document(Base):
    """Document Table"""
    __tablename__ = "documents"
    
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    file_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # File type, e.g., 'pdf', 'txt', 'docx', 'md', 'html' etc.
    doc_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Associated knowledge base
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Associated user
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Document status
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    
    # Relationships
    knowledge_base: Mapped["KnowledgeBase"] = relationship("KnowledgeBase", backref="documents")


class DocumentChunk(Base):
    """Document Chunk Table"""
    __tablename__ = "document_chunks"
    
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Associated document
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Metadata
    chunk_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Relationships
    document: Mapped["Document"] = relationship("Document", backref="chunks")
