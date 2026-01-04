<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Card, CardContent, CardHeader, CardTitle } from '~/components/ui/card'
import { Label } from '~/components/ui/label'
import { Input } from '~/components/ui/input'
import { Switch } from '~/components/ui/switch'
import { Bot } from 'lucide-vue-next'
import type { AvailableAgentTools } from '~/types/api'

const { t } = useI18n()

interface AgentConfigData {
  enable_agent: boolean
  agent_max_iterations: number
  agent_enabled_tools: string[]
  mcp_server_ids: string[]
}

interface Props {
  modelValue: AgentConfigData
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false
})

const emit = defineEmits<{
  'update:modelValue': [value: AgentConfigData]
}>()

// Fetch available Agent tools
const { data: availableTools } = useAPI<AvailableAgentTools>('/v1/admin/agent-tools/available', { server: false })

const updateField = <K extends keyof AgentConfigData>(key: K, value: AgentConfigData[K]) => {
  const newValue = { ...props.modelValue, [key]: value }
  emit('update:modelValue', newValue)
}

const toggleTool = (toolName: string, checked: boolean) => {
  const currentTools = [...(props.modelValue.agent_enabled_tools || [])]
  if (checked) {
    if (!currentTools.includes(toolName)) {
      currentTools.push(toolName)
    }
  } else {
    const index = currentTools.indexOf(toolName)
    if (index > -1) {
      currentTools.splice(index, 1)
    }
  }
  updateField('agent_enabled_tools', currentTools)
}

const toggleMcpServer = (serverId: string, checked: boolean) => {
  const currentServers = [...(props.modelValue.mcp_server_ids || [])]
  if (checked) {
    if (!currentServers.includes(serverId)) {
      currentServers.push(serverId)
    }
  } else {
    const index = currentServers.indexOf(serverId)
    if (index > -1) {
      currentServers.splice(index, 1)
    }
  }
  updateField('mcp_server_ids', currentServers)
}
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle class="flex items-center gap-2">
        <Bot class="h-5 w-5" />
        {{ t('admin.pages.assistants.create.agentConfig.title') }}
      </CardTitle>
    </CardHeader>
    <CardContent>
      <div class="space-y-6">
        <!-- Enable Agent -->
        <div class="space-y-2">
          <div class="flex items-center space-x-2">
            <Switch
              id="enable_agent"
              :model-value="props.modelValue.enable_agent"
              :disabled="disabled"
              @update:model-value="(val) => updateField('enable_agent', val)"
            />
            <Label for="enable_agent" class="text-sm cursor-pointer">
              {{ t('admin.pages.assistants.create.agentConfig.enableLabel') }}
            </Label>
          </div>
          <div class="text-sm text-muted-foreground">
            {{ t('admin.pages.assistants.create.agentConfig.enableHelp') }}
          </div>
        </div>

        <!-- Agent Max Iterations -->
        <div v-if="props.modelValue.enable_agent" class="space-y-2">
          <Label for="agent_max_iterations">{{ t('admin.pages.assistants.create.agentConfig.maxIterationsLabel') }}</Label>
          <Input
            id="agent_max_iterations"
            :model-value="props.modelValue.agent_max_iterations"
            @update:model-value="(val) => updateField('agent_max_iterations', Number(val))"
            type="number"
            placeholder="5"
            min="1"
            max="20"
            :disabled="disabled"
            class="max-w-xs"
          />
          <div class="text-sm text-muted-foreground">
            {{ t('admin.pages.assistants.create.agentConfig.maxIterationsHelp') }}
          </div>
        </div>

        <!-- Local Tools -->
        <div v-if="props.modelValue.enable_agent && availableTools?.local_tools?.length" class="space-y-3">
          <div>
            <Label>{{ t('admin.pages.assistants.create.agentConfig.localToolsLabel') }}</Label>
            <div class="text-sm text-muted-foreground">
              {{ t('admin.pages.assistants.create.agentConfig.localToolsHelp') }}
            </div>
          </div>
          <div class="space-y-2 ml-2">
            <div
              v-for="tool in availableTools.local_tools"
              :key="tool.name"
              class="flex items-start space-x-2"
            >
              <Switch
                :id="`tool-${tool.name}`"
                :model-value="props.modelValue.agent_enabled_tools?.includes(tool.name)"
                @update:model-value="(checked) => toggleTool(tool.name, checked)"
                :disabled="disabled"
              />
              <div class="grid gap-1 leading-none">
                <Label
                  :for="`tool-${tool.name}`"
                  class="text-sm font-medium leading-none cursor-pointer"
                >
                  {{ tool.name }}
                </Label>
                <p class="text-sm text-muted-foreground">
                  {{ tool.description }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- MCP Servers -->
        <div v-if="props.modelValue.enable_agent && availableTools?.mcp_servers?.length" class="space-y-3">
          <div>
            <Label>{{ t('admin.pages.assistants.create.agentConfig.mcpServersLabel') }}</Label>
            <div class="text-sm text-muted-foreground">
              {{ t('admin.pages.assistants.create.agentConfig.mcpServersHelp') }}
            </div>
          </div>
          <div class="space-y-2 ml-2">
            <div
              v-for="server in availableTools.mcp_servers"
              :key="server.id"
              class="flex items-start space-x-2"
            >
              <Switch
                :id="`mcp-${server.id}`"
                :model-value="props.modelValue.mcp_server_ids?.includes(server.id)"
                @update:model-value="(checked) => toggleMcpServer(server.id, checked)"
                :disabled="disabled"
              />
              <div class="grid gap-1 leading-none">
                <Label
                  :for="`mcp-${server.id}`"
                  class="text-sm font-medium leading-none cursor-pointer"
                >
                  {{ server.name }}
                </Label>
                <p class="text-sm text-muted-foreground">
                  {{ server.description }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- No Tools Hint -->
        <div v-if="props.modelValue.enable_agent && !availableTools?.local_tools?.length && !availableTools?.mcp_servers?.length" class="text-sm text-muted-foreground p-4 bg-muted rounded-md">
          {{ t('admin.pages.assistants.create.agentConfig.noTools') }}
        </div>
      </div>
    </CardContent>
  </Card>
</template>
