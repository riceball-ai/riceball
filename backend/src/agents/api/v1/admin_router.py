"""
Agent API v1 - Admin routes
"""
import uuid
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.auth import current_superuser
from src.users.models import User
from ...schemas import (
    MCPServerConfigCreate,
    MCPServerConfigResponse,
    MCPServerToolsResponse,
    MCPToolInfo,
    MCPPresetResponse
)
from ...service import MCPServerService
from ...mcp.manager import mcp_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp-servers")


@router.post("", response_model=MCPServerConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_mcp_server(
    server_data: MCPServerConfigCreate,
    current_user: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session)
):
    """Create MCP server configuration manually (Admin only)"""
    service = MCPServerService(session)
    server = await service.create_mcp_server(server_data.model_dump())
    return MCPServerConfigResponse.model_validate(server)


@router.get("", response_model=List[MCPServerConfigResponse])
async def list_mcp_servers(
    current_user: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session)
):
    """List all MCP server configurations (Admin only)"""
    service = MCPServerService(session)
    servers = await service.list_mcp_servers()
    return [MCPServerConfigResponse.model_validate(s) for s in servers]


@router.get("/presets", response_model=List[MCPPresetResponse])
async def list_mcp_presets(
    current_user: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session)
):
    """List all available MCP server presets"""
    service = MCPServerService(session)
    presets = await service.list_presets()
    return [MCPPresetResponse.model_validate(p) for p in presets]


@router.post("/presets/{preset_id}/install", response_model=MCPServerConfigResponse, status_code=status.HTTP_201_CREATED)
async def install_mcp_preset(
    preset_id: str,
    connection_overrides: Optional[Dict[str, Any]] = Body(default=None),
    current_user: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session)
):
    """Install an MCP server from a preset"""
    service = MCPServerService(session)
    try:
        server = await service.install_preset(preset_id, connection_overrides)
        return MCPServerConfigResponse.model_validate(server)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to install preset {preset_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{server_id}", response_model=MCPServerConfigResponse)
async def get_mcp_server(
    server_id: uuid.UUID,
    current_user: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session)
):
    """Get MCP server configuration (Admin only)"""
    service = MCPServerService(session)
    server = await service.get_mcp_server(server_id)
    
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return MCPServerConfigResponse.model_validate(server)


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mcp_server(
    server_id: uuid.UUID,
    current_user: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session)
):
    """Delete MCP server configuration (Admin only)"""
    service = MCPServerService(session)
    success = await service.delete_mcp_server(server_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="MCP server not found")

@router.get("/{server_name}/tools", response_model=MCPServerToolsResponse)
async def list_mcp_server_tools(
    server_name: str,
    current_user: User = Depends(current_superuser)
):
    """List tools available from MCP server (Admin only)"""
    client = await mcp_manager.get_client(server_name)
    if not client:
        # Check if it was supposed to be there but failed? 
        # For now just 404
        raise HTTPException(status_code=404, detail="MCP server not connected or registered")
        
    try:
        # We can either fetch from cache or live
        # tools = await mcp_manager.list_all_tools() # This lists all tools from all servers
        # We want specific server tools.
        # The manager caches them, but doesn't expose a clean per-server getter for cache.
        # Let's call refresh on the client to be safe and live
        tools = await client.list_tools()
        
        tool_infos = []
        for tool in tools:
            # Handle different formats (dict vs object)
            tool_data = tool if isinstance(tool, dict) else tool.__dict__
            
            tool_infos.append(MCPToolInfo(
                name=tool_data.get("name"),
                description=tool_data.get("description", ""),
                inputSchema=tool_data.get("inputSchema", {})
            ))
        
        return MCPServerToolsResponse(
            server_name=server_name,
            tools=tool_infos
        )
    except Exception as e:
        logger.error(f"Error listing tools for {server_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
