import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator

from src.assistants.models import (
    AssistantStatusEnum,
    ConversationStatusEnum,
    ConversationShareScopeEnum,
    ConversationShareStatusEnum,
    MessageTypeEnum
)
from src.ai_models.api.v1.schemas import ModelBase


class GenerateTitleResponse(BaseModel):
    """Generate Title Response"""
    conversation_id: uuid.UUID = Field(..., description="Conversation ID")
    title: str = Field(..., description="Generated title")
    model_used: str = Field(..., description="Model used")
    updated: bool = Field(..., description="Whether updated in database")


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
    config: Dict[str, Any] = Field(default_factory=dict, description="Model configuration")
    is_public: bool = Field(default=False, description="Whether assistant is public")
    rag_config: RAGConfig = Field(default_factory=RAGConfig, description="RAG configuration")


class AssistantCreate(AssistantBase):
    """Schema for creating an assistant"""
    model_id: uuid.UUID = Field(..., description="Model ID to use")
    status: AssistantStatusEnum = Field(default=AssistantStatusEnum.DRAFT, description="Assistant status")
    knowledge_base_ids: Optional[List[uuid.UUID]] = Field(
        default_factory=list,
        description="Knowledge base IDs to associate"
    )


class AssistantUpdate(BaseModel):
    """Schema for updating an assistant"""
    name: Optional[str] = Field(None, max_length=200, description="Assistant name")
    description: Optional[str] = Field(None, description="Assistant description")
    system_prompt: Optional[str] = Field(None, description="System prompt for the assistant")
    avatar_file_path: Optional[str] = Field(None, max_length=500, description="Avatar URL")
    model_id: Optional[uuid.UUID] = Field(None, description="Model ID to use")
    config: Optional[Dict[str, Any]] = Field(None, description="Model configuration")
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

    # Related objects
    model: Optional[ModelBase] = None

    # Computed field for avatar URL
    avatar_url: Optional[str] = Field(None, description="Full avatar URL")

    model_config = ConfigDict(from_attributes=True)


# Conversation schemas
class ConversationBase(BaseModel):
    """Base conversation schema"""
    title: str = Field(..., max_length=500, description="Conversation title")


class ConversationCreate(ConversationBase):
    """Schema for creating a conversation"""
    assistant_id: uuid.UUID = Field(..., description="Assistant ID")

class ConversationUpdate(BaseModel):
    """Schema for updating a conversation"""
    title: Optional[str] = Field(None, max_length=500, description="Conversation title")
    status: Optional[ConversationStatusEnum] = Field(None, description="Conversation status")


class ConversationResponse(ConversationBase):
    """Schema for conversation response"""
    id: uuid.UUID
    assistant_id: uuid.UUID
    user_id: uuid.UUID
    status: ConversationStatusEnum
    last_message_at: Optional[datetime]
    message_count: int
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    extra_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    
    # Related objects
    assistant_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("extra_data", mode="before")
    @classmethod
    def _default_extra_data(cls, value: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        return value or {}


# Message schemas
class MessageBase(BaseModel):
    """Base message schema"""
    content: str = Field(..., description="Message content")


class MessageCreate(MessageBase):
    """Schema for creating a message"""
    message_type: MessageTypeEnum = Field(..., description="Message type")
    conversation_id: uuid.UUID = Field(..., description="Conversation ID")
    extra_data: Dict[str, Any] = Field(default_factory=dict, description="Message metadata")


class MessageResponse(MessageBase):
    """Schema for message response"""
    id: uuid.UUID
    message_type: MessageTypeEnum
    conversation_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    token_count: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    extra_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("extra_data", mode="before")
    @classmethod
    def _default_extra_data(cls, value: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        return value or {}


# Conversation share schemas
class ConversationShareCreateRequest(BaseModel):
    """Request body for creating a conversation share link"""
    conversation_id: uuid.UUID = Field(..., description="Conversation ID" )
    scope: ConversationShareScopeEnum = Field(..., description="Share scope")
    start_message_id: Optional[uuid.UUID] = Field(
        None,
        description="Start message ID when sharing a specific Q/A pair"
    )
    end_message_id: Optional[uuid.UUID] = Field(
        None,
        description="End message ID when sharing a specific Q/A pair"
    )


class ConversationShareResponse(BaseModel):
    """Response for share creation"""
    id: uuid.UUID
    conversation_id: uuid.UUID
    scope: ConversationShareScopeEnum
    status: ConversationShareStatusEnum
    start_message_id: Optional[uuid.UUID]
    end_message_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SharedMessage(BaseModel):
    """Simplified message for public share response"""
    id: uuid.UUID
    message_type: MessageTypeEnum
    content: str
    extra_data: Dict[str, Any] = Field(default_factory=dict, description="Message metadata")
    created_at: datetime


class AssistantShareInfo(BaseModel):
    """Assistant metadata exposed via public share"""
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    avatar_file_path: Optional[str] = Field(None, description="Assistant avatar storage path")
    avatar_url: Optional[str] = Field(None, description="Public URL for avatar image")
    translations: Dict[str, Dict[str, str]] = Field(default_factory=dict, description="Localized fields")


class ConversationSharePublicResponse(BaseModel):
    """Public share payload that is accessible without auth"""
    id: uuid.UUID
    conversation_id: uuid.UUID
    scope: ConversationShareScopeEnum
    assistant_id: Optional[uuid.UUID] = None
    assistant_name: str
    assistant_description: Optional[str] = None
    assistant: Optional[AssistantShareInfo] = None
    conversation_title: str
    messages: List[SharedMessage]
    created_at: datetime

# Chat schemas for API
class ImageAttachment(BaseModel):
    """Image attachment for chat message"""
    data_url: Optional[str] = Field(None, description="Base64 encoded image data URL (data:image/...;base64,...)")
    url: Optional[str] = Field(None, description="Server URL for uploaded image")
    alt: Optional[str] = Field(None, description="Alternative text for image")
    mime_type: Optional[str] = Field(None, alias="mimeType", description="MIME type for the attachment")
    size: Optional[int] = Field(None, description="File size in bytes")
    file_key: Optional[str] = Field(
        None,
        alias="fileKey",
        description="Internal storage key (S3 object path)",
    )

    model_config = ConfigDict(populate_by_name=True)

class ChatRequest(BaseModel):
    """Chat message request"""
    content: str = Field(..., description="Message content")
    conversation_id: uuid.UUID = Field(..., description="Conversation ID")
    images: Optional[List[ImageAttachment]] = Field(None, description="Image attachments (for vision models)")
    language: Optional[str] = Field(None, description="Language code for localization (e.g. zh-CN)")

class ChatMessageResponse(BaseModel):
    """Chat message response"""
    conversation_id: uuid.UUID
    user_message: MessageResponse
    assistant_message: MessageResponse

# Streaming chat schemas
class StreamEventType(str, Enum):
    """Stream event types"""
    ASSISTANT_MESSAGE_START = "assistant_message_start"
    CONTENT_CHUNK = "content_chunk"
    ASSISTANT_MESSAGE_COMPLETE = "assistant_message_complete"
    ERROR = "error"

class StreamAssistantMessageStartData(BaseModel):
    """Stream assistant message start data"""
    id: str
    conversation_id: str
    message_type: str
    model: str
    created_at: str

class StreamMediaItem(BaseModel):
    """Media payload emitted during streaming."""
    id: Optional[str] = None
    type: str = Field(default="image")
    mime_type: str
    data_url: Optional[str] = None
    url: Optional[str] = None
    alt: Optional[str] = None
    index: Optional[int] = None
    source: Optional[str] = None

class StreamContentChunkData(BaseModel):
    """Stream content chunk data"""
    content: str
    is_final: bool
    media: Optional[List[StreamMediaItem]] = None

class StreamAssistantMessageCompleteData(BaseModel):
    """Stream assistant message complete data"""
    id: str
    content: str
    conversation_id: str
    message_type: str
    model: str
    created_at: str
    updated_at: str
    user_message_id: str
    media: Optional[List[StreamMediaItem]] = None

class StreamErrorData(BaseModel):
    """Stream error data"""
    error: str
    conversation_id: str

class StreamEvent(BaseModel):
    """Stream event wrapper"""
    type: StreamEventType
    data: Dict[str, Any]


# List responses
class AssistantListResponse(BaseModel):
    """Assistant list response with pagination"""
    items: List[AssistantResponse]
    total: int
    page: int
    size: int
    pages: int


class ConversationListResponse(BaseModel):
    """Conversation list response with pagination"""
    items: List[ConversationResponse]
    total: int
    page: int
    size: int
    pages: int


class MessageListResponse(BaseModel):
    """Message list response with pagination"""
    items: List[MessageResponse]
    total: int
    page: int
    size: int
    pages: int


# Dashboard schemas
class DashboardOverview(BaseModel):
    """Dashboard overview metrics"""
    total_users: int
    total_token_usage: int
    total_conversations: int


class ChartDataPoint(BaseModel):
    """Generic chart data point"""
    name: str
    value: float
    extra: Optional[Dict[str, Any]] = None


class DashboardStatsResponse(BaseModel):
    """Dashboard statistics response"""
    overview: DashboardOverview
    user_growth: List[ChartDataPoint]
    top_assistants: List[Dict[str, Any]]
    recent_users: List[Dict[str, Any]]
