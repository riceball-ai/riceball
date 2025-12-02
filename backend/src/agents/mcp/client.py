"""
MCP Client implementation
"""
import logging
from typing import List, Dict, Any, Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP client wrapper"""
    
    def __init__(self, server_params: StdioServerParameters):
        self.server_params = server_params
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self._connected = False
    
    async def connect(self):
        """Connect to MCP server"""
        try:
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(self.server_params)
            )
            self.stdio, self.write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.stdio, self.write)
            )
            
            await self.session.initialize()
            self._connected = True
            logger.info(f"Connected to MCP server: {self.server_params.command}")
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            raise
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self._connected and self.session is not None
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """Get available tools list"""
        if not self.is_connected:
            raise RuntimeError("MCP session not initialized")
        
        try:
            response = await self.session.list_tools()
            return [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema
                }
                for tool in response.tools
            ]
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            raise
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool"""
        if not self.is_connected:
            raise RuntimeError("MCP session not initialized")
        
        try:
            result = await self.session.call_tool(tool_name, arguments)
            return result
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name}: {e}")
            raise
    
    async def list_resources(self) -> List[Dict[str, Any]]:
        """Get available resources list"""
        if not self.is_connected:
            raise RuntimeError("MCP session not initialized")
        
        try:
            response = await self.session.list_resources()
            return [
                {
                    "uri": resource.uri,
                    "name": resource.name,
                    "description": resource.description,
                    "mimeType": resource.mimeType
                }
                for resource in response.resources
            ]
        except Exception as e:
            logger.error(f"Failed to list resources: {e}")
            raise
    
    async def read_resource(self, uri: str) -> Any:
        """Read a resource"""
        if not self.is_connected:
            raise RuntimeError("MCP session not initialized")
        
        try:
            result = await self.session.read_resource(uri)
            return result
        except Exception as e:
            logger.error(f"Failed to read resource {uri}: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from server"""
        try:
            await self.exit_stack.aclose()
            self._connected = False
            logger.info("Disconnected from MCP server")
        except Exception as e:
            logger.error(f"Error disconnecting from MCP server: {e}")
