<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { Save, X } from 'lucide-vue-next'
import { Button } from '~/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '~/components/ui/card'
import { Input } from '~/components/ui/input'
import { Label } from '~/components/ui/label'
import { Textarea } from '~/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '~/components/ui/select'
import { Switch } from '~/components/ui/switch'
import KnowledgeBaseConfig from '~/components/admin/KnowledgeBaseConfig.vue'
import AgentConfig from '~/components/admin/AgentConfig.vue'
import AvatarUpload from '~/components/AvatarUpload.vue'
import type { Assistant, Model, RagConfig, AvailableAgentTools } from '~/types/api'
import { ASSISTANT_CATEGORIES } from '~/constants/assistants'
import { useConfigStore } from '~/stores/config'

const props = withDefaults(defineProps<{
  initialData?: Partial<Assistant>
  isAdmin?: boolean
  loading?: boolean
  submitLabel?: string
}>(), {
  isAdmin: false,
  loading: false
})

const emit = defineEmits<{
  (e: 'submit', data: Partial<Assistant>): void
  (e: 'cancel'): void
}>()

const { t } = useI18n()

// Config
const configStore = useConfigStore()
const enableCategories = ref(false)

onMounted(async () => {
  const config = await configStore.getConfig()
  const val = config.enable_assistant_categories
  enableCategories.value = String(val).toLowerCase() !== 'false'
})

// Fetch model list
const modelEndpoint = props.isAdmin ? '/v1/admin/all-models?capabilities=chat' : '/v1/models'
const { data: models } = useAPI<Model[]>(modelEndpoint, { server: false })

const modelOptions = computed(() => {
  const list = models.value ?? []
  // For non-admin, filter active models
  const filtered = props.isAdmin ? list : list.filter(m => m.status === 'ACTIVE')
  return filtered.map(m => ({ label: m.display_name, value: m.id }))
})

// Fetch available Agent tools (Admin only)
// Moved to AgentConfig component

// Max history toggle state
const enableMaxHistory = ref(false)

// Watch enableMaxHistory to update formData
watch(enableMaxHistory, (enabled) => {
  if (enabled) {
    if (formData.value.max_history_messages === undefined || formData.value.max_history_messages === null) {
      formData.value.max_history_messages = 10
    }
  } else {
    formData.value.max_history_messages = null
  }
})

// Form data
const formData = ref<Partial<Assistant>>({
  name: '',
  avatar_file_path: '',
  description: '',
  system_prompt: '',
  model_id: '',
  temperature: 0.7,
  max_history_messages: null,
  is_public: false,
  status: props.isAdmin ? 'DRAFT' : 'ACTIVE',
  category: 'general',
  tags: [],
  enable_agent: false,
  agent_max_iterations: 5,
  agent_enabled_tools: [],
  mcp_server_ids: [],
  knowledge_base_ids: [],
  rag_config: undefined
})

// Agent config state
const agentConfig = ref({
  enable_agent: false,
  agent_max_iterations: 5,
  agent_enabled_tools: [] as string[],
  mcp_server_ids: [] as string[]
})

// Watch agent config changes
watch(agentConfig, (newConfig) => {
  formData.value.enable_agent = newConfig.enable_agent
  formData.value.agent_max_iterations = newConfig.agent_max_iterations
  formData.value.agent_enabled_tools = newConfig.agent_enabled_tools
  formData.value.mcp_server_ids = newConfig.mcp_server_ids
}, { deep: true })

// Knowledge base config state
const knowledgeBaseConfig = ref<{
  knowledge_base_ids: string[]
  rag_config?: RagConfig
}>({
  knowledge_base_ids: [],
  rag_config: undefined
})

// Watch knowledge base config changes
watch(knowledgeBaseConfig, (newConfig) => {
  formData.value.knowledge_base_ids = newConfig.knowledge_base_ids
  formData.value.rag_config = newConfig.rag_config
}, { deep: true })

// Initialize form data from props
watch(() => props.initialData, (newData) => {
  if (newData) {
    // Determine if max history is enabled
    const hasMaxHistory = newData.max_history_messages !== null && newData.max_history_messages !== undefined
    enableMaxHistory.value = hasMaxHistory

    formData.value = {
      ...formData.value,
      ...newData,
      // Ensure correct types
      temperature: newData.temperature !== undefined ? Number(newData.temperature) : 0.7,
      max_history_messages: hasMaxHistory ? Number(newData.max_history_messages) : null,
      tags: newData.tags || [],
      knowledge_base_ids: newData.knowledge_base_ids || [],
      mcp_server_ids: newData.mcp_server_ids || [],
      agent_enabled_tools: newData.agent_enabled_tools || []
    }
    
    // Sync knowledge base config
    const hasKnowledgeBases = newData.knowledge_base_ids && newData.knowledge_base_ids.length > 0
    knowledgeBaseConfig.value = {
      knowledge_base_ids: newData.knowledge_base_ids || [],
      rag_config: hasKnowledgeBases ? newData.rag_config : undefined
    }

    // Sync agent config
    agentConfig.value.enable_agent = !!newData.enable_agent
    agentConfig.value.agent_max_iterations = newData.agent_max_iterations || 5
    agentConfig.value.agent_enabled_tools = newData.agent_enabled_tools || []
    agentConfig.value.mcp_server_ids = newData.mcp_server_ids || []
  }
}, { immediate: true, deep: true })

// Tag input handling
const tagsInput = computed({
  get: () => formData.value.tags?.join(', ') || '',
  set: (val: string) => {
    formData.value.tags = val.split(/[,，]/).map(t => t.trim()).filter(Boolean)
  }
})

// Form validation errors
const errors = ref<Record<string, string>>({})

// Form validation
const validateForm = (): boolean => {
  const newErrors: Record<string, string> = {}
  
  if (!formData.value.name || formData.value.name.length < 2) {
    newErrors.name = props.isAdmin 
      ? t('admin.pages.assistants.create.validation.nameMin')
      : t('assistantForm.nameError')
  }
  
  if (!formData.value.system_prompt || formData.value.system_prompt.length < 10) {
    newErrors.system_prompt = props.isAdmin
      ? t('admin.pages.assistants.create.validation.systemPromptMin')
      : t('assistantForm.systemPromptError')
  }
  
  if (!formData.value.model_id) {
    newErrors.model_id = props.isAdmin
      ? t('admin.pages.assistants.create.validation.modelRequired')
      : t('assistantForm.modelError')
  }
  
  if (props.isAdmin && !formData.value.status) {
    newErrors.status = t('admin.pages.assistants.create.validation.statusRequired')
  }
  
  errors.value = newErrors
  return Object.keys(newErrors).length === 0
}

const handleSubmit = () => {
  if (!validateForm()) return
  emit('submit', formData.value)
}
</script>

<template>
  <div class="space-y-6">
    <Card class="max-w-4xl">
      <CardHeader>
        <CardTitle>{{ t('assistantForm.basicInfo') }}</CardTitle>
      </CardHeader>
      <CardContent>
        <form @submit.prevent="handleSubmit" class="space-y-6">
          <!-- Basic Info -->
          <div class="grid gap-6">
            <!-- Avatar -->
            <div class="space-y-2">
              <Label>{{ t('assistantForm.avatar') }}</Label>
              <AvatarUpload
                id="avatar"
                v-model="formData.avatar_file_path"
                :disabled="loading"
              />
              <div class="text-sm text-muted-foreground">
                {{ t('assistantForm.avatarHelp') }}
              </div>
            </div>

            <!-- Name -->
            <div class="space-y-2">
              <Label for="name">
                {{ t('assistantForm.name') }} <span class="text-destructive">*</span>
              </Label>
              <Input
                id="name"
                v-model="formData.name"
                :placeholder="t('assistantForm.namePlaceholder')"
                :class="{ 'border-destructive': errors.name }"
                :disabled="loading"
              />
              <div v-if="errors.name" class="text-sm text-destructive">
                {{ errors.name }}
              </div>
            </div>

            <!-- Description -->
            <div class="space-y-2">
              <Label for="description">{{ t('assistantForm.description') }}</Label>
              <Textarea
                id="description"
                v-model="formData.description"
                :placeholder="t('assistantForm.descriptionPlaceholder')"
                :rows="3"
                :disabled="loading"
              />
            </div>

            <!-- Category -->
            <div class="space-y-2" v-if="enableCategories">
              <Label for="category">{{ t('assistantForm.category') }}</Label>
              <Select v-model="formData.category" :disabled="loading">
                <SelectTrigger>
                  <SelectValue :placeholder="t('assistantForm.categoryPlaceholder')" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem
                    v-for="category in ASSISTANT_CATEGORIES"
                    :key="category.value"
                    :value="category.value"
                  >
                    {{ t(`assistants.categories.${category.value}`) }}
                  </SelectItem>
                </SelectContent>
              </Select>
              <div class="text-sm text-muted-foreground">
                {{ t('assistantForm.categoryHelp') }}
              </div>
            </div>

            <!-- Tags -->
            <div class="space-y-2">
              <Label for="tags">{{ t('assistantForm.tags') }}</Label>
              <Input
                id="tags"
                v-model="tagsInput"
                :placeholder="t('assistantForm.tagsPlaceholder')"
                :disabled="loading"
              />
              <div class="text-sm text-muted-foreground">
                {{ t('assistantForm.tagsHelp') }}
              </div>
            </div>
          </div>

          <!-- Model Config -->
          <div class="space-y-4 pt-4 border-t">
            <h3 class="text-lg font-medium">{{ t('assistantForm.modelConfig') }}</h3>

            <!-- System Prompt -->
            <div class="space-y-2">
              <Label for="system_prompt">
                {{ t('assistantForm.systemPrompt') }} <span class="text-destructive">*</span>
              </Label>
              <Textarea
                id="system_prompt"
                v-model="formData.system_prompt"
                :placeholder="t('assistantForm.systemPromptPlaceholder')"
                :rows="5"
                :class="{ 'border-destructive': errors.system_prompt }"
                :disabled="loading"
              />
              <div v-if="errors.system_prompt" class="text-sm text-destructive">
                {{ errors.system_prompt }}
              </div>
              <div class="text-sm text-muted-foreground">
                {{ t('assistantForm.systemPromptHelp') }}
              </div>
            </div>

            <!-- Model Selection -->
            <div class="space-y-2">
              <Label for="model_id">
                {{ t('assistantForm.model') }} <span class="text-destructive">*</span>
              </Label>
              <Select v-model="formData.model_id" :disabled="loading">
                <SelectTrigger :class="{ 'border-destructive': errors.model_id }">
                  <SelectValue :placeholder="t('assistantForm.modelPlaceholder')" />
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
                {{ t('assistantForm.modelHelp') }}
              </div>
            </div>

            <!-- Parameters -->
            <div class="grid grid-cols-2 gap-4">
              <div class="space-y-2">
                <Label for="temperature">{{ t('assistantForm.temperature') }}</Label>
                <Input
                  id="temperature"
                  v-model.number="formData.temperature"
                  type="number"
                  placeholder="0.7"
                  min="0"
                  max="2"
                  step="0.1"
                  :disabled="loading"
                />
                <div class="text-sm text-muted-foreground">
                  {{ t('assistantForm.temperatureHelp') }}
                </div>
              </div>
              <div class="space-y-2">
                <div class="flex items-center justify-between">
                  <Label for="max_history_messages">{{ t('assistantForm.maxHistory') }}</Label>
                  <Switch
                    v-model="enableMaxHistory"
                    @update:modelValue="(val) => enableMaxHistory = val"
                    :disabled="loading"
                  />
                </div>
                <div v-if="enableMaxHistory" class="pt-2">
                  <Input
                    id="max_history_messages"
                    :model-value="formData.max_history_messages ?? ''"
                    @update:model-value="(val) => formData.max_history_messages = (val === '' || val === null || val === undefined) ? null : Number(val)"
                    type="number"
                    placeholder="10"
                    min="0"
                    :disabled="loading"
                  />
                </div>
                <div class="text-sm text-muted-foreground">
                  {{ t('assistantForm.maxHistoryHelp') }}
                </div>
              </div>
            </div>
          </div>

          <!-- Publish Settings -->
          <div class="space-y-4 pt-4 border-t">
            <h3 class="text-lg font-medium">{{ t('assistantForm.publishSettings') }}</h3>
            
            <!-- Is Public -->
            <div class="flex items-center space-x-2">
              <input
                id="is_public"
                type="checkbox"
                v-model="formData.is_public"
                :disabled="loading"
                class="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
              />
              <Label for="is_public" class="text-sm cursor-pointer">
                {{ t('assistantForm.isPublic') }}
              </Label>
            </div>

            <!-- Status -->
            <div class="space-y-2">
              <Label for="status">
                {{ t('assistantForm.status') }} <span class="text-destructive">*</span>
              </Label>
              <Select v-model="formData.status" :disabled="loading">
                <SelectTrigger :class="{ 'border-destructive': errors.status }">
                  <SelectValue :placeholder="t('assistantForm.statusPlaceholder')" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ACTIVE">{{ t('assistantForm.statusActive') }}</SelectItem>
                  <SelectItem v-if="isAdmin" value="INACTIVE">{{ t('admin.pages.assistants.create.publishSettings.statuses.inactive') }}</SelectItem>
                  <SelectItem value="DRAFT">{{ t('assistantForm.statusDraft') }}</SelectItem>
                </SelectContent>
              </Select>
              <div v-if="errors.status" class="text-sm text-destructive">
                {{ errors.status }}
              </div>
            </div>
          </div>
        </form>
      </CardContent>
    </Card>

    <!-- Knowledge Base Config (Admin Only) -->
    <KnowledgeBaseConfig
      v-if="isAdmin"
      v-model="knowledgeBaseConfig"
      :disabled="loading"
      class="max-w-4xl"
    />

    <!-- Agent Config (Admin Only) -->
    <AgentConfig
      v-if="isAdmin"
      v-model="agentConfig"
      :disabled="loading"
      class="max-w-4xl"
    />

    <!-- Action Buttons -->
    <Card class="max-w-4xl">
      <CardContent class="pt-6">
        <div class="flex justify-end gap-3">
          <Button variant="outline" @click="emit('cancel')" :disabled="loading">
            <X class="h-4 w-4 mr-2" />
            {{ t('common.cancel') }}
          </Button>
          <Button @click="handleSubmit" :disabled="loading">
            <Save class="h-4 w-4 mr-2" />
            {{ submitLabel || (initialData ? t('common.save') : t('assistantForm.createButton')) }}
          </Button>
        </div>
      </CardContent>
    </Card>

    <!-- Tips (Admin Only) -->
    <Card v-if="isAdmin" class="max-w-4xl">
      <CardHeader>
        <CardTitle class="text-lg">{{ t('admin.pages.assistants.create.tips.title') }}</CardTitle>
      </CardHeader>
      <CardContent class="space-y-3 text-sm text-muted-foreground">
        <div>
          <strong>{{ t('admin.pages.assistants.create.tips.systemPromptTitle') }}</strong>{{ t('admin.pages.assistants.create.tips.systemPromptContent') }}
        </div>
        <div>
          <strong>{{ t('admin.pages.assistants.create.tips.modelSelectionTitle') }}</strong>{{ t('admin.pages.assistants.create.tips.modelSelectionContent') }}
        </div>
        <div>
          <strong>{{ t('admin.pages.assistants.create.tips.parameterTitle') }}</strong>
          <ul class="ml-4 mt-1 space-y-1">
            <li>• <strong>{{ t('admin.pages.assistants.create.tips.temperatureTitle') }}</strong>{{ t('admin.pages.assistants.create.tips.temperatureContent') }}</li>
            <li>• <strong>{{ t('admin.pages.assistants.create.tips.tokensTitle') }}</strong>{{ t('admin.pages.assistants.create.tips.tokensContent') }}</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
