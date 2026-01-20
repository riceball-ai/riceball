"""
Knowledge base write tools (List and Add)
"""
from typing import Any, Optional, List, Dict
import uuid
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .base import AgentTool, AgentToolConfig
from .registry import tool_registry

@tool_registry.register
class KnowledgeBaseListTool(AgentTool):
    """Tool for listing available knowledge bases"""
    
    def __init__(self, config: Optional[AgentToolConfig] = None, session: Optional[AsyncSession] = None, owner_id: Optional[uuid.UUID] = None, is_superuser: bool = False):
        super().__init__(config)
        self.session = session
        self.owner_id = owner_id
        self.is_superuser = is_superuser
    
    @property
    def name(self) -> str:
        return "knowledge_base_list"
    
    @property
    def description(self) -> str:
        return "List all available Knowledge Bases. Returns ID, name, and description for each."
    
    async def execute(self, **kwargs) -> Any:
        """Execute knowledge base list"""
        try:
            if not self.session:
                return "Error: Database session not available"
            
            if not self.owner_id:
                return "Error: User context not available"
            
            # Import here to avoid circular dependency
            from src.rag.service import RAGService
            
            rag_service = RAGService(self.session)
            
            # Get KBs
            kbs = await rag_service.get_knowledge_bases(self.owner_id, limit=100)
            
            if not kbs:
                return "No Knowledge Bases found."
            
            results = []
            for kb in kbs:
                results.append(f"ID: {kb.id} | Name: {kb.name} | Description: {kb.description or 'No description'}")
            
            return "\n".join(results)
            
        except Exception as e:
            return f"Error listing knowledge bases: {str(e)}"


@tool_registry.register
class KnowledgeBaseAddTool(AgentTool):
    """Tool for adding content to a knowledge base"""
    
    def __init__(self, config: Optional[AgentToolConfig] = None, session: Optional[AsyncSession] = None, owner_id: Optional[uuid.UUID] = None, is_superuser: bool = False):
        super().__init__(config)
        self.session = session
        self.owner_id = owner_id
        self.is_superuser = is_superuser
    
    @property
    def name(self) -> str:
        return "knowledge_base_add_document"
    
    @property
    def description(self) -> str:
        return "Add a new document/memory to a specific Knowledge Base. Requires knowledge_base_id and content (text). Title is optional."
    
    async def execute(self, knowledge_base_id: str, content: str, title: str = "Agent Memory") -> Any:
        """
        Add document to knowledge base.
        
        Args:
            knowledge_base_id (str): UUID of the target knowledge base
            content (str): The text content to save
            title (str, optional): Title for the document. Defaults to "Agent Memory".
        """
        try:
            if not self.session:
                return "Error: Database session not available"
            
            if not self.owner_id:
                return "Error: User context not available"
            
            try:
                kb_uuid = uuid.UUID(knowledge_base_id)
            except ValueError:
                return "Error: Invalid knowledge_base_id format (must be UUID)"

            # Import here to avoid circular dependency
            from src.rag.service import RAGService
            
            rag_service = RAGService(self.session)
            
            # Add document
            # Check permissions first
            kb = await rag_service.get_knowledge_base(kb_uuid, None if self.is_superuser else self.owner_id)
            if not kb:
                return "Error: Knowledge base not found or access denied"

            # Use the actual owner of the KB if bypassing checks, otherwise current user
            target_owner_id = kb.owner_id if self.is_superuser else self.owner_id

            document = await rag_service.add_document(
                title=title,
                content=content,
                knowledge_base_id=kb_uuid,
                owner_id=target_owner_id,
                metadata={"source": "agent_tool", "created_by": "assistant"}
            )
            
            return f"Successfully added document '{document.title}' (ID: {document.id}) to Knowledge Base {knowledge_base_id}"
            
        except ValueError as ve:
            return f"Error: {str(ve)}" # Likely "Knowledge base not found or access denied" or "Embedding model not configured"
        except Exception as e:
            return f"Error adding document: {str(e)}"
