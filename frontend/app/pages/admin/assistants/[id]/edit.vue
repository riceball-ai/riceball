<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, Save, X, Trash2 } from 'lucide-vue-next'
import { Button } from '~/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card'
import { Input } from '~/components/ui/input'
import { Label } from '~/components/ui/label'
import { Textarea } from '~/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '~/components/ui/select'
import KnowledgeBaseConfig from '~/components/admin/KnowledgeBaseConfig.vue'
import { 
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '~/components/ui/alert-dialog'
import { toast } from 'vue-sonner'
import type { Assistant, Model, RagConfig, AvailableAgentTools } from '~/types/api'
import { ASSISTANT_CATEGORIES } from '~/constants/assistants'

const { t } = useI18n()

// Page metadata
definePageMeta({
  breadcrumb: 'admin.pages.assistants.edit.breadcrumb',
  layout: 'admin'
})

const router = useRouter()
const route = useRoute()
const assistantId = route.params.id as string

// Fetch model list
const { data: models } = useAPI<Model[]>('/v1/admin/all-models?capabilities=chat', { server: false })

const modelOptions = computed(() =>
  (models.value ?? []).map(m => ({ label: m.display_name, value: m.id }))
)

// Fetch available Agent tools
const { data: availableTools } = useAPI<AvailableAgentTools>('/v1/admin/agent-tools/available', { server: false })

// State management
const loading = ref(false)
const saveLoading = ref(false)
const deleteLoading = ref(false)
const assistant = ref<Assistant | null>(null)

// Form data
const formData = ref<Partial<Assistant>>({
  name: '',
  avatar_file_path: '',
  description: '',
  system_prompt: '',
  model_id: '',
  temperature: 0.7,
  max_history_messages: undefined,
  is_public: false,
  status: 'DRAFT',
  category: 'general',
  tags: [],
  enable_agent: false,
  agent_max_iterations: 5,
  agent_enabled_tools: [],
  mcp_server_ids: []
})

// Tag input handling
const tagsInput = computed({
  get: () => formData.value.tags?.join(', ') || '',
  set: (val: string) => {
    formData.value.tags = val.split(/[,，]/).map(t => t.trim()).filter(Boolean)
  }
})

// Form validation errors
const errors = ref<Record<string, string>>({})

// Knowledge base config state
const knowledgeBaseConfig = ref<{
  knowledge_base_ids: string[]
  rag_config?: RagConfig
}>({
  knowledge_base_ids: [],
  rag_config: undefined
})

// Load assistant data
const loadAssistant = async () => {
  loading.value = true
  try {
    const { $api } = useNuxtApp()
    const response = await $api(`/v1/admin/assistants/${assistantId}`) as any
    assistant.value = response
    
    // Initialize form data
    formData.value = {
      name: response.name || '',
      avatar_file_path: response.avatar_file_path || '',
      description: response.description || '',
      system_prompt: response.system_prompt || '',
      model_id: response.model_id || '',
      temperature: response.temperature || 0.7,
      max_history_messages: response.max_history_messages,
      is_public: response.is_public || false,
      status: response.status || 'DRAFT',
      category: response.category || 'general',
      tags: response.tags || [],
      enable_agent: response.enable_agent || false,
      agent_max_iterations: response.agent_max_iterations || 5,
      agent_enabled_tools: response.agent_enabled_tools || [],
      mcp_server_ids: response.mcp_server_ids || []
    }
    
    // Initialize knowledge base config
    knowledgeBaseConfig.value = {
      knowledge_base_ids: response.knowledge_base_ids || [],
      rag_config: response.rag_config || undefined
    }
    
  } catch (error) {
    console.error('Failed to load assistant data:', error)
    toast.error(t('admin.pages.assistants.edit.loadFailed'))
    router.push('/admin/assistants')
  } finally {
    loading.value = false
  }
}

// Form validation
const validateForm = (): boolean => {
  const newErrors: Record<string, string> = {}
  
  if (!formData.value.name || formData.value.name.length < 2) {
    newErrors.name = t('admin.pages.assistants.create.validation.nameMin')
  }
  // description is optional now
  if (!formData.value.system_prompt || formData.value.system_prompt.length < 10) {
    newErrors.system_prompt = t('admin.pages.assistants.create.validation.systemPromptMin')
  }
  if (!formData.value.model_id) {
    newErrors.model_id = t('admin.pages.assistants.create.validation.modelRequired')
  }
  if (!formData.value.status) {
    newErrors.status = t('admin.pages.assistants.create.validation.statusRequired')
  }
  
  errors.value = newErrors
  return Object.keys(newErrors).length === 0
}

// Update assistant
const updateAssistant = async () => {
  if (!validateForm()) {
    toast.error(t('admin.pages.assistants.create.checkForm'))
    return
  }
  
  saveLoading.value = true
  try {
    const { $api } = useNuxtApp()
    
    // Merge form data and knowledge base config
    const submitData = {
      ...formData.value,
      ...knowledgeBaseConfig.value
    }
    
    await $api(`/v1/admin/assistants/${assistantId}`, {
      method: 'PUT',
      body: submitData
    })
    
    toast.success(t('admin.pages.assistants.edit.updateSuccess'))
    router.push('/admin/assistants')
    
  } catch (error) {
    console.error('Update failed:', error)
    toast.error(t('admin.pages.assistants.edit.updateFailed'))
  } finally {
    saveLoading.value = false
  }
}

// Delete assistant
const deleteAssistant = async () => {
  deleteLoading.value = true
  try {
    const { $api } = useNuxtApp()
    await $api(`/v1/admin/assistants/${assistantId}`, {
      method: 'DELETE'
    })
    
    toast.success(t('admin.pages.assistants.edit.deleteSuccess'))
    router.push('/admin/assistants')
    
  } catch (error) {
    console.error('Delete failed:', error)
    toast.error(t('admin.pages.assistants.edit.deleteFailed'))
  } finally {
    deleteLoading.value = false
  }
}

// Cancel action
const handleCancel = () => {
  router.push('/admin/assistants')
}

// Page initialization
onMounted(() => {
  loadAssistant()
})
</script>

<template>
  <div class="container mx-auto py-6 space-y-6">
    <!-- Header navigation -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-4">
        <Button variant="ghost" size="sm" @click="handleCancel">
          <ArrowLeft class="h-4 w-4 mr-2" />
          {{ t('admin.back') }}
        </Button>
        <div>
          <h1 class="text-2xl font-bold">{{ t('admin.pages.assistants.edit.title') }}</h1>
          <p class="text-muted-foreground">
            {{ assistant?.name ? t('admin.pages.assistants.edit.editing', { name: assistant.name }) : t('admin.loading') }}
          </p>
        </div>
      </div>

      <!-- Delete button -->
      <AlertDialog>
        <AlertDialogTrigger as-child>
          <Button variant="destructive" size="sm" :disabled="loading">
            <Trash2 class="h-4 w-4 mr-2" />
            {{ t('admin.delete') }}
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{{ t('admin.pages.assistants.edit.deleteConfirm.title') }}</AlertDialogTitle>
            <AlertDialogDescription>
              {{ t('admin.pages.assistants.edit.deleteConfirm.description', { name: assistant?.name }) }}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{{ t('admin.cancel') }}</AlertDialogCancel>
            <AlertDialogAction 
              @click="deleteAssistant" 
              :disabled="deleteLoading"
              class="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {{ t('admin.confirm') }}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
    </div>

    <!-- Form card -->
    <Card v-else-if="assistant" class="max-w-4xl">
      <CardHeader>
        <CardTitle>{{ t('admin.pages.assistants.edit.title') }}</CardTitle>
        <CardDescription>
          {{ t('admin.pages.assistants.edit.description') }}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form @submit.prevent="updateAssistant" class="space-y-6">
          <!-- Basic info -->
          <div class="space-y-4">
            <!-- Avatar -->
            <div class="space-y-2">
              <Label for="avatar">{{ t('admin.pages.assistants.create.basicInfo.avatarLabel') }}</Label>
              <AvatarUpload
                id="avatar"
                v-model="formData.avatar_file_path"
                :initial-url="assistant?.avatar_url"
                :disabled="saveLoading"
              />
              <div class="text-sm text-muted-foreground">
                {{ t('admin.pages.assistants.create.basicInfo.avatarHelp') }}
              </div>
            </div>
        
            <!-- Name -->
            <div class="space-y-2">
              <Label for="name">
                {{ t('admin.pages.assistants.create.basicInfo.nameLabel') }} <span class="text-destructive">*</span>
              </Label>
              <Input
                id="name"
                v-model="formData.name"
                :placeholder="t('admin.pages.assistants.create.basicInfo.namePlaceholder')"
                :class="{ 'border-destructive': errors.name }"
                :disabled="saveLoading"
              />
              <div v-if="errors.name" class="text-sm text-destructive">
                {{ errors.name }}
              </div>
            </div>

            <!-- Description -->
            <div class="space-y-2">
              <Label for="description">
                {{ t('admin.pages.assistants.create.basicInfo.descriptionLabel') }}
              </Label>
              <Textarea
                id="description"
                v-model="formData.description"
                :placeholder="t('admin.pages.assistants.create.basicInfo.descriptionPlaceholder')"
                :rows="3"
                :class="{ 'border-destructive': errors.description }"
                :disabled="saveLoading"
              />
              <div v-if="errors.description" class="text-sm text-destructive">
                {{ errors.description }}
              </div>
            </div>

            <!-- Category -->
            <div class="space-y-2">
              <Label for="category">{{ t('admin.pages.assistants.create.basicInfo.categoryLabel') }}</Label>
              <Select v-model="formData.category" :disabled="saveLoading">
                <SelectTrigger>
                  <SelectValue :placeholder="t('admin.pages.assistants.create.basicInfo.categoryPlaceholder')" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem
                    v-for="category in ASSISTANT_CATEGORIES"
                    :key="category.value"
                    :value="category.value"
                  >
                    {{ t(`admin.pages.assistants.create.basicInfo.categories.${category.value}`) }}
                  </SelectItem>
                </SelectContent>
              </Select>
              <div class="text-sm text-muted-foreground">
                {{ t('admin.pages.assistants.create.basicInfo.categoryHelp') }}
              </div>
            </div>

            <!-- Tags -->
            <div class="space-y-2">
              <Label for="tags">{{ t('admin.pages.assistants.create.basicInfo.tagsLabel') }}</Label>
              <Input
                id="tags"
                v-model="tagsInput"
                :placeholder="t('admin.pages.assistants.create.basicInfo.tagsPlaceholder')"
                :disabled="saveLoading"
              />
              <div class="text-sm text-muted-foreground">
                {{ t('admin.pages.assistants.create.basicInfo.tagsHelp') }}
              </div>
            </div>
          </div>

          <!-- Model config -->
          <div class="space-y-4">
            <h3 class="text-lg font-medium">{{ t('admin.pages.assistants.create.modelConfig.title') }}</h3>
            
            <!-- System prompt -->
            <div class="space-y-2">
              <Label for="system_prompt">
                {{ t('admin.pages.assistants.create.modelConfig.systemPromptLabel') }} <span class="text-destructive">*</span>
              </Label>
              <Textarea
                id="system_prompt"
                v-model="formData.system_prompt"
                :placeholder="t('admin.pages.assistants.create.modelConfig.systemPromptPlaceholder')"
                :rows="5"
                :class="{ 'border-destructive': errors.system_prompt }"
                :disabled="saveLoading"
              />
              <div v-if="errors.system_prompt" class="text-sm text-destructive">
                {{ errors.system_prompt }}
              </div>
              <div class="text-sm text-muted-foreground">
                {{ t('admin.pages.assistants.create.modelConfig.systemPromptHelp') }}
              </div>
            </div>

            <!-- Model selection -->
            <div class="space-y-2">
              <Label for="model_id">
                {{ t('admin.pages.assistants.create.modelConfig.modelLabel') }} <span class="text-destructive">*</span>
              </Label>
              <Select v-model="formData.model_id" :disabled="saveLoading">
                <SelectTrigger :class="{ 'border-destructive': errors.model_id }">
                  <SelectValue :placeholder="t('admin.pages.assistants.create.modelConfig.modelPlaceholder')" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem
                    v-for="model in modelOptions"
                    :key="model.value"
                    :value="model.value"
                  >
                    {{ model.label }}
                  </SelectItem>
                </SelectContent>
              </Select>
              <div v-if="errors.model_id" class="text-sm text-destructive">
                {{ errors.model_id }}
              </div>
              <div class="text-sm text-muted-foreground">
                {{ t('admin.pages.assistants.create.modelConfig.modelHelp') }}
              </div>
            </div>

            <!-- Parameter config -->
            <div class="grid grid-cols-2 gap-4">
              <div class="space-y-2">
                <Label for="temperature">{{ t('admin.pages.assistants.create.modelConfig.temperatureLabel') }}</Label>
                <Input
                  id="temperature"
                  v-model.number="formData.temperature"
                  type="number"
                  placeholder="0.7"
                  min="0"
                  max="2"
                  step="0.1"
                  :disabled="saveLoading"
                />
                <div class="text-sm text-muted-foreground">
                  {{ t('admin.pages.assistants.create.modelConfig.temperatureHelp') }}
                </div>
              </div>
              <div class="space-y-2">
                <Label for="max_history_messages">{{ t('admin.pages.assistants.create.modelConfig.maxHistoryLabel') }}</Label>
                <Input
                  id="max_history_messages"
                  v-model.number="formData.max_history_messages"
                  type="number"
                  placeholder="10"
                  min="0"
                  max="100"
                  :disabled="saveLoading"
                  class="max-w-xs"
                />
                <div class="text-sm text-muted-foreground">
                  {{ t('admin.pages.assistants.create.modelConfig.maxHistoryHelp') }}
                </div>
              </div>
            </div>
          </div>

          <!-- Publish settings -->
          <div class="space-y-4">
            <h3 class="text-lg font-medium">{{ t('admin.pages.assistants.create.publishSettings.title') }}</h3>
            
            <!-- Public toggle -->
            <div class="flex items-center space-x-2">
              <input
                id="is_public"
                type="checkbox"
                v-model="formData.is_public"
                :disabled="saveLoading"
                class="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
              />
              <Label for="is_public" class="text-sm cursor-pointer">
                {{ t('admin.pages.assistants.create.publishSettings.isPublicLabel') }}
              </Label>
            </div>

            <!-- Status -->
            <div class="space-y-2">
              <Label for="status">
                {{ t('admin.pages.assistants.create.publishSettings.statusLabel') }} <span class="text-destructive">*</span>
              </Label>
              <Select v-model="formData.status" :disabled="saveLoading">
                <SelectTrigger :class="{ 'border-destructive': errors.status }">
                  <SelectValue :placeholder="t('admin.pages.assistants.create.publishSettings.statusPlaceholder')" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ACTIVE">{{ t('admin.pages.assistants.create.publishSettings.statuses.active') }}</SelectItem>
                  <SelectItem value="INACTIVE">{{ t('admin.pages.assistants.create.publishSettings.statuses.inactive') }}</SelectItem>
                  <SelectItem value="DRAFT">{{ t('admin.pages.assistants.create.publishSettings.statuses.draft') }}</SelectItem>
                </SelectContent>
              </Select>
              <div v-if="errors.status" class="text-sm text-destructive">
                {{ errors.status }}
              </div>
            </div>
          </div>

          <!-- Agent config -->
          <div class="space-y-4">
            <h3 class="text-lg font-medium">{{ t('admin.pages.assistants.create.agentConfig.title') }}</h3>
            
            <!-- Enable Agent -->
            <div class="space-y-2">
              <div class="flex items-center space-x-2">
                <input
                  id="enable_agent"
                  type="checkbox"
                  v-model="formData.enable_agent"
                  :disabled="saveLoading"
                  class="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                />
                <Label for="enable_agent" class="text-sm cursor-pointer">
                  {{ t('admin.pages.assistants.create.agentConfig.enableLabel') }}
                </Label>
              </div>
              <div class="text-sm text-muted-foreground">
                {{ t('admin.pages.assistants.create.agentConfig.enableHelp') }}
              </div>
            </div>

            <!-- Agent max iterations -->
            <div v-if="formData.enable_agent" class="space-y-2">
              <Label for="agent_max_iterations">{{ t('admin.pages.assistants.create.agentConfig.maxIterationsLabel') }}</Label>
              <Input
                id="agent_max_iterations"
                v-model.number="formData.agent_max_iterations"
                type="number"
                placeholder="5"
                min="1"
                max="20"
                :disabled="saveLoading"
                class="max-w-xs"
              />
              <div class="text-sm text-muted-foreground">
                {{ t('admin.pages.assistants.create.agentConfig.maxIterationsHelp') }}
              </div>
            </div>

            <!-- Local tools -->
            <div v-if="formData.enable_agent && availableTools?.local_tools?.length" class="space-y-3">
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
                  <input
                    :id="`tool-${tool.name}`"
                    type="checkbox"
                    :checked="formData.agent_enabled_tools?.includes(tool.name)"
                    @change="(e: Event) => {
                      const target = e.target as HTMLInputElement
                      const checked = target.checked
                      if (!formData.agent_enabled_tools) {
                        formData.agent_enabled_tools = []
                      }
                      if (checked) {
                        if (!formData.agent_enabled_tools.includes(tool.name)) {
                          formData.agent_enabled_tools.push(tool.name)
                        }
                      } else {
                        const index = formData.agent_enabled_tools.indexOf(tool.name)
                        if (index > -1) {
                          formData.agent_enabled_tools.splice(index, 1)
                        }
                      }
                    }"
                    :disabled="saveLoading"
                    class="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
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

            <!-- MCP servers -->
            <div v-if="formData.enable_agent && availableTools?.mcp_servers?.length" class="space-y-3">
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
                  <input
                    :id="`mcp-${server.id}`"
                    type="checkbox"
                    :checked="formData.mcp_server_ids?.includes(server.id)"
                    @change="(e: Event) => {
                      const target = e.target as HTMLInputElement
                      const checked = target.checked
                      if (!formData.mcp_server_ids) {
                        formData.mcp_server_ids = []
                      }
                      if (checked) {
                        if (!formData.mcp_server_ids.includes(server.id)) {
                          formData.mcp_server_ids.push(server.id)
                        }
                      } else {
                        const index = formData.mcp_server_ids.indexOf(server.id)
                        if (index > -1) {
                          formData.mcp_server_ids.splice(index, 1)
                        }
                      }
                    }"
                    :disabled="saveLoading"
                    class="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
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

            <!-- No available tools tip -->
            <div v-if="formData.enable_agent && !availableTools?.local_tools?.length && !availableTools?.mcp_servers?.length" class="text-sm text-muted-foreground p-4 bg-muted rounded-md">
              {{ t('admin.pages.assistants.create.agentConfig.noTools') }}
            </div>
          </div>
        </form>
      </CardContent>
    </Card>

    <!-- Knowledge base config -->
    <KnowledgeBaseConfig
      v-if="assistant"
      v-model="knowledgeBaseConfig"
      :disabled="saveLoading"
      class="max-w-4xl"
    />

    <!-- Action buttons -->
    <Card v-if="assistant" class="max-w-4xl">
      <CardContent class="pt-6">
        <div class="flex justify-end gap-3">
          <Button variant="outline" @click="handleCancel" :disabled="saveLoading">
            <X class="h-4 w-4 mr-2" />
            {{ t('admin.cancel') }}
          </Button>
          <Button @click="updateAssistant" :disabled="saveLoading">
            <Save class="h-4 w-4 mr-2" />
            {{ t('admin.save') }}
          </Button>
        </div>
      </CardContent>
    </Card>

    <!-- Metadata info -->
    <Card v-if="assistant" class="max-w-4xl">
      <CardHeader>
        <CardTitle class="text-lg">{{ t('admin.pages.assistants.edit.metadata.title') }}</CardTitle>
      </CardHeader>
      <CardContent class="grid grid-cols-2 gap-4 text-sm">
        <div>
          <div class="text-muted-foreground">{{ t('admin.pages.assistants.edit.metadata.id') }}</div>
          <div class="font-mono">{{ assistant.id }}</div>
        </div>
        <div>
          <div class="text-muted-foreground">{{ t('admin.pages.assistants.edit.metadata.createdAt') }}</div>
          <div>{{ new Date(assistant.created_at).toLocaleString() }}</div>
        </div>
        <div>
          <div class="text-muted-foreground">{{ t('admin.pages.assistants.edit.metadata.updatedAt') }}</div>
          <div>{{ new Date(assistant.updated_at).toLocaleString() }}</div>
        </div>
        <div>
          <div class="text-muted-foreground">{{ t('admin.pages.assistants.edit.metadata.owner') }}</div>
          <div>{{ assistant.owner_id || t('admin.pages.assistants.edit.metadata.system') }}</div>
        </div>
      </CardContent>
    </Card>

    <!-- Tips/info -->
    <Card class="max-w-4xl">
      <CardHeader>
        <CardTitle class="text-lg">{{ t('admin.pages.assistants.edit.tips.title') }}</CardTitle>
      </CardHeader>
      <CardContent class="space-y-3 text-sm text-muted-foreground">
        <div>
          <strong>{{ t('admin.pages.assistants.edit.tips.warning') }}</strong>
        </div>
        <div>
          <strong>{{ t('admin.pages.assistants.edit.tips.status') }}</strong>
          <ul class="ml-4 mt-1 space-y-1">
            <li>• <strong>{{ t('admin.pages.assistants.edit.tips.statusList.active') }}</strong></li>
            <li>• <strong>{{ t('admin.pages.assistants.edit.tips.statusList.inactive') }}</strong></li>
            <li>• <strong>{{ t('admin.pages.assistants.edit.tips.statusList.draft') }}</strong></li>
          </ul>
        </div>
        <div>
          <strong>{{ t('admin.pages.assistants.edit.tips.security') }}</strong>
        </div>
      </CardContent>
    </Card>
  </div>
</template>