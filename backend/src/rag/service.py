import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from langchain_core.documents import Document as VectorDocument
import logging
import asyncio

from .models import Document, DocumentChunk, KnowledgeBase
from .schemas import RetrievalResult, RetrievalChunk
from .embeddings import EmbeddingService
from .chunker import DocumentChunker
from .content_extractor import DocumentContentExtractor
from .vector_store import ChromaVectorStore
from src.files.service import FileService

logger = logging.getLogger(__name__)


class RAGService:
    """RAG Core Service"""
    
    def __init__(self, session: AsyncSession, file_service: Optional[FileService] = None):
        self.session = session
        self.embedding_service = EmbeddingService()
        self.chunker = DocumentChunker()
        self.vector_store = ChromaVectorStore()
        
        # If file service is not provided, create a new instance
        if file_service:
            self.file_service = file_service
        else:
            self.file_service = FileService(session)
        
        self.content_extractor = DocumentContentExtractor(self.file_service)
    
    def _infer_file_type(self, filename: Optional[str], file_path: Optional[str]) -> Optional[str]:
        """Infer file type from filename or path"""
        if not filename and not file_path:
            return None
        
        # Prefer filename, then file_path
        target_name = filename or file_path
        if not target_name:
            return None
        
        # Extract file extension
        from pathlib import Path
        ext = Path(target_name).suffix.lower()
        
        # Extension to file type mapping
        ext_mapping = {
            '.txt': 'txt',
            '.md': 'md',
            '.markdown': 'md',
            '.pdf': 'pdf',
            '.doc': 'doc',
            '.docx': 'docx',
            '.xls': 'xls',
            '.xlsx': 'xlsx',
            '.ppt': 'ppt',
            '.pptx': 'pptx',
            '.csv': 'csv',
            '.json': 'json',
            '.xml': 'xml',
            '.html': 'html',
            '.htm': 'html',
            '.rtf': 'rtf',
            '.odt': 'odt',
            '.ods': 'ods',
            '.odp': 'odp',
        }
        
        return ext_mapping.get(ext)
    
    async def create_knowledge_base(
        self,
        name: str,
        description: Optional[str],
        embedding_model_id: Optional[str],
        chunk_size: Optional[int],
        chunk_overlap: Optional[int],
        owner_id: uuid.UUID,
    ) -> KnowledgeBase:
        """Create knowledge base"""
        try:
            # Check if name already exists
            existing_kb = await self.session.execute(
                select(KnowledgeBase).where(
                    and_(
                        KnowledgeBase.name == name,
                        KnowledgeBase.owner_id == owner_id,
                        KnowledgeBase.status == "ACTIVE"
                    )
                )
            )
            if existing_kb.scalar_one_or_none():
                raise ValueError(f"Knowledge base with name '{name}' already exists")
            
            kb_data = {
                "name": name,
                "description": description,
                "owner_id": owner_id,
                "embedding_model_id": embedding_model_id,
                "chunk_size": chunk_size or 1000,
                "chunk_overlap": chunk_overlap or 200,
            }
            
            kb = KnowledgeBase(**kb_data)
            
            self.session.add(kb)
            await self.session.commit()
            await self.session.refresh(kb)
            
            logger.info(f"Created knowledge base: {kb.name} (ID: {kb.id})")
            return kb
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create knowledge base: {e}")
            raise
    
    async def get_knowledge_bases(
        self, 
        owner_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[KnowledgeBase]:
        """Get user's knowledge base list"""
        result = await self.session.execute(
            select(KnowledgeBase)
            .where(
                and_(
                    KnowledgeBase.owner_id == owner_id,
                    KnowledgeBase.status == "ACTIVE"
                )
            )
            .offset(skip)
            .limit(limit)
            .order_by(KnowledgeBase.created_at.desc())
        )
        return result.scalars().all()
    
    async def get_knowledge_base(
        self, 
        kb_id: uuid.UUID, 
        owner_id: Optional[uuid.UUID] = None
    ) -> Optional[KnowledgeBase]:
        """Get specific knowledge base"""
        if owner_id is not None:
            # Query with permission check
            result = await self.session.execute(
                select(KnowledgeBase).where(
                    and_(
                        KnowledgeBase.id == kb_id,
                        KnowledgeBase.owner_id == owner_id,
                        KnowledgeBase.status == "ACTIVE"
                    )
                )
            )
        else:
            # Query without permission check
            result = await self.session.execute(
                select(KnowledgeBase).where(
                    and_(
                        KnowledgeBase.id == kb_id,
                        KnowledgeBase.status == "ACTIVE"
                    )
                )
            )
        return result.scalar_one_or_none()
    
    async def add_document_from_file(
        self,
        file_path: str,
        knowledge_base_id: uuid.UUID,
        owner_id: uuid.UUID,
        filename: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Document:
        """Add document to knowledge base from file path"""
        try:
            # Verify knowledge base exists and belongs to user
            kb = await self.get_knowledge_base(knowledge_base_id, owner_id)
            if not kb:
                raise ValueError("Knowledge base not found or access denied")
            
            # Find corresponding file record from database to get original filename as title
            file_record = await self.file_service.get_file_by_path(file_path)
            if file_record:
                title = file_record.filename
                original_filename = file_record.filename
            else:
                # If file record not found, use passed filename or extract from path
                title = filename or file_path.split('/')[-1]
                original_filename = filename
            
            # Infer file type
            file_type = self._infer_file_type(original_filename, file_path)
            
            # Extract content from file path using content extractor
            _, content = await self.content_extractor.extract_from_file_path(
                file_path, original_filename
            )
            
            # Merge metadata
            combined_metadata = {
                "source_type": "file",
                "original_filename": original_filename,
                **(metadata or {})
            }
            
            # Call existing add document method
            document = await self.add_document(
                title=title,
                content=content,
                knowledge_base_id=knowledge_base_id,
                owner_id=owner_id,
                file_path=file_path,
                file_type=file_type,
                metadata=combined_metadata
            )
            
            logger.info(f"Added document '{title}' from file '{file_path}' to knowledge base {knowledge_base_id}")
            return document
            
        except Exception as e:
            logger.error(f"Failed to add document from file: {e}")
            raise
    
    async def add_document(
        self,
        title: str,
        content: str,
        knowledge_base_id: uuid.UUID,
        owner_id: uuid.UUID,
        source_url: Optional[str] = None,
        file_path: Optional[str] = None,
        file_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Document:
        """Add document to knowledge base"""
        try:
            # Verify knowledge base exists and belongs to user
            kb = await self.get_knowledge_base(knowledge_base_id, owner_id)
            if not kb:
                raise ValueError("Knowledge base not found or access denied")
            
            # If file_type not provided, try to infer from file path
            if not file_type and (file_path or source_url):
                file_type = self._infer_file_type(None, file_path or source_url)
            
            # Create document record
            document = Document(
                title=title,
                content=content,
                knowledge_base_id=knowledge_base_id,
                owner_id=owner_id,
                source_url=source_url,
                file_path=file_path,
                file_type=file_type,
                doc_metadata=metadata or {}
            )
            
            self.session.add(document)
            await self.session.flush()
            
            # Chunk document
            chunks = self.chunker.chunk_document(
                content,
                chunk_size=kb.chunk_size,
                chunk_overlap=kb.chunk_overlap,
                metadata={"document_id": str(document.id), "title": title}
            )
            
            logger.info(f"Split document into {len(chunks)} chunks")
            
            if not kb.embedding_model_id:
                raise ValueError("Knowledge base embedding model is not configured")

            embedder = await self.embedding_service.get_embedder(
                model_id=str(kb.embedding_model_id)
            )
            # Save document chunks to database
            chunk_records = []
            for i, chunk in enumerate(chunks):
                chunk_record = DocumentChunk(
                    content=chunk.content,
                    chunk_index=i,
                    token_count=chunk.token_count,
                    document_id=document.id,
                    chunk_metadata=chunk.metadata
                )
                chunk_records.append(chunk_record)
                self.session.add(chunk_record)
            
            await self.session.flush()

            vector_documents = []
            for chunk_record in chunk_records:
                vector_documents.append(VectorDocument(
                    id = str(chunk_record.id),
                    page_content = chunk_record.content,
                    metadata = {
                        'chunk_id': str(chunk_record.id),
                        'document_id': str(document.id),
                        'chunk_index': chunk_record.chunk_index,
                        'knowledge_base_id': str(knowledge_base_id),
                        'title': title,
                        **chunk_record.chunk_metadata
                    }
                ))            
            collection_name = f"kb_{knowledge_base_id}"
            await self.vector_store.add_documents(
                collection_name=collection_name,
                documents=vector_documents,
                embedding_function=embedder,
            )
            
            await self.session.commit()
            logger.info(f"Added document '{title}' to knowledge base {knowledge_base_id}")
            return document
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to add document: {e}")
            raise
    
    async def get_documents(
        self,
        knowledge_base_id: uuid.UUID,
        owner_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Document]:
        """Get document list in knowledge base"""
        # Verify knowledge base access permission
        kb = await self.get_knowledge_base(knowledge_base_id, owner_id)
        if not kb:
            raise ValueError("Knowledge base not found or access denied")
        
        result = await self.session.execute(
            select(Document)
            .where(
                and_(
                    Document.knowledge_base_id == knowledge_base_id,
                    Document.status == "ACTIVE"
                )
            )
            .offset(skip)
            .limit(limit)
            .order_by(Document.created_at.desc())
        )
        return result.scalars().all()
    
    async def get_document_chunks(
        self,
        document_id: uuid.UUID,
        owner_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[DocumentChunk]:
        """Get document chunk list"""
        try:
            # Get document info first, verify permission
            query = select(Document).where(Document.id == document_id)
            if owner_id is not None:
                query = query.where(
                    and_(
                        Document.owner_id == owner_id,
                        Document.status == "ACTIVE"
                    )
                )
            else:
                query = query.where(Document.status == "ACTIVE")
            
            document_result = await self.session.execute(query)
            document = document_result.scalar_one_or_none()
            
            if not document:
                raise ValueError("Document not found or access denied")
            
            # Query document chunks
            chunk_result = await self.session.execute(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == document_id)
                .offset(skip)
                .limit(limit)
                .order_by(DocumentChunk.chunk_index.asc())
            )
            return chunk_result.scalars().all()
            
        except Exception as e:
            logger.error(f"Failed to get document chunks: {e}")
            raise
    
    
    async def delete_document(
        self,
        document_id: uuid.UUID,
        owner_id: uuid.UUID
    ) -> bool:
        """Delete document"""
        try:
            # Get document
            result = await self.session.execute(
                select(Document)
                .options(selectinload(Document.chunks))
                .where(
                    and_(
                        Document.id == document_id,
                        Document.owner_id == owner_id,
                        Document.status == "ACTIVE"
                    )
                )
            )
            document = result.scalar_one_or_none()
            
            if not document:
                return False
            
            # Delete from vector database
            collection_name = f"kb_{document.knowledge_base_id}"
            chunk_ids = [str(chunk.id) for chunk in document.chunks]
            
            if chunk_ids:
                await self.vector_store.delete_documents(collection_name, chunk_ids)
            
            # Mark as deleted (soft delete)
            document.status = "DELETED"
            
            await self.session.commit()
            logger.info(f"Deleted document {document_id}")
            return True
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to delete document: {e}")
            raise


    async def _relevance_search_with_score(
        self,
        query: str,
        knowledge_base_id: uuid.UUID,
        k: int,
        kb_obj: KnowledgeBase,
    ) -> List[Any]: # List[Tuple[Document, float]]
        """Helper for scored search"""
        if not kb_obj.embedding_model_id:
            return []
            
        collection_name = f"kb_{knowledge_base_id}"
        embedding_model_id = str(kb_obj.embedding_model_id)
        embedder = await self.embedding_service.get_embedder(embedding_model_id)
        
        return await self.vector_store.similarity_search_with_score(
            collection_name=collection_name,
            query=query,
            k=k,
            embedding_function=embedder
        )

    # Legacy method replaced by retrieve_multi
    # async def relevance_search(...)
            
    async def retrieve_multi(
        self,
        query: str,
        knowledge_base_id: uuid.UUID,
        k: int,
        kb_obj: KnowledgeBase,
    ) -> List[Any]: # List[Tuple[Document, float]]
        """Helper for scored search"""
        if not kb_obj.embedding_model_id:
            return []
            
        collection_name = f"kb_{knowledge_base_id}"
        embedding_model_id = str(kb_obj.embedding_model_id)
        embedder = await self.embedding_service.get_embedder(embedding_model_id)
        
        return await self.vector_store.similarity_search_with_score(
            collection_name=collection_name,
            query=query,
            k=k,
            embedding_function=embedder
        )

    async def retrieve_multi(
        self,
        query: str,
        knowledge_base_ids: List[uuid.UUID],
        top_k: int = 5,
        score_threshold: Optional[float] = None,
    ) -> RetrievalResult:
        """
        Execute RAG retrieval across multiple Knowledge Bases with global Reranking.
        """
        all_chunks: List[RetrievalChunk] = []
        
        # Pre-fetch KnowledgeBase objects
        stmt = select(KnowledgeBase).where(KnowledgeBase.id.in_(knowledge_base_ids))
        result = await self.session.execute(stmt)
        kbs = result.scalars().all()
        kb_map = {kb.id: kb for kb in kbs}

        # Create tasks (using score-based search)
        tasks = []
        valid_kb_ids = [] # keep track of order
        
        for kb_id in knowledge_base_ids:
            kb = kb_map.get(kb_id)
            if kb:
                # We request top_k from EACH KB to ensure we have enough candidates
                # Since we will global sort later.
                tasks.append(self._relevance_search_with_score(query, kb_id, k=top_k, kb_obj=kb))
                valid_kb_ids.append(kb_id)
        
        if not tasks:
            return RetrievalResult(query=query, chunks=[])

        # Execute all searches
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results_list):
            kb_id = valid_kb_ids[i]
            
            if isinstance(result, Exception):
                logger.warning(f"Error retrieving from KB {kb_id}: {result}")
                continue
                
            if not result:
                continue
            
            # Result is List[Tuple[Document, float]]
            for doc, score in result:
                # Filter by score threshold if provided
                if score_threshold is not None and score < score_threshold:
                    continue

                # Convert VectorDocument to RetrievalChunk
                chunks_doc_id = None
                if doc.metadata and "doc_id" in doc.metadata:
                    try:
                        chunks_doc_id = uuid.UUID(doc.metadata["doc_id"])
                    except (ValueError, TypeError):
                        pass

                chunk = RetrievalChunk(
                    content=doc.page_content,
                    metadata=doc.metadata or {},
                    score=score,
                    kb_id=kb_id,
                    doc_id=chunks_doc_id
                )
                all_chunks.append(chunk)

        # Global Re-ranking (Sort by score descending)
        # Assuming scores are comparable (normalized relevance scores)
        all_chunks.sort(key=lambda x: x.score if x.score is not None else -1.0, reverse=True)
        
        # Limit to top_k Global
        final_chunks = all_chunks[:top_k]
        
        return RetrievalResult(
            query=query,
            chunks=final_chunks
        )

    def format_retrieval_result_for_llm(self, result: RetrievalResult) -> str:
        """
        Format the retrieval result into a context string with citations.
        Matches the style used in PromptBuilder.
        """
        context_entries = []
        entry_index = 1
        
        for chunk in result.chunks:
            metadata = chunk.metadata or {}
            # Try to get title from metadata, fallback to doc_id or "Untitled"
            title = metadata.get("title") or metadata.get("source") or "Untitled Document"
            content = chunk.content or ""
            
            context_entries.append(
                f"[Reference {entry_index}] (Document {title})\n{content}"
            )
            entry_index += 1
            
        return "\n\n".join(context_entries)