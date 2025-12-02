"""
MCP Server Registry
"""
import logging
from typing import Dict, List

from mcp import StdioServerParameters

from .client import MCPClient
from ..models import MCPServerConfig

logger = logging.getLogger(__name__)


class MCPServerRegistry:
    """MCP server registry for managing server connections"""
    
    def __init__(self):
        self.servers: Dict[str, MCPClient] = {}
    
    async def register_server(self, config: MCPServerConfig) -> MCPClient:
        """Register and connect to an MCP server"""
        try:
            # Check server type
            if config.server_type.value != "STDIO":
                raise ValueError(f"Unsupported server type: {config.server_type}")
            
            # Create server parameters
            connection_config = config.connection_config
            server_params = StdioServerParameters(
                command=connection_config["command"],
                args=connection_config.get("args", []),
                env=connection_config.get("env")
            )
            
            # Create and connect client
            client = MCPClient(server_params)
            await client.connect()
            
            # Store in registry
            self.servers[config.name] = client
            logger.info(f"Registered MCP server: {config.name}")
            
            return client
            
        except Exception as e:
            logger.error(f"Failed to register MCP server {config.name}: {e}")
            raise
    
    async def get_server(self, name: str) -> MCPClient:
        """Get MCP server client"""
        if name not in self.servers:
            raise ValueError(f"MCP server '{name}' not registered")
        return self.servers[name]
    
    def is_registered(self, name: str) -> bool:
        """Check if server is registered"""
        return name in self.servers
    
    async def list_all_tools(self, server_name: str) -> List[Dict]:
        """List all tools from a server"""
        client = await self.get_server(server_name)
        return await client.list_tools()
    
    async def unregister_server(self, name: str):
        """Unregister and disconnect a server"""
        if name in self.servers:
            client = self.servers[name]
            await client.disconnect()
            del self.servers[name]
            logger.info(f"Unregistered MCP server: {name}")
    
    async def shutdown_all(self):
        """Shutdown all registered servers"""
        for name, client in list(self.servers.items()):
            try:
                await client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting server {name}: {e}")
        self.servers.clear()
        logger.info("All MCP servers shut down")
    
    def list_registered_servers(self) -> List[str]:
        """List all registered server names"""
        return list(self.servers.keys())


# Global registry instance
mcp_registry = MCPServerRegistry()
