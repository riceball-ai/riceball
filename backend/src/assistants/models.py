import enum
import uuid
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    String,
    Text,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
    Integer,
    Boolean,
    DateTime,
    Numeric,
    UniqueConstraint
)
from sqlalchemy.ext.mutable import MutableDict, MutableList

from src.models import Base

if TYPE_CHECKING:
    from src.ai_models.models import Model
    from src.users.models import User
    from src.agents.models import MCPServerConfig
    

class AssistantStatusEnum(enum.Enum):
    """Assistant status enumeration"""
    ACTIVE = "ACTIVE"  # Active and available
    INACTIVE = "INACTIVE"  # Disabled
    DRAFT = "DRAFT"  # Draft state


class ConversationStatusEnum(enum.Enum):
    """Conversation status enumeration"""
    ACTIVE = "ACTIVE"  # Active conversation
    ARCHIVED = "ARCHIVED"  # Archived conversation
    DELETED = "DELETED"  # Deleted conversation


class MessageTypeEnum(enum.Enum):
    """Message type enumeration"""
    USER = "USER"  # User message
    ASSISTANT = "ASSISTANT"  # Assistant response
    SYSTEM = "SYSTEM"  # System message


class ConversationShareScopeEnum(enum.Enum):
    """Scope of conversation sharing"""
    CONVERSATION = "CONVERSATION"
    MESSAGE = "MESSAGE"


class ConversationShareStatusEnum(enum.Enum):
    """Status of a conversation share link"""
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


class Assistant(Base):
    """Assistant table - represents AI assistants"""
    __tablename__ = "assistants"

    # Assistant name
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # Assistant description
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # System prompt/instructions for the assistant
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Assistant avatar file ID (foreign key to file_records)
    avatar_file_path: Mapped[Optional[str]] = mapped_column(
        String(1000)
    )
    
    # Assistant status
    status: Mapped[AssistantStatusEnum] = mapped_column(
        SQLEnum(AssistantStatusEnum), 
        default=AssistantStatusEnum.DRAFT, 
        nullable=False
    )
    
    # Model ID (foreign key to ai_models.models)
    model_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("models.id", ondelete="CASCADE"),
        nullable=False
    )

    # Owner user ID (foreign key to users table)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Model configuration (temperature, max_tokens, etc.)
    config: Mapped[Dict[str, Any]] = mapped_column(MutableDict.as_mutable(JSON), nullable=False, default=dict)

    # Model Parameters - Native parameters passed directly to LLM API (e.g. tools, top_p)
    model_parameters: Mapped[Dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON), 
        nullable=False, 
        default=dict,
        server_default="{}"
    )

    # Temperature setting for the assistant (0.0 to 2.0, default 1.0)
    temperature: Mapped[float] = mapped_column(
        default=1.0,
        server_default="1.0",
        nullable=False,
        comment="Temperature for text generation (0.0-2.0)"
    )

    # Maximum tokens for response generation
    max_tokens: Mapped[int] = mapped_column(
        Integer,
        default=2048,
        server_default="2048",
        nullable=False,
        comment="Maximum number of tokens to generate"
    )

    # Maximum number of history messages to include in context (None for no limit)
    max_history_messages: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Maximum number of history messages to include in context"
    )

    # Whether this assistant is public (visible to other users)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Usage count - number of times this assistant has been used (conversation created)
    usage_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
        comment="Number of times this assistant has been used"
    )

    # Agent configuration - Enable tool calling capabilities
    enable_agent: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        comment="Whether to enable agent (tool calling) capabilities"
    )
    
    # Agent maximum iterations
    agent_max_iterations: Mapped[int] = mapped_column(
        Integer,
        default=5,
        server_default="5",
        nullable=False,
        comment="Maximum iterations for agent reasoning"
    )
    
    # Agent enabled tools (JSON list of tool names)
    agent_enabled_tools: Mapped[List[str]] = mapped_column(
        MutableList.as_mutable(JSON),
        nullable=False,
        default=list,
        server_default="[]",
        comment="List of enabled tool names for agent"
    )
    
    # Agent tool configuration (JSON)
    agent_tool_config: Mapped[Dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON),
        nullable=False,
        default=dict,
        server_default="{}",
        comment="Tool configuration parameters for agent"
    )

    # RAG configuration (retrieval count, similarity threshold, etc.)
    rag_config: Mapped[Dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=False, default=dict
    )

    # Associated knowledge base IDs
    knowledge_base_ids: Mapped[List[uuid.UUID]] = mapped_column(
        MutableList.as_mutable(JSON), nullable=False, default=list
    )
    
    # Translations for multi-language support
    # Format: {"locale": {"field_name": "translated_value"}}
    translations: Mapped[Optional[Dict[str, Dict[str, str]]]] = mapped_column(
        MutableDict.as_mutable(JSON),
        nullable=True,
        default=dict,
        comment="Multi-language translations for name, description, and system_prompt"
    )
    
    # Assistant category (e.g., "coding", "writing", "general")
    category: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Primary category of the assistant"
    )

    # Assistant tags (JSON list of strings)
    tags: Mapped[List[str]] = mapped_column(
        MutableList.as_mutable(JSON),
        nullable=False,
        default=list,
        server_default="[]",
        comment="List of tags for filtering"
    )

    # Associated model
    model: Mapped["Model"] = relationship(
        "Model"
    )

    # Associated owner - relationship defined in User model
    owner: Mapped["User"] = relationship(
        "User"
    )
    
    # Associated conversations
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation",
        back_populates="assistant",
        cascade="all, delete-orphan"
    )
    
    # Associated MCP servers
    mcp_servers: Mapped[List["MCPServerConfig"]] = relationship(
        "MCPServerConfig",
        secondary="assistant_mcp_servers",
        back_populates="assistants"
    )

    @property
    def mcp_server_ids(self) -> List[uuid.UUID]:
        """Safely get MCP server IDs without triggering lazy load"""
        from sqlalchemy import inspect
        from sqlalchemy.orm.base import NO_VALUE
        try:
            insp = inspect(self)
            if 'mcp_servers' in insp.mapper.relationships:
                mcp_servers_state = insp.attrs.mcp_servers
                loaded_value = mcp_servers_state.loaded_value
                if loaded_value is not NO_VALUE and loaded_value is not None:
                    return [mcp.id for mcp in loaded_value]
        except Exception:
            pass
        return []

    def __repr__(self):
        return f"<Assistant(name='{self.name}', owner_id='{self.owner_id}')>"


class Conversation(Base):
    """Conversation table - represents chat conversations"""
    __tablename__ = "conversations"

    # Conversation title
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Conversation status
    status: Mapped[ConversationStatusEnum] = mapped_column(
        SQLEnum(ConversationStatusEnum), 
        default=ConversationStatusEnum.ACTIVE, 
        nullable=False
    )
    
    # Assistant ID (foreign key)
    assistant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assistants.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # User ID (foreign key)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Last message time
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Message count in this conversation
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Conversation metadata (custom data)
    extra_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    
    # Associated assistant
    assistant: Mapped["Assistant"] = relationship(
        "Assistant",
        back_populates="conversations"
    )
    
    # Associated user
    user: Mapped["User"] = relationship(
        "User"
    )
    
    # Associated messages
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at"
    )

    # Associated share links
    shares: Mapped[List["ConversationShare"]] = relationship(
        "ConversationShare",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Conversation(title='{self.title}', user_id='{self.user_id}')>"


class Message(Base):
    """Message table - represents individual messages in conversations"""
    __tablename__ = "messages"

    # Message content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Message type
    message_type: Mapped[MessageTypeEnum] = mapped_column(
        SQLEnum(MessageTypeEnum), 
        nullable=False
    )
    
    # Conversation ID (foreign key)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # User ID (foreign key) - for user messages
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True
    )
    
    # Message metadata (custom data, model response info, etc.)
    extra_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    
    # User feedback for the message (like/dislike)
    feedback: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Associated conversation
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages"
    )
    
    # Associated user (for user messages)
    user: Mapped[Optional["User"]] = relationship(
        "User"
    )

    def __repr__(self):
        return f"<Message(type='{self.message_type}', conversation_id='{self.conversation_id}')>"


class ConversationShare(Base):
    """Conversation share table - stores shareable links for conversations or messages"""
    __tablename__ = "conversation_shares"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False
    )

    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    scope: Mapped[ConversationShareScopeEnum] = mapped_column(
        SQLEnum(ConversationShareScopeEnum),
        nullable=False
    )

    start_message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=True
    )

    end_message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=True
    )

    status: Mapped[ConversationShareStatusEnum] = mapped_column(
        SQLEnum(ConversationShareStatusEnum),
        default=ConversationShareStatusEnum.ACTIVE,
        nullable=False
    )

    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    extra_data: Mapped[Dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON),
        nullable=False,
        default=dict
    )

    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="shares"
    )

    creator: Mapped["User"] = relationship(
        "User"
    )

    start_message: Mapped[Optional["Message"]] = relationship(
        "Message",
        foreign_keys=[start_message_id]
    )

    end_message: Mapped[Optional["Message"]] = relationship(
        "Message",
        foreign_keys=[end_message_id]
    )

    def __repr__(self):
        return f"<ConversationShare(conversation_id='{self.conversation_id}', scope='{self.scope.value}')>"


class PinnedAssistant(Base):
    """Pinned assistants for users"""
    __tablename__ = "pinned_assistants"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    assistant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assistants.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", backref="pinned_assistants")
    assistant: Mapped["Assistant"] = relationship("Assistant")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'assistant_id', name='uq_user_assistant_pin'),
    )
