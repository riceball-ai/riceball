import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate as sqlalchemy_paginate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional

from src.database import get_async_session
from src.auth import current_superuser
from src.users.models import User
from ...service import RAGService
from ...models import KnowledgeBase, Document
from .schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    DocumentCreateFromFile,
    DocumentResponse,
    DocumentListResponse,
    DocumentChunkListResponse,
    RAGQueryRequest,
    RAGQueryResponse
)

router = APIRouter()


# TODO: Modifying knowledge base cannot change embedding model because it involves rebuilding vector database, not supported yet

@router.get(
    "/knowledge-bases", 
    response_model=Page[KnowledgeBaseResponse],
    summary="Get all knowledge bases (Admin)",
    description="Admin view all users' knowledge bases"
)
async def list_all_knowledge_bases(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_superuser)
):
    """Get all knowledge bases (Admin)"""
    try:
        query = (
            select(KnowledgeBase)
            .where(KnowledgeBase.status == "ACTIVE")
            .order_by(KnowledgeBase.created_at.desc())
        )
        return await sqlalchemy_paginate(session, query)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve knowledge bases"
        )

@router.get(
    "/knowledge-bases/all",
    response_model=list[KnowledgeBaseResponse],
    summary="Get all knowledge bases (No pagination)",
    description="Admin view all knowledge bases list, without pagination"
)
async def list_all_knowledge_bases_without_pagination(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_superuser)
):
    """Get all knowledge bases (No pagination)"""
    try:
        result = await session.execute(
            select(KnowledgeBase)
            .where(KnowledgeBase.status == "ACTIVE")
            .order_by(KnowledgeBase.created_at.desc())
        )
        return result.scalars().all()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve knowledge bases"
        )


@router.post(
    "/knowledge-bases", 
    response_model=KnowledgeBaseResponse,
    summary="Create knowledge base",
    description="Create a new knowledge base for storing and retrieving documents"
)
async def create_knowledge_base(
    kb_data: KnowledgeBaseCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_superuser)
):
    """Create knowledge base"""
    try:
        service = RAGService(session)
        
        kb = await service.create_knowledge_base(
            name=kb_data.name,
            description=kb_data.description,
            embedding_model_id=kb_data.embedding_model_id,
            chunk_size=kb_data.chunk_size,
            chunk_overlap=kb_data.chunk_overlap,
            owner_id=current_user.id,
        )
        return kb
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create knowledge base"
        )


@router.put(
    "/knowledge-bases/{kb_id}",
    response_model=KnowledgeBaseResponse,
    summary="Update knowledge base",
    description="Update knowledge base basic info (Changing embedding model is not supported; adjusting chunk parameters does not automatically rebuild vectors)"
)
async def update_knowledge_base(
    kb_id: uuid.UUID,
    kb_data: KnowledgeBaseUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_superuser)
):
    """Update knowledge base

    Limitations:
    - Changing embedding_model_id is not allowed (involves vector rebuilding, migration process will be provided separately)
    - Modifying chunk_size / chunk_overlap currently does not automatically re-chunk existing documents, only affects subsequent new documents
    """
    try:
        # Query knowledge base
        result = await session.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        )
        kb = result.scalar_one_or_none()
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base not found"
            )

        # Allow setting embedding_model_id for the first time, but forbid modification if it already exists
        if kb_data.embedding_model_id is not None:
            if kb.embedding_model_id is None:
                kb.embedding_model_id = kb_data.embedding_model_id
                changed = True
            elif str(kb.embedding_model_id) != kb_data.embedding_model_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Changing embedding_model_id is not supported. Create a new knowledge base instead."
                )

        # Fields allowed to update
        updatable_fields = [
            ("name", kb_data.name),
            ("description", kb_data.description),
            ("chunk_size", kb_data.chunk_size),
            ("chunk_overlap", kb_data.chunk_overlap),
        ]

        changed = False
        for field_name, new_value in updatable_fields:
            if new_value is not None and getattr(kb, field_name) != new_value:
                setattr(kb, field_name, new_value)
                changed = True

        if not changed:
            return kb  # Return directly if no changes

        # TODO: If re-chunking existing documents is needed in the future, trigger background job here
        # e.g.: enqueue_rechunk_job(kb_id)

        await session.commit()
        await session.refresh(kb)
        return kb
    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update knowledge base"
        )

@router.get(
    "/knowledge-bases/{kb_id}", 
    response_model=KnowledgeBaseResponse,
    summary="Get knowledge base details (Admin)",
    description="Admin view details of any knowledge base"
)
async def get_knowledge_base_admin(
    kb_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_superuser)
):
    """Get knowledge base details (Admin)"""
    try:
        result = await session.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id
            )
        )
        kb = result.scalar_one_or_none()
        
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base not found"
            )
        
        return kb
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve knowledge base"
        )


@router.get(
    "/knowledge-bases/{kb_id}/documents", 
    response_model=Page[DocumentListResponse],
    summary="Get knowledge base documents (Admin)",
    description="Admin view all documents in any knowledge base"
)
async def list_documents_admin(
    kb_id: uuid.UUID,
    file_type: Optional[str] = None,
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session),
):
    """Get document list in knowledge base (Admin)"""
    try:
        # Verify knowledge base exists
        kb_result = await session.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        )
        if not kb_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base not found"
            )
        
        # Build query conditions
        conditions = [
            Document.knowledge_base_id == kb_id,
            Document.status == "ACTIVE"
        ]
        
        # Add filter condition if file type is specified
        if file_type:
            conditions.append(Document.file_type == file_type)

        # Add search condition
        if search:
            conditions.append(Document.title.ilike(f"%{search}%"))
        
        query = (
            select(Document)
            .where(and_(*conditions))
            .order_by(Document.created_at.desc())
        )
        return await sqlalchemy_paginate(session, query)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve documents"
        )


@router.post(
    "/documents/from-file", 
    response_model=DocumentResponse,
    summary="Add document from file",
    description="Automatically extract content from uploaded file path and add to knowledge base"
)
async def add_document_from_file(
    doc_data: DocumentCreateFromFile,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_superuser)
):
    """Add document to knowledge base from file path"""
    try:
        from src.files.service import FileService
        
        # Create file service instance
        file_service = FileService(session)
        
        # Create RAG service instance, passing file service
        service = RAGService(session, file_service)
        
        document = await service.add_document_from_file(
            file_path=doc_data.file_path,
            knowledge_base_id=doc_data.knowledge_base_id,
            owner_id=current_user.id,
            filename=doc_data.filename,
            metadata=doc_data.metadata
        )
        return document
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add document from file"
        )


@router.get(
    "/documents/{doc_id}", 
    response_model=DocumentResponse,
    summary="Get document details",
    description="Get detailed information of a specific document"
)
async def get_document(
    doc_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_superuser)
):
    """Get document details"""
    try:
        from sqlalchemy import select, and_
        from ...models import Document
        
        result = await session.execute(
            select(Document).where(
                and_(
                    Document.id == doc_id,
                    Document.owner_id == current_user.id,
                    Document.status == "ACTIVE"
                )
            )
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        return document
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document"
        )


@router.get(
    "/documents/{doc_id}/chunks", 
    response_model=Page[DocumentChunkListResponse],
    summary="Get document chunks (Admin)",
    description="Admin view all chunks of any document"
)
async def get_document_chunks(
    doc_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_superuser)
):
    """Get document chunks (Admin)"""
    try:
        service = RAGService(session)
        
        # Admin can view chunks of any document, no owner_id verification needed
        chunks = await service.get_document_chunks(
            document_id=doc_id,
            owner_id=None,  # Admin permission, no owner restriction
            skip=0,
            limit=1000  # Set a large limit to get all chunks
        )
        
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or has no chunks"
            )
        
        # Use fastapi_pagination for pagination
        from sqlalchemy import select
        from ...models import DocumentChunk
        
        query = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == doc_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        return await sqlalchemy_paginate(session, query)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document chunks"
        )


@router.delete(
    "/knowledge-bases/{kb_id}",
    summary="Delete knowledge base (Admin)",
    description="Admin delete any knowledge base and all its documents"
)
async def delete_knowledge_base_admin(
    kb_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_superuser)
):
    """Delete knowledge base (Admin)"""
    try:
        # Get knowledge base
        kb_result = await session.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        )
        kb = kb_result.scalar_one_or_none()
        
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base not found"
            )
        
        # Soft delete knowledge base
        kb.status = "DELETED"
        
        # Soft delete all related documents
        documents_result = await session.execute(
            select(Document).where(
                Document.knowledge_base_id == kb_id,
                Document.status == "ACTIVE"
            )
        )
        documents = documents_result.scalars().all()
        
        for doc in documents:
            doc.status = "DELETED"
        
        await session.commit()
        
        return {
            "message": "Knowledge base deleted successfully",
            "deleted_documents": len(documents)
        }
    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete knowledge base"
        )


@router.delete(
    "/documents/{doc_id}",
    summary="Delete document (Admin)",
    description="Admin delete any document"
)
async def delete_document_admin(
    doc_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_superuser)
):
    """Delete document (Admin)"""
    try:
        # Get document
        result = await session.execute(
            select(Document).where(Document.id == doc_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Use RAG service to delete (including vector database cleanup)
        service = RAGService(session)
        # Temporarily set document owner to current admin user to pass permission check
        original_owner = document.owner_id
        success = await service.delete_document(doc_id, original_owner)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        return {"message": "Document deleted successfully"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )
    


@router.post(
    "/get_relevant_documents", 
    response_model=RAGQueryResponse,
)
async def rag_query(
    query_data: RAGQueryRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """RAG Query"""
    try:
        service = RAGService(session)
        docs = await service.relevance_search(
            query=query_data.query,
            knowledge_base_id=query_data.knowledge_base_id,
            k=query_data.k,
        )
        
        return RAGQueryResponse(
            query=query_data.query,
            knowledge_base_id=query_data.knowledge_base_id,
            documents=docs
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get relevant documents"
        )


@router.get(
    "/stats",
    summary="Get system statistics (Admin)",
    description="Get usage statistics of the RAG system"
)
async def get_rag_stats(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(current_superuser)
):
    """Get RAG system statistics"""
    try:
        # Count knowledge bases
        kb_count_result = await session.execute(
            select(func.count(KnowledgeBase.id)).where(
                KnowledgeBase.status == "ACTIVE"
            )
        )
        kb_count = kb_count_result.scalar() or 0
        
        # Count documents
        doc_count_result = await session.execute(
            select(func.count(Document.id)).where(
                Document.status == "ACTIVE"
            )
        )
        doc_count = doc_count_result.scalar() or 0
        
        # Count knowledge bases by user
        kb_by_user_result = await session.execute(
            select(
                func.count(KnowledgeBase.id).label('count'),
                KnowledgeBase.owner_id
            )
            .where(KnowledgeBase.status == "ACTIVE")
            .group_by(KnowledgeBase.owner_id)
        )
        kb_by_user = kb_by_user_result.all()
        
        return {
            "total_knowledge_bases": kb_count,
            "total_documents": doc_count,
            "knowledge_bases_by_user": [
                {"user_id": str(row.owner_id), "count": row.count}
                for row in kb_by_user
            ],
            "avg_documents_per_kb": round(doc_count / kb_count, 2) if kb_count > 0 else 0
        }
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )