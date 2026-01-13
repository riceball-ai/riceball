// Frontend types for MCP

export enum MCPServerTypeEnum {
    STDIO = "STDIO",
    SSE = "SSE",
    HTTP = "HTTP"
}

export interface MCPServerConfigResponse {
    id: string;
    name: string;
    description?: string;
    server_type: MCPServerTypeEnum;
    connection_config: Record<string, any>;
    is_active: boolean;
    extra_data: Record<string, any>;
    created_at: string;
    updated_at: string;
}

export interface MCPToolInfo {
    name: string;
    description: string;
    inputSchema: Record<string, any>;
}

export interface MCPServerToolsResponse {
    server_name: string;
    tools: MCPToolInfo[];
}

export interface MCPPresetResponse {
    id: string;
    name: string;
    description: string;
    server_type: MCPServerTypeEnum;
    connection_config: Record<string, any>;
    logo_url?: string;
}

export interface MCPServerConfigCreate {
    name: string;
    description?: string;
    server_type: MCPServerTypeEnum;
    connection_config: Record<string, any>;
    is_active?: boolean;
}
