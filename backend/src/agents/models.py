"""
Agent data models - Tool execution engine for Assistants
"""
import enum
import uuid
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    String,
    Text,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
    Boolean,
    Table,
    Column
)
from sqlalchemy.ext.mutable import MutableDict, MutableList
from fastapi_users_db_sqlalchemy.generics import GUID

from src.models import Base

if TYPE_CHECKING:
    from src.assistants.models import Conversation, Assistant


class AgentExecutionStatusEnum(enum.Enum):
    """Agent execution status enumeration"""
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"


class MCPServerTypeEnum(enum.Enum):
    """MCP server type enumeration"""
    STDIO = "STDIO"  # Standard input/output
    SSE = "SSE"      # Server-sent events
    HTTP = "HTTP"    # HTTP protocol


# Assistant and MCP server many-to-many relationship table
assistant_mcp_servers = Table(
    'assistant_mcp_servers',
    Base.metadata,
    Column('assistant_id', GUID, ForeignKey('assistants.id', ondelete="CASCADE"), primary_key=True),
    Column('mcp_server_id', GUID, ForeignKey('mcp_servers.id', ondelete="CASCADE"), primary_key=True)
)


class AgentExecution(Base):
    """Agent execution record table - tracks tool usage in conversations"""
    __tablename__ = "agent_executions"

    # Conversation ID
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Input text
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Output text
    output_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Execution status
    status: Mapped[AgentExecutionStatusEnum] = mapped_column(
        SQLEnum(AgentExecutionStatusEnum),
        default=AgentExecutionStatusEnum.RUNNING,
        nullable=False
    )
    
    # Thought chain (reasoning process, JSON format)
    # Structure: [{"step": 1, "thought": "...", "action": "...", "observation": "..."}]
    thought_chain: Mapped[List[Dict[str, Any]]] = mapped_column(
        MutableList.as_mutable(JSON),
        nullable=False,
        default=list
    )
    
    # Token usage statistics
    token_usage: Mapped[Dict[str, int]] = mapped_column(
        MutableDict.as_mutable(JSON),
        nullable=False,
        default=dict
    )
    
    # Error message (if failed)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Execution metadata (use extra_data to avoid SQLAlchemy conflict)
    extra_data: Mapped[Dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON),
        nullable=False,
        default=dict
    )
    
    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation")

    def __repr__(self):
        return f"<AgentExecution(conversation_id='{self.conversation_id}', status='{self.status}')>"


class MCPServerConfig(Base):
    """MCP server configuration table"""
    __tablename__ = "mcp_servers"

    # Server name (unique)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    
    # Server description
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Server type
    server_type: Mapped[MCPServerTypeEnum] = mapped_column(
        SQLEnum(MCPServerTypeEnum),
        default=MCPServerTypeEnum.STDIO,
        nullable=False
    )
    
    # Connection configuration (JSON format)
    # For STDIO: {"command": "npx", "args": [...], "env": {...}}
    # For SSE/HTTP: {"url": "...", "headers": {...}}
    connection_config: Mapped[Dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON),
        nullable=False
    )
    
    # Whether this server is active
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Server metadata (use extra_data to avoid SQLAlchemy conflict)
    extra_data: Mapped[Dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON),
        nullable=False,
        default=dict
    )
    
    # Relationships
    assistants: Mapped[List["Assistant"]] = relationship(
        "Assistant",
        secondary=assistant_mcp_servers,
        back_populates="mcp_servers"
    )

    def __repr__(self):
        return f"<MCPServerConfig(name='{self.name}', type='{self.server_type}')>"
