// Composable for MCP API operations
import { type MCPServerConfigResponse, type MCPPresetResponse, type MCPServerToolsResponse } from '~/types/mcp'

export const useMCP = () => {
  const { $api } = useNuxtApp()

  const listServers = async () => {
    return await $api<MCPServerConfigResponse[]>('/api/v1/admin/mcp-servers')
  }

  const listPresets = async () => {
    return await $api<MCPPresetResponse[]>('/api/v1/admin/mcp-servers/presets')
  }

  const installPreset = async (presetId: string, overrides: Record<string, any> = {}) => {
    return await $api<MCPServerConfigResponse>(`/api/v1/admin/mcp-servers/presets/${presetId}/install`, {
      method: 'POST',
      body: overrides
    })
  }

  const createServer = async (data: any) => {
    return await $api<MCPServerConfigResponse>('/api/v1/admin/mcp-servers', {
      method: 'POST',
      body: data
    })
  }

  const deleteServer = async (serverId: string) => {
    return await $api(`/api/v1/admin/mcp-servers/${serverId}`, {
      method: 'DELETE'
    })
  }

  const updateServer = async (serverId: string, data: any) => {
    return await $api<MCPServerConfigResponse>(`/api/v1/admin/mcp-servers/${serverId}`, {
        method: 'PATCH',
        body: data
    })
  }

  const listTools = async (serverName: string) => {
      return await $api<MCPServerToolsResponse>(`/api/v1/admin/mcp-servers/${serverName}/tools`)
  }

  return {
    listServers,
    listPresets,
    installPreset,
    createServer,
    deleteServer,
    updateServer,
    listTools
  }
}
