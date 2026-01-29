<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { Save, X, ArrowLeft } from 'lucide-vue-next'
import { Button } from '~/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '~/components/ui/tabs'
import { Card, CardContent } from '~/components/ui/card'
import BasicInfo from '~/components/assistants/form/BasicInfo.vue'
import ModelSettings from '~/components/assistants/form/ModelSettings.vue'
import ReviewDeployForm from '~/components/assistants/form/ReviewDeployForm.vue'
import KnowledgeBaseConfig from '~/components/admin/KnowledgeBaseConfig.vue'
import AgentConfig from '~/components/admin/AgentConfig.vue'
import type { Assistant, Model } from '~/types/api'
import { useConfigStore } from '~/stores/config'

const { t } = useI18n()

// Page metadata
definePageMeta({
  breadcrumb: 'admin.pages.assistants.create.breadcrumb',
  layout: 'admin'
})

const router = useRouter()
const configStore = useConfigStore()
const loading = ref(false)
const enableCategories = ref(false)
const activeTab = ref('general')

// Computed for sub-components
const knowledgeBaseData = computed({
  get: () => ({
    knowledge_base_ids: formData.value.knowledge_base_ids || [],
    rag_config: formData.value.rag_config
  }),
  set: (val) => {
    formData.value.knowledge_base_ids = val.knowledge_base_ids
    formData.value.rag_config = val.rag_config
  }
})

const agentData = computed({
  get: () => ({
    enable_agent: !!formData.value.enable_agent,
    agent_max_iterations: formData.value.agent_max_iterations || 5,
    agent_enabled_tools: formData.value.agent_enabled_tools || [],
    mcp_server_ids: formData.value.mcp_server_ids || []
  }),
  set: (val) => {
    formData.value.enable_agent = val.enable_agent
    formData.value.agent_max_iterations = val.agent_max_iterations
    formData.value.agent_enabled_tools = val.agent_enabled_tools
    formData.value.mcp_server_ids = val.mcp_server_ids
  }
})

onMounted(async () => {
  const config = await configStore.getConfig()
  const val = config.enable_assistant_categories
  enableCategories.value = String(val).toLowerCase() !== 'false'
})

// Fetch model list
const { data: models } = useAPI<Model[]>('/v1/admin/all-models?capabilities=chat', { server: false })

const modelOptions = computed(() => {
  const list = models.value ?? []
  return list.map(m => ({ 
    label: m.display_name, 
    value: m.id 
  }))
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
  status: 'DRAFT',
  category: 'general',
  tags: [],
  // Defaults for simple create
  enable_agent: false,
  knowledge_base_ids: [],
})

// Validation
const errors = ref<Record<string, string>>({})

const validateForm = (): boolean => {
  const newErrors: Record<string, string> = {}
  
  if (!formData.value.name || formData.value.name.length < 2) {
    newErrors.name = t('admin.pages.assistants.create.validation.nameMin')
    activeTab.value = 'general'
  }
  
  if (!formData.value.system_prompt || formData.value.system_prompt.length < 10) {
    newErrors.system_prompt = t('admin.pages.assistants.create.validation.systemPromptMin')
    activeTab.value = 'model'
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

// Actions
const handleCancel = () => {
  router.push('/admin/assistants')
}

const handleSubmit = async () => {
  if (!validateForm()) return

  loading.value = true
  try {
    const { $api } = useNuxtApp()
    
    // Create
    const result = await $api<Assistant>('/v1/admin/assistants', {
      method: 'POST',
      body: formData.value
    })
    
    toast.success(t('admin.pages.assistants.create.createSuccess'))
    
    // Auto-redirect to edit page for advanced config (Agent/RAG)
    router.push(`/admin/assistants/${result.id}`)
    
  } catch (error) {
    console.error('Create failed:', error)
    toast.error(t('admin.pages.assistants.create.createFailed'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="space-y-6 pb-10">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-4">
        <Button variant="ghost" size="icon" @click="handleCancel">
          <ArrowLeft class="w-5 h-5" />
        </Button>
        <div>
          <h1 class="text-2xl font-bold tracking-tight">{{ t('admin.pages.assistants.create.title') }}</h1>
          <p class="text-muted-foreground">{{ t('admin.pages.assistants.create.subtitle') }}</p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <Button variant="outline" @click="handleCancel" :disabled="loading">
          <X class="w-4 h-4 mr-2" />
          {{ t('common.cancel') }}
        </Button>
        <Button @click="handleSubmit" :disabled="loading">
          <Save class="w-4 h-4 mr-2" />
          {{ t('admin.pages.assistants.create.createButton') }}
        </Button>
      </div>
    </div>

    <Tabs v-model="activeTab" class="space-y-4">
      <TabsList>
        <TabsTrigger value="general">{{ t('assistantForm.basicInfo') }}</TabsTrigger>
        <TabsTrigger value="model">{{ t('assistantForm.modelConfig') }}</TabsTrigger>
        <TabsTrigger value="knowledge">{{ t('admin.knowledgeBase.title') }}</TabsTrigger>
        <TabsTrigger value="agent">{{ t('admin.agent.title') }}</TabsTrigger>
      </TabsList>

      <TabsContent value="general" class="space-y-6">
        <BasicInfo
          v-model="formData"
          :enable-categories="enableCategories"
          :loading="loading"
          :errors="errors"
        />
        <ReviewDeployForm
          v-model="formData"
          :is-admin="true"
          :loading="loading"
          :errors="errors"
        />
      </TabsContent>

      <TabsContent value="model">
        <ModelSettings
          v-model="formData"
          :model-options="modelOptions"
          :loading="loading"
          :errors="errors"
        />
      </TabsContent>

      <TabsContent value="knowledge">
         <KnowledgeBaseConfig
           v-model="knowledgeBaseData"
           :disabled="loading"
         />
      </TabsContent>

      <TabsContent value="agent">
        <AgentConfig
          v-model="agentData"
          :disabled="loading"
        />
      </TabsContent>
    </Tabs>
  </div>
</template>
