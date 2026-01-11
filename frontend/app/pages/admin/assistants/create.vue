<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { Save, X } from 'lucide-vue-next'
import { Button } from '~/components/ui/button'
import { Card, CardContent } from '~/components/ui/card'
import BasicInfo from '~/components/assistants/form/BasicInfo.vue'
import ModelSettings from '~/components/assistants/form/ModelSettings.vue'
import ReviewDeployForm from '~/components/assistants/form/ReviewDeployForm.vue'
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

onMounted(async () => {
  const config = await configStore.getConfig()
  const val = config.enable_assistant_categories
  enableCategories.value = String(val).toLowerCase() !== 'false'
})

// Fetch model list
const { data: models } = useAPI<Model[]>('/v1/admin/all-models?capabilities=chat', { server: false })

const modelOptions = computed(() => {
  const list = models.value ?? []
  return list.map(m => ({ label: m.display_name, value: m.id }))
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
  }
  
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
  <div class="space-y-6 max-w-4xl mx-auto pb-10">
    <div class="flex flex-col gap-2">
      <h1 class="text-2xl font-bold tracking-tight">{{ t('admin.pages.assistants.create.title') }}</h1>
      <p class="text-muted-foreground">{{ t('admin.pages.assistants.create.subtitle') }}</p>
    </div>

    <!-- Basic Info -->
    <BasicInfo
      v-model="formData"
      :enable-categories="enableCategories"
      :errors="errors"
      :loading="loading"
    />

    <!-- Model Settings -->
    <ModelSettings
      v-model="formData"
      :model-options="modelOptions"
      :errors="errors"
      :loading="loading"
    />

    <!-- Publish Settings -->
    <ReviewDeployForm
      v-model="formData"
      :is-admin="true"
      :errors="errors"
      :loading="loading"
    />

    <!-- Actions -->
    <Card>
      <CardContent class="pt-6">
        <div class="flex justify-end gap-3">
          <Button variant="outline" @click="handleCancel" :disabled="loading">
            <X class="h-4 w-4 mr-2" />
            {{ t('common.cancel') }}
          </Button>
          <Button @click="handleSubmit" :disabled="loading">
            <Save class="h-4 w-4 mr-2" />
            {{ t('common.saveAndContinue') }}
          </Button>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
