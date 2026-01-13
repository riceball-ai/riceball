"""
MCP Client Abstraction
Supports multiple transport layers (Stdio, SSE)
"""
import abc
import logging
from typing import Any, Dict, List, Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

logger = logging.getLogger(__name__)

class MCPClientBase(abc.ABC):
    """Abstract base class for MCP clients"""
    
    def __init__(self, name: str):
        self.name = name
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self.session is not None

    @abc.abstractmethod
    async def connect(self):
        """Establish connection to the MCP server"""
        pass

    async def disconnect(self):
        """Disconnect from the MCP server"""
        if self._connected or self.exit_stack:
            try:
                await self.exit_stack.aclose()
            except Exception as e:
                logger.error(f"Error disconnecting client {self.name}: {e}")
            finally:
                self._connected = False
                self.session = None
                logger.info(f"Disconnected MCP server: {self.name}")

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools"""
        if not self.is_connected:
            raise RuntimeError(f"Client {self.name} is not connected")
        
        try:
            result = await self.session.list_tools()
            # Serialize tools to dictionary for upper layers
            # Handling both Pydantic models from mcp types or dicts
            tools_data = []
            for t in result.tools:
                 if hasattr(t, 'model_dump'):
                     tools_data.append(t.model_dump())
                 elif hasattr(t, 'dict'):
                     tools_data.append(t.dict())
                 else:
                     # Fallback assuming it might be a simple object or dict
                     tools_data.append(t if isinstance(t, dict) else t.__dict__)
            return tools_data
        except Exception as e:
            logger.error(f"Failed to list tools for {self.name}: {e}")
            raise

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a specific tool"""
        if not self.is_connected:
            raise RuntimeError(f"Client {self.name} is not connected")
            
        try:
            return await self.session.call_tool(tool_name, arguments)
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name} on {self.name}: {e}")
            raise

class MCPStdioClient(MCPClientBase):
    """MCP Client using Stdio transport (Local Process)"""
    
    def __init__(self, name: str, command: str, args: List[str] = None, env: Dict[str, str] = None):
        super().__init__(name)
        self.server_params = StdioServerParameters(
            command=command,
            args=args or [],
            env=env
        )

    async def connect(self):
        try:
            logger.debug(f"Connecting to Stdio MCP server: {self.server_params.command}")
            transport = await self.exit_stack.enter_async_context(
                stdio_client(self.server_params)
            )
            read, write = transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await self.session.initialize()
            self._connected = True
            logger.info(f"Connected to Stdio MCP server: {self.name}")
        except Exception as e:
            logger.error(f"Failed to connect to Stdio server {self.name}: {e}")
            self._connected = False
            raise

class MCPSseClient(MCPClientBase):
    """MCP Client using SSE transport (Remote/Docker)"""
    
    def __init__(self, name: str, url: str, headers: Dict[str, str] = None):
        super().__init__(name)
        self.url = url
        self.headers = headers or {}

    async def connect(self):
        try:
            logger.debug(f"Connecting to SSE MCP server: {self.url}")
            # sse_client context manager yields (read, write) streams
            transport = await self.exit_stack.enter_async_context(
                sse_client(url=self.url, headers=self.headers)
            )
            read, write = transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await self.session.initialize()
            self._connected = True
            logger.info(f"Connected to SSE MCP server: {self.name}")
        except Exception as e:
            logger.error(f"Failed to connect to SSE server {self.name}: {e}")
            self._connected = False
            raise

def create_mcp_client(config_name: str, server_type: str, connection_config: Dict[str, Any]) -> MCPClientBase:
    """Factory function to create appropriate client"""
    if server_type == "STDIO":
        return MCPStdioClient(
            name=config_name,
            command=connection_config.get("command"),
            args=connection_config.get("args", []),
            env=connection_config.get("env")
        )
    elif server_type == "SSE" or server_type == "HTTP":
        return MCPSseClient(
            name=config_name,
            url=connection_config.get("url"),
            headers=connection_config.get("headers")
        )
    else:
        raise ValueError(f"Unsupported server type: {server_type}")
