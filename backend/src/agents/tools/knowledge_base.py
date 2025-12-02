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
            
            # Query each knowledge base
            all_results = []
            for kb_id_str in self.knowledge_base_ids:
                try:
                    kb_id = uuid.UUID(kb_id_str)
                    results = await rag_service.relevance_search(
                        query=query,
                        knowledge_base_id=kb_id,
                        k=top_k
                    )
                    all_results.extend(results)
                except Exception:
                    continue
            
            if not all_results:
                return "No relevant information found in knowledge base."
            
            # Format results
            formatted_results = []
            for i, doc in enumerate(all_results[:top_k], 1):
                content = doc.page_content if hasattr(doc, 'page_content') else str(doc)
                formatted_results.append(f"[Result {i}]\n{content}\n")
            
            return "\n".join(formatted_results)
            
        except Exception as e:
            return f"Error querying knowledge base: {str(e)}"
