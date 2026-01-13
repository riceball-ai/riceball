"""
MCP Server Presets
Predefined configurations for common MCP servers to simplify setup.
"""
from typing import Dict, Any, List
from pydantic import BaseModel

from ..models import MCPServerTypeEnum

class MCPPreset(BaseModel):
    id: str
    name: str
    description: str
    server_type: MCPServerTypeEnum
    connection_config: Dict[str, Any]
    logo_url: str | None = None

# Define built-in presets
MCP_PRESETS: List[MCPPreset] = [
    MCPPreset(
        id="filesystem-docker",
        name="Filesystem (Docker Sidecar)",
        description="Access local files via Docker sidecar container. Requires 'mcp-filesystem' service in docker-compose.",
        server_type=MCPServerTypeEnum.HTTP,
        connection_config={
            "url": "http://localhost:8999/sse",
            "headers": {}
        }
    ),
    MCPPreset(
        id="brave-search-docker",
        name="Brave Search (Docker Sidecar)",
        description="Web search capability via Brave Search API. Requires 'mcp-brave' service in docker-compose and API Key.",
        server_type=MCPServerTypeEnum.HTTP,
        connection_config={
            "url": "http://mcp-brave:8000/sse",
            "headers": {}
        }
    ),
    MCPPreset(
        id="fetch-docker",
        name="Fetch (Docker Sidecar)",
        description="Fetch URL content. Requires 'mcp-fetch' service.",
        server_type=MCPServerTypeEnum.HTTP,
        connection_config={
            "url": "http://mcp-fetch:8000/sse",
            "headers": {}
        }
    ),
    # Keep a local example just in case someone runs locally without Docker
    MCPPreset(
        id="filesystem-local-npm",
        name="Filesystem (Local NPM)",
        description="[DEV ONLY] Runs 'npx -y @modelcontextprotocol/server-filesystem' locally. Requires Node.js installed on backend host.",
        server_type=MCPServerTypeEnum.STDIO,
        connection_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/files"],
            "env": {}
        }
    )
]

def get_preset_by_id(preset_id: str) -> MCPPreset | None:
    for preset in MCP_PRESETS:
        if preset.id == preset_id:
            return preset
    return None
