"""
Agent API v1 - Admin routes
"""
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.auth import current_superuser
from src.users.models import User
from ...schemas import (
    MCPServerConfigCreate,
    MCPServerConfigResponse,
    MCPServerToolsResponse,
    MCPToolInfo
)
from ...service import MCPServerService
from ...mcp.registry import mcp_registry

router = APIRouter(prefix="/mcp-servers")


@router.post("", response_model=MCPServerConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_mcp_server(
    server_data: MCPServerConfigCreate,
    current_user: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_async_session)
):
    """Create MCP server configuration (Admin only)"""
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
    if not mcp_registry.is_registered(server_name):
        raise HTTPException(status_code=404, detail="MCP server not registered")
    
    try:
        tools = await mcp_registry.list_all_tools(server_name)
        tool_infos = [
            MCPToolInfo(
                name=tool["name"],
                description=tool.get("description", ""),
                inputSchema=tool.get("inputSchema", {})
            )
            for tool in tools
        ]
        
        return MCPServerToolsResponse(
            server_name=server_name,
            tools=tool_infos
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
