import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, computed_field

from src.files.storage import storage_service
from src.assistants.models import AssistantStatusEnum
from src.ai_models.api.v1.schemas import ModelBase


# RAG configuration schema
class RAGConfig(BaseModel):
    """Retrieval configuration for assistants"""
    retrieval_count: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Number of chunks to retrieve"
    )
    similarity_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Similarity threshold for retrieval"
    )


# Assistant schemas
class AssistantBase(BaseModel):
    """Base assistant schema"""
    name: str = Field(..., max_length=200, description="Assistant name")
    description: Optional[str] = Field(None, description="Assistant description")
    system_prompt: Optional[str] = Field(None, description="System prompt for the assistant")
    avatar_file_path: Optional[str] = Field(None, max_length=500, description="Avatar URL")
    config: Dict[str, Any] = Field(default_factory=dict, description="App-specific configuration")
    model_parameters: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Native parameters passed directly to Model API (e.g. tools, top_p)"
    )
    temperature: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="Temperature for text generation (0.0-2.0)"
    )
    max_tokens: Optional[int] = Field(
        default=2048,
        ge=1,
        description="Maximum number of tokens to generate"
    )
    max_history_messages: Optional[int] = Field(
        default=None,
        ge=0,
        description="Maximum number of history messages to include in context (None for no limit)"
    )
    category: Optional[str] = Field(None, max_length=50, description="Assistant category")
    tags: List[str] = Field(default_factory=list, description="Assistant tags")
    is_public: bool = Field(default=False, description="Whether assistant is public")
    rag_config: RAGConfig = Field(default_factory=RAGConfig, description="RAG configuration")
    
    # Agent configuration
    enable_agent: bool = Field(
        default=False,
        description="Whether to enable agent (tool calling) capabilities"
    )
    agent_max_iterations: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum iterations for agent reasoning"
    )
    agent_enabled_tools: List[str] = Field(
        default_factory=list,
        description="List of enabled tool names for agent"
    )
    agent_tool_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Tool configuration parameters for agent"
    )


class AssistantCreate(AssistantBase):
    """Schema for creating an assistant"""
    model_id: uuid.UUID = Field(..., description="Model ID to use")
    status: AssistantStatusEnum = Field(default=AssistantStatusEnum.DRAFT, description="Assistant status")
    knowledge_base_ids: Optional[List[uuid.UUID]] = Field(
        default_factory=list,
        description="Knowledge base IDs to associate"
    )
    mcp_server_ids: Optional[List[uuid.UUID]] = Field(
        default_factory=list,
        description="MCP server IDs to attach for agent tools"
    )


class AssistantUpdate(BaseModel):
    """Schema for updating an assistant"""
    name: Optional[str] = Field(None, max_length=200, description="Assistant name")
    description: Optional[str] = Field(None, description="Assistant description")
    system_prompt: Optional[str] = Field(None, description="System prompt for the assistant")
    avatar_file_path: Optional[str] = Field(None, max_length=500, description="Avatar URL")
    model_id: Optional[uuid.UUID] = Field(None, description="Model ID to use")
    config: Optional[Dict[str, Any]] = Field(None, description="Model configuration")
    model_parameters: Optional[Dict[str, Any]] = Field(
        None, 
        description="Native parameters passed directly to Model API (e.g. tools, top_p)"
    )
    temperature: Optional[float] = Field(
        None,
        ge=0.0,
        le=2.0,
        description="Temperature for text generation (0.0-2.0)"
    )
    max_tokens: Optional[int] = Field(
        None,
        ge=1,
        description="Maximum number of tokens to generate"
    )
    max_history_messages: Optional[int] = Field(
        None,
        ge=0,
        description="Maximum number of history messages to include in context (None for no limit)"
    )
    category: Optional[str] = Field(None, max_length=50, description="Assistant category")
    tags: Optional[List[str]] = Field(None, description="Assistant tags")
    status: Optional[AssistantStatusEnum] = Field(None, description="Assistant status")
    is_public: Optional[bool] = Field(None, description="Whether assistant is public")
    rag_config: Optional[RAGConfig] = Field(
        None,
        description="RAG configuration"
    )
    knowledge_base_ids: Optional[List[uuid.UUID]] = Field(
        None,
        description="Knowledge base IDs to associate"
    )
    mcp_server_ids: Optional[List[uuid.UUID]] = Field(
        None,
        description="MCP server IDs to attach for agent tools"
    )
    
    # Agent configuration
    enable_agent: Optional[bool] = Field(
        None,
        description="Whether to enable agent (tool calling) capabilities"
    )
    agent_max_iterations: Optional[int] = Field(
        None,
        ge=1,
        le=20,
        description="Maximum iterations for agent reasoning"
    )
    agent_enabled_tools: Optional[List[str]] = Field(
        None,
        description="List of enabled tool names for agent"
    )
    agent_tool_config: Optional[Dict[str, Any]] = Field(
        None,
        description="Tool configuration parameters for agent"
    )


class AssistantResponse(AssistantBase):
    """Schema for assistant response"""
    id: uuid.UUID
    model_id: uuid.UUID
    owner_id: uuid.UUID
    status: AssistantStatusEnum
    created_at: datetime
    updated_at: datetime
    knowledge_base_ids: List[uuid.UUID] = Field(
        default_factory=list,
        description="Associated knowledge base IDs"
    )
    mcp_server_ids: List[uuid.UUID] = Field(
        default_factory=list,
        description="Attached MCP server IDs for agent tools"
    )
    
    # Multi-language translations
    translations: Optional[Dict[str, Dict[str, str]]] = Field(
        None,
        description="Multi-language translations {locale: {field: value}}"
    )
    
    # User specific fields
    is_pinned: bool = Field(
        default=False,
        description="Whether the current user has pinned this assistant"
    )

    # Related objects
    model: Optional[ModelBase] = None

    @computed_field
    def avatar_url(self) -> Optional[str]:
        """Full avatar URL"""
        if not self.avatar_file_path:
            return None
            
        return storage_service.get_public_url_sync(self.avatar_file_path)

    model_config = ConfigDict(from_attributes=True)


# Translation management schemas
class TranslationData(BaseModel):
    """Translation data for a specific locale"""
    name: Optional[str] = Field(None, description="Translated name")
    description: Optional[str] = Field(None, description="Translated description")
    system_prompt: Optional[str] = Field(None, description="Translated system prompt")


class AssistantTranslationsResponse(BaseModel):
    """Schema for assistant translations (translation management page)"""
    id: uuid.UUID
    default_name: str = Field(..., description="Default name")
    default_description: Optional[str] = Field(None, description="Default description")
    default_system_prompt: Optional[str] = Field(None, description="Default system prompt")
    translations: Dict[str, Dict[str, str]] = Field(
        default_factory=dict,
        description="All translations {locale: {field: value}}"
    )
    available_locales: List[str] = Field(
        default_factory=lambda: ["zh-Hans", "zh-Hant", "ja", "ko", "es", "fr", "de"],
        description="Available locales for translation"
    )
    translation_progress: Dict[str, int] = Field(
        default_factory=dict,
        description="Translation completion percentage for each locale"
    )


class UpdateTranslationRequest(BaseModel):
    """Request to update translation for a specific locale"""
    name: Optional[str] = Field(None, description="Translated name")
    description: Optional[str] = Field(None, description="Translated description")
    system_prompt: Optional[str] = Field(None, description="Translated system prompt")


# List responses
class AssistantListResponse(BaseModel):
    """Assistant list response with pagination"""
    items: List[AssistantResponse]
    total: int
    page: int
    size: int
    pages: int