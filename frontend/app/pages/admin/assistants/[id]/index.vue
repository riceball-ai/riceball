<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, Save, Trash2 } from 'lucide-vue-next'
import { Button } from '~/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '~/components/ui/tabs'
import { Card, CardContent } from '~/components/ui/card'
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
import BasicInfo from '~/components/assistants/form/BasicInfo.vue'
import ModelSettings from '~/components/assistants/form/ModelSettings.vue'
import ReviewDeployForm from '~/components/assistants/form/ReviewDeployForm.vue'
import KnowledgeBaseConfig from '~/components/admin/KnowledgeBaseConfig.vue'
import AgentConfig from '~/components/admin/AgentConfig.vue'
import TranslationManager from '~/components/assistants/form/TranslationManager.vue'
import RetrievalTester from '~/components/assistants/form/RetrievalTester.vue'
import type { Assistant, Model, RagConfig } from '~/types/api'
import { useConfigStore } from '~/stores/config'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const configStore = useConfigStore()
const assistantId = route.params.id as string

// Page metadata
definePageMeta({
  breadcrumb: 'admin.pages.assistants.edit.breadcrumb',
  layout: 'admin'
})

// State
const loading = ref(false)
const saveLoading = ref(false)
const deleteLoading = ref(false)
const enableCategories = ref(false)
const activeTab = ref('general')

// Data
const formData = ref<Partial<Assistant>>({})
const originalData = ref<Assistant | null>(null)

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

// Fetch options
const { data: models } = useAPI<Model[]>('/v1/admin/all-models?capabilities=chat', { server: false })
const modelOptions = computed(() => {
  return (models.value ?? []).map(m => ({ 
    label: m.display_name, 
    value: m.id
  }))
})

// Validation
const errors = ref<Record<string, string>>({})

// Load data
onMounted(async () => {
  const config = await configStore.getConfig()
  enableCategories.value = String(config.enable_assistant_categories).toLowerCase() !== 'false'
  
  loadAssistant()
})

const loadAssistant = async () => {
  loading.value = true
  try {
    const { $api } = useNuxtApp()
    const response = await $api<Assistant>(`/v1/admin/assistants/${assistantId}`)
    originalData.value = response
    formData.value = JSON.parse(JSON.stringify(response))
  } catch (error) {
    console.error('Failed to load assistant:', error)
    toast.error(t('admin.pages.assistants.edit.loadFailed'))
    router.push('/admin/assistants')
  } finally {
    loading.value = false
  }
}

// Actions
const handleSave = async () => {
  // Validate basic info
  if (!formData.value.name || formData.value.name.length < 2) {
    errors.value.name = t('admin.pages.assistants.create.validation.nameMin')
    activeTab.value = 'general'
    return
  }
  if (!formData.value.system_prompt) {
    errors.value.system_prompt = t('admin.pages.assistants.create.validation.systemPromptMin')
    activeTab.value = 'model'
    return
  }

  saveLoading.value = true
  try {
    const { $api } = useNuxtApp()
    await $api(`/v1/admin/assistants/${assistantId}`, {
      method: 'PUT',
      body: formData.value
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

const handleDelete = async () => {
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
</script>

<template>
  <div class="space-y-6 pb-10">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-4">
        <Button variant="ghost" size="icon" @click="router.push('/admin/assistants')">
          <ArrowLeft class="w-5 h-5" />
        </Button>
        <div>
          <h1 class="text-2xl font-bold tracking-tight">{{ t('admin.pages.assistants.edit.title') }}</h1>
          <p class="text-muted-foreground">{{ formData.name || '...' }}</p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <AlertDialog>
          <AlertDialogTrigger as-child>
            <Button variant="destructive" :disabled="deleteLoading || saveLoading">
              <Trash2 class="w-4 h-4 mr-2" />
              {{ t('common.delete') }}
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>{{ t('admin.pages.assistants.edit.deleteTitle') }}</AlertDialogTitle>
              <AlertDialogDescription>
                {{ t('admin.pages.assistants.edit.deleteDescription') }}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>{{ t('common.cancel') }}</AlertDialogCancel>
              <AlertDialogAction @click="handleDelete" class="bg-destructive text-destructive-foreground hover:bg-destructive/90">
                {{ t('common.confirmDelete') }}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
        
        <Button @click="handleSave" :disabled="saveLoading || deleteLoading || loading">
          <Save class="w-4 h-4 mr-2" />
          {{ t('common.save') }}
        </Button>
      </div>
    </div>

    <Tabs v-model="activeTab" class="space-y-4">
      <TabsList>
        <TabsTrigger value="general">{{ t('assistantForm.basicInfo') }}</TabsTrigger>
        <TabsTrigger value="model">{{ t('assistantForm.modelConfig') }}</TabsTrigger>
        <TabsTrigger value="knowledge">{{ t('admin.knowledgeBase.title') }}</TabsTrigger>
        <TabsTrigger value="retrieval">{{ t('assistants.retrievalTest.title') }}</TabsTrigger>
        <TabsTrigger value="agent">{{ t('admin.agent.title') }}</TabsTrigger>
        <TabsTrigger value="translations">{{ t('admin.pages.assistants.translations.title') }}</TabsTrigger>
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

      <TabsContent value="retrieval">
        <RetrievalTester :assistant-id="assistantId" />
      </TabsContent>

      <TabsContent value="agent">
        <AgentConfig
          v-model="agentData"
          :disabled="loading"
        />
      </TabsContent>

      <TabsContent value="translations">
        <TranslationManager :assistant-id="assistantId" />
      </TabsContent>
    </Tabs>
  </div>
</template>
