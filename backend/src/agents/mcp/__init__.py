"""
MCP (Model Context Protocol) integration module
"""
from .client import MCPClient
from .registry import mcp_registry, MCPServerRegistry
from .tools_adapter import MCPToolAdapter

__all__ = ["MCPClient", "mcp_registry", "MCPServerRegistry", "MCPToolAdapter"]
