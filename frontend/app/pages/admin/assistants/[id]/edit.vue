<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, Trash2, AudioWaveform } from 'lucide-vue-next'
import { Button } from '~/components/ui/button'
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
import AssistantForm from '~/components/assistants/AssistantForm.vue'
import type { Assistant } from '~/types/api'

const { t } = useI18n()

// Page metadata
definePageMeta({
  breadcrumb: 'admin.pages.assistants.edit.breadcrumb',
  layout: 'admin'
})

const router = useRouter()
const route = useRoute()
const assistantId = route.params.id as string

// State management
const loading = ref(false)
const saveLoading = ref(false)
const deleteLoading = ref(false)
const assistant = ref<Assistant | null>(null)

// Load assistant data
const loadAssistant = async () => {
  loading.value = true
  try {
    const { $api } = useNuxtApp()
    const response = await $api(`/v1/admin/assistants/${assistantId}`) as any
    assistant.value = response
  } catch (error) {
    console.error('Failed to load assistant data:', error)
    toast.error(t('admin.pages.assistants.edit.loadFailed'))
    router.push('/admin/assistants')
  } finally {
    loading.value = false
  }
}

// Update assistant
const updateAssistant = async (data: Partial<Assistant>) => {
  saveLoading.value = true
  try {
    const { $api } = useNuxtApp()
    
    await $api(`/v1/admin/assistants/${assistantId}`, {
      method: 'PUT',
      body: data
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

      <div class="flex items-center gap-2">
        <Button variant="outline" @click="router.push(`/admin/assistants/${assistantId}/integrations`)">
            <AudioWaveform class="h-4 w-4 mr-2"/>
            Integrations
        </Button>

        <!-- Delete button -->
        <AlertDialog>
        <AlertDialogTrigger as-child>
          <Button variant="destructive" :disabled="loading">
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
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
    </div>

    <!-- Form -->
    <AssistantForm
      v-else-if="assistant"
      :initial-data="assistant"
      :is-admin="true"
      :loading="saveLoading"
      @submit="updateAssistant"
      @cancel="handleCancel"
    />
  </div>
</template>
