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

  const deleteServer = async (serverId: string) => {
    return await $api(`/api/v1/admin/mcp-servers/${serverId}`, {
      method: 'DELETE'
    })
  }

  const listTools = async (serverName: string) => {
      // Need to handle error gracefully if server is disconnected
      try {
        return await $api<MCPServerToolsResponse>(`/api/v1/admin/mcp-servers/${serverName}/tools`)
      } catch (e) {
          console.error("Failed to list tools", e)
          return null
      }
  }

  return {
    listServers,
    listPresets,
    installPreset,
    deleteServer,
    listTools
  }
}
