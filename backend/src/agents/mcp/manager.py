"""
MCP Connection Manager
Handles lifecycle of MCP client connections and tool caching
"""
import logging
import asyncio
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .client import MCPClientBase, create_mcp_client
from ..models import MCPServerConfig

logger = logging.getLogger(__name__)

class MCPConnectionManager:
    """
    Manages connections to multiple MCP servers.
    Handles connection lifecycle, tool discovery, and caching.
    """
    
    def __init__(self):
        # Active clients: server_name -> client instance
        self.clients: Dict[str, MCPClientBase] = {}
        # Tool cache: server_name -> list of tool definitions
        self.tool_cache: Dict[str, List[Dict[str, Any]]] = {}
    
    async def load_and_connect_all(self, session: AsyncSession):
        """
        Load all active servers from database and establish connections.
        Should be called on application startup.
        """
        logger.info("Initializing MCP Connection Manager...")
        try:
            stmt = select(MCPServerConfig).where(MCPServerConfig.is_active == True)
            result = await session.execute(stmt)
            configs = result.scalars().all()
            
            for config in configs:
                # Skip if already connected
                if config.name in self.clients and self.clients[config.name].is_connected:
                    continue
                    
                asyncio.create_task(self.connect_server(config))
                
        except Exception as e:
            logger.error(f"Failed to load MCP servers: {e}")

    async def connect_server(self, config: MCPServerConfig):
        """Connect to a single MCP server"""
        logger.info(f"Attempting to connect to MCP server: {config.name} ({config.server_type.value})")
        
        try:
            # Create client instance
            client = create_mcp_client(
                config_name=config.name,
                server_type=config.server_type.value,
                connection_config=config.connection_config or {}
            )
            
            # Connect
            await client.connect()
            
            # Since connect() is async and might not be fully ready immediately if it uses background tasks?
            # Actually standard client.connect() awaits until session is initialized.
            
            self.clients[config.name] = client
            
            # Initial tool discovery
            try:
                await self.refresh_tools(config.name)
            except Exception as e:
                 logger.warning(f"Initial tool refresh failed for {config.name}, but connection is active: {e}")
            
            logger.info(f"Successfully connected to MCP server: {config.name}")
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {config.name}: {e}")
            # We don't raise here to allow other servers to connect

    async def disconnect_server(self, name: str):
        """Disconnect a specific server"""
        if client := self.clients.get(name):
            await client.disconnect()
            del self.clients[name]
            if name in self.tool_cache:
                del self.tool_cache[name]

    async def get_client(self, name: str) -> Optional[MCPClientBase]:
        """Get a connected client by name"""
        return self.clients.get(name)

    async def get_tools(self, name: str) -> Optional[List[Dict[str, Any]]]:
        """Get tools for a server (from cache or client)"""
        return self.tool_cache.get(name)

    async def list_all_tools(self) -> List[Dict[str, Any]]:
        """
        Return a flattened list of all available tools from all servers.
        Injects 'server_name' into each tool definition for routing.
        """
        all_tools = []
        for server_name, tools in self.tool_cache.items():
            for tool in tools:
                # Create a copy to avoid modifying cache
                tool_copy = tool.copy()
                tool_copy['_server_name'] = server_name # Internal metadata
                all_tools.append(tool_copy)
        return all_tools

    async def refresh_tools(self, server_name: str):
        """Force refresh tools for a specific server"""
        if client := self.clients.get(server_name):
            try:
                tools = await client.list_tools()
                self.tool_cache[server_name] = tools
                logger.debug(f"Refreshed {len(tools)} tools for {server_name}")
            except Exception as e:
                logger.error(f"Failed to refresh tools for {server_name}: {e}")

    async def shutdown(self):
        """Gracefully shutdown all connections"""
        logger.info("Shutting down MCP Connection Manager...")
        for name in list(self.clients.keys()):
            await self.disconnect_server(name)

# Global instance
mcp_manager = MCPConnectionManager()
