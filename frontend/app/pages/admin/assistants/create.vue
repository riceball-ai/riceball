<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import AssistantForm from '~/components/assistants/AssistantForm.vue'
import type { Assistant } from '~/types/api'

const { t } = useI18n()

// Page metadata
definePageMeta({
  breadcrumb: 'admin.pages.assistants.create.breadcrumb',
  layout: 'admin'
})

const router = useRouter()
const loading = ref(false)

// Create assistant
const createAssistant = async (data: Partial<Assistant>) => {
  loading.value = true
  try {
    const { $api } = useNuxtApp()
    
    await $api('/v1/admin/assistants', {
      method: 'POST',
      body: data
    })
    
    toast.success(t('admin.pages.assistants.create.createSuccess'))
    router.push('/admin/assistants')
    
  } catch (error) {
    console.error('Create failed:', error)
    toast.error(t('admin.pages.assistants.create.createFailed'))
  } finally {
    loading.value = false
  }
}

// Cancel action
const handleCancel = () => {
  router.push('/admin/assistants')
}
</script>

<template>
  <div class="space-y-6">
    <AssistantForm
      :is-admin="true"
      :loading="loading"
      @submit="createAssistant"
      @cancel="handleCancel"
    />
  </div>
</template>
