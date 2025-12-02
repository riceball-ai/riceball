"""
Agent Pydantic schemas for API
"""
import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from .models import MCPServerTypeEnum


# Tool Registry Schemas
class LocalToolInfo(BaseModel):
    """Local tool information"""
    name: str
    description: str


class AvailableToolsResponse(BaseModel):
    """Available tools response"""
    local_tools: List[LocalToolInfo]
    mcp_servers: List[str]


# MCP Server Schemas
class MCPServerConfigBase(BaseModel):
    """Base MCP server config schema"""
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    server_type: MCPServerTypeEnum = MCPServerTypeEnum.STDIO
    connection_config: Dict[str, Any]
    is_active: bool = True
    extra_data: Dict[str, Any] = Field(default_factory=dict)


class MCPServerConfigCreate(MCPServerConfigBase):
    """Create MCP server config"""
    pass


class MCPServerConfigUpdate(BaseModel):
    """Update MCP server config"""
    description: Optional[str] = Field(None, max_length=500)
    connection_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    extra_data: Optional[Dict[str, Any]] = None


class MCPServerConfigResponse(MCPServerConfigBase):
    """MCP server config response"""
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MCPToolInfo(BaseModel):
    """MCP tool information"""
    name: str
    description: str
    input_schema: Dict[str, Any] = Field(default_factory=dict, alias="inputSchema")

    class Config:
        populate_by_name = True


class MCPServerToolsResponse(BaseModel):
    """MCP server tools response"""
    server_name: str
    tools: List[MCPToolInfo]


