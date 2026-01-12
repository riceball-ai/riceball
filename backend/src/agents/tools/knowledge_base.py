"""
Knowledge base query tool
"""
from typing import Any, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from .base import AgentTool, AgentToolConfig
from .registry import tool_registry


@tool_registry.register
class KnowledgeBaseTool(AgentTool):
    """Tool for querying knowledge base"""
    
    def __init__(self, config: Optional[AgentToolConfig] = None, session: Optional[AsyncSession] = None):
        super().__init__(config)
        self.session = session
        self.knowledge_base_ids = config.parameters.get("knowledge_base_ids", []) if config else []
    
    @property
    def name(self) -> str:
        return "knowledge_base_query"
    
    @property
    def description(self) -> str:
        return "Query information from knowledge base. Useful for retrieving relevant documents and context."
    
    async def execute(self, query: str, top_k: int = 5) -> Any:
        """Execute knowledge base query"""
        try:
            if not self.session:
                return "Error: Database session not available"
            
            if not self.knowledge_base_ids:
                return "Error: No knowledge base configured"
            
            # Import here to avoid circular dependency
            from src.rag.service import RAGService
            
            rag_service = RAGService(self.session)
            
            # Query each knowledge base with Unified Retrieval Service
            try:
                kb_uuids = [uuid.UUID(kb_id_str) for kb_id_str in self.knowledge_base_ids]
            except (ValueError, TypeError):
                return "Error: Invalid knowledge base ID format"

            try:
                 # Use retrieve_multi which includes Reranking and Global Sorting
                retrieval_result = await rag_service.retrieve_multi(
                    query=query,
                    knowledge_base_ids=kb_uuids,
                    top_k=top_k
                )
            except Exception as e:
                return f"Error retrieving information: {str(e)}"
            
            if not retrieval_result.chunks:
                return "No relevant information found in knowledge base."
            
            # Format results
            formatted_results = []
            for i, chunk in enumerate(retrieval_result.chunks, 1):
                # Use retrieval chunk structure directly
                title = chunk.metadata.get("title") or chunk.metadata.get("source") or "Untitled Document"
                content = chunk.content
                formatted_results.append(f"[Result {i} (Source: {title})]\n{content}\n")
            
            return "\n".join(formatted_results)
            
        except Exception as e:
            return f"Error querying knowledge base: {str(e)}"
