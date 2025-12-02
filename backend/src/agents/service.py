"""
Agent Service - Business logic for MCP Server operations
"""
import uuid
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .models import MCPServerConfig
from .mcp.registry import mcp_registry

logger = logging.getLogger(__name__)


class MCPServerService:
    """MCP server configuration service"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_mcp_server(self, server_data: Dict[str, Any]) -> MCPServerConfig:
        """Create MCP server configuration"""
        server = MCPServerConfig(**server_data)
        
        self.session.add(server)
        await self.session.commit()
        await self.session.refresh(server)
        
        # Try to register with MCP registry
        if server.is_active:
            try:
                await mcp_registry.register_server(server)
            except Exception as e:
                logger.error(f"Failed to register MCP server: {e}")
        
        return server
    
    async def get_mcp_server(self, server_id: uuid.UUID) -> Optional[MCPServerConfig]:
        """Get MCP server by ID"""
        stmt = select(MCPServerConfig).where(MCPServerConfig.id == server_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_mcp_servers(self) -> List[MCPServerConfig]:
        """List all MCP servers"""
        stmt = select(MCPServerConfig)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def delete_mcp_server(self, server_id: uuid.UUID) -> bool:
        """Delete MCP server"""
        server = await self.get_mcp_server(server_id)
        if not server:
            return False
        
        # Unregister from MCP registry
        if mcp_registry.is_registered(server.name):
            await mcp_registry.unregister_server(server.name)
        
        await self.session.delete(server)
        await self.session.commit()
        
        return True
