"""
Agent Service - Business logic for MCP Server operations
"""
import uuid
import logging
import asyncio
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .models import MCPServerConfig
from .mcp.manager import mcp_manager
from .mcp.presets import MCP_PRESETS, get_preset_by_id

logger = logging.getLogger(__name__)


class MCPServerService:
    """MCP server configuration service"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_mcp_server(self, server_data: Dict[str, Any]) -> MCPServerConfig:
        """Create MCP server configuration manually"""
        server = MCPServerConfig(**server_data)
        
        self.session.add(server)
        await self.session.commit()
        await self.session.refresh(server)
        
        # Connect if active
        if server.is_active:
            # Run connection in background to avoid blocking API response
            asyncio.create_task(mcp_manager.connect_server(server))
        
        return server
    
    async def install_preset(self, preset_id: str, connection_overrides: Dict[str, Any] = None) -> MCPServerConfig:
        """Install an MCP server from a preset"""
        preset = get_preset_by_id(preset_id)
        if not preset:
            raise ValueError(f"Preset {preset_id} not found")
            
        connection_config = preset.connection_config.copy()
        if connection_overrides:
            connection_config.update(connection_overrides)
            
        # Ensure unique name
        base_name = preset.name
        name = base_name
        counter = 1
        
        # Simple name collision avoidance loop
        while True:
            stmt = select(MCPServerConfig).where(MCPServerConfig.name == name)
            existing = (await self.session.execute(stmt)).scalar_one_or_none()
            if not existing:
                break
            name = f"{base_name} ({counter})"
            counter += 1

        server_data = {
            "name": name,
            "description": preset.description,
            "server_type": preset.server_type,
            "connection_config": connection_config,
            "is_active": True,
            "extra_data": {
                "installed_from_preset": preset_id,
                "logo_url": preset.logo_url
            }
        }
        
        server = MCPServerConfig(**server_data)
        self.session.add(server)
        await self.session.commit()
        await self.session.refresh(server)
        
        # Auto connect in background
        asyncio.create_task(mcp_manager.connect_server(server))
        
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
    
    async def list_presets(self) -> List[Any]:
        """List available presets"""
        return MCP_PRESETS

    async def update_mcp_server(self, server_id: uuid.UUID, update_data: Dict[str, Any]) -> Optional[MCPServerConfig]:
        """Update MCP server configuration"""
        server = await self.get_mcp_server(server_id)
        if not server:
            return None
            
        # Check if name is changing and if new name conflicts
        if "name" in update_data and update_data["name"] != server.name:
            stmt = select(MCPServerConfig).where(MCPServerConfig.name == update_data["name"])
            existing = (await self.session.execute(stmt)).scalar_one_or_none()
            if existing:
                raise ValueError(f"Server with name '{update_data['name']}' already exists")
                
        # Store old name for disconnection if needed
        old_name = server.name
        
        # Update fields
        for key, value in update_data.items():
            if hasattr(server, key):
                setattr(server, key, value)
                
        await self.session.commit()
        await self.session.refresh(server)
        
        # Reconnect logic
        # Always disconnect the old one
        await mcp_manager.disconnect_server(old_name)
        
        # If still active, connect the new one
        if server.is_active:
             asyncio.create_task(mcp_manager.connect_server(server))
             
        return server

    async def delete_mcp_server(self, server_id: uuid.UUID) -> bool:
        """Delete MCP server"""
        server = await self.get_mcp_server(server_id)
        if not server:
            return False
        
        # Disconnect
        await mcp_manager.disconnect_server(server.name)
        
        await self.session.delete(server)
        await self.session.commit()
        
        return True
