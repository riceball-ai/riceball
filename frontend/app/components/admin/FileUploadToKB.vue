<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { Upload, Trash2 } from 'lucide-vue-next'
import { Button } from '~/components/ui/button'
import { Label } from '~/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '~/components/ui/select'
import { toast } from 'vue-sonner'
import type { KnowledgeBase, FileUploadResponse } from '~/types/api'

const { $api } = useNuxtApp()
const { t } = useI18n()

interface UploadProgress {
  fileName: string
  progress: number
  status: 'uploading' | 'processing' | 'completed' | 'failed'
}

interface Props {
  defaultKnowledgeBaseId?: string
}

const props = withDefaults(defineProps<Props>(), {
  defaultKnowledgeBaseId: ''
})

const emit = defineEmits<{
  'upload-complete': []
}>()

// State
const selectedKbId = ref(props.defaultKnowledgeBaseId)
const selectedFiles = ref<File[]>([])
const uploading = ref(false)
const uploadProgress = ref<UploadProgress[]>([])
const knowledgeBases = ref<KnowledgeBase[]>([])
const fileInput = ref<HTMLInputElement>()

// Watch props changes
watch(() => props.defaultKnowledgeBaseId, (newId) => {
  selectedKbId.value = newId
}, { immediate: true })

// File selection
const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files) {
    const newFiles = Array.from(target.files)
    selectedFiles.value.push(...newFiles)
  }
}

// Remove file
const removeFile = (index: number) => {
  selectedFiles.value.splice(index, 1)
}

// Load knowledge base list
const loadKnowledgeBases = async () => {
  try {
    const response = await $api('/v1/admin/rag/knowledge-bases') as any
    knowledgeBases.value = response.items || response || []
  } catch (error) {
    console.error('Failed to load knowledge base list:', error)
    toast.error(t('components.fileUpload.loadKnowledgeBasesFailed'))
  }
}

// Upload files
const uploadFiles = async () => {
  if (!selectedKbId.value || selectedFiles.value.length === 0) {
    toast.error(t('components.fileUpload.selectKnowledgeBaseAndFiles'))
    return
  }

  uploading.value = true
  uploadProgress.value = selectedFiles.value.map(file => ({
    fileName: file.name,
    progress: 0,
    status: 'uploading' as const
  }))

  try {
    const { $api } = useNuxtApp()

    for (let i = 0; i < selectedFiles.value.length; i++) {
      const file = selectedFiles.value[i]
      const progressItem = uploadProgress.value[i]

      if (!file || !progressItem) continue

      try {
        // 1. Upload file
        progressItem.status = 'uploading'
        progressItem.progress = 0

        const formData = new FormData()
        formData.append('file', file)
        formData.append('file_type', 'document')

        const uploadResponse: any = await $api('/v1/files/upload', {
          method: 'POST',
          body: formData
        })

        progressItem.progress = 50
        progressItem.status = 'processing'

        // 2. Add to knowledge base
        await $api('/v1/admin/rag/documents/from-file', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            file_path: uploadResponse.file_path,
            knowledge_base_id: selectedKbId.value,
            title: file.name
          })
        })

        progressItem.progress = 100
        progressItem.status = 'completed'

      } catch (error) {
        console.error(`Failed to upload file ${file.name}:`, error)
        progressItem.status = 'failed'
        toast.error(t('components.fileUpload.uploadFileFailed', { name: file.name }))
      }
    }

    // Check if there are successfully uploaded files
    const successCount = uploadProgress.value.filter(p => p.status === 'completed').length
    if (successCount > 0) {
      toast.success(t('components.fileUpload.uploadSuccess', { count: successCount }))
      emit('upload-complete')
      
      // Clear state
      selectedFiles.value = []
      uploadProgress.value = []
    }

  } finally {
    uploading.value = false
  }
}

onMounted(() => {
  loadKnowledgeBases()
})
</script>

<template>
  <div class="space-y-4">
    <div>
      <Label for="kb-select">{{ t('components.fileUpload.selectKnowledgeBase') }}</Label>
      <Select v-model="selectedKbId" required>
        <SelectTrigger>
          <SelectValue :placeholder="t('components.fileUpload.selectKnowledgeBasePlaceholder')" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem
            v-for="kb in knowledgeBases"
            :key="kb.id"
            :value="kb.id"
          >
            {{ kb.name }}
          </SelectItem>
        </SelectContent>
      </Select>
    </div>

    <div>
      <Label for="file-upload">{{ t('components.fileUpload.uploadFiles') }}</Label>
      <div class="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
        <input
          ref="fileInput"
          type="file"
          multiple
          accept=".pdf,.txt,.md,.docx,.doc,.pptx,.xlsx,.xls"
          class="hidden"
          @change="handleFileSelect"
        />
        <div v-if="selectedFiles.length === 0">
          <Upload class="mx-auto h-12 w-12 text-gray-400" />
          <div class="mt-4">
            <Button
              variant="outline"
              @click="fileInput?.click()"
            >
              {{ t('components.fileUpload.selectFiles') }}
            </Button>
            <p class="mt-2 text-sm text-gray-500">
              {{ t('components.fileUpload.supportedFormats') }}
            </p>
          </div>
        </div>
        <div v-else>
          <div class="space-y-2">
            <div
              v-for="(file, index) in selectedFiles"
              :key="index"
              class="flex items-center justify-between p-2 bg-gray-50 rounded"
            >
              <span class="text-sm">{{ file.name }}</span>
              <Button
                variant="ghost"
                size="sm"
                @click="removeFile(index)"
              >
                <Trash2 class="h-4 w-4" />
              </Button>
            </div>
          </div>
          <div class="mt-4 space-x-2">
            <Button
              variant="outline"
              @click="fileInput?.click()"
            >
              {{ t('components.fileUpload.addMore') }}
            </Button>
            <Button
              @click="uploadFiles"
              :disabled="!selectedKbId || uploading"
            >
              <Upload class="h-4 w-4 mr-2" v-if="!uploading" />
              <div class="h-4 w-4 mr-2 animate-spin rounded-full border-2 border-current border-t-transparent" v-else />
              {{ uploading ? t('components.fileUpload.uploading') : t('components.fileUpload.startUpload') }}
            </Button>
          </div>
        </div>
      </div>
    </div>

    <!-- Upload progress -->
    <div v-if="uploadProgress.length > 0" class="space-y-2">
      <h4 class="font-medium">{{ t('components.fileUpload.uploadProgress') }}</h4>
      <div
        v-for="progress in uploadProgress"
        :key="progress.fileName"
        class="space-y-1"
      >
        <div class="flex justify-between text-sm">
          <span>{{ progress.fileName }}</span>
          <span>{{ progress.status }}</span>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-2">
          <div
            class="bg-blue-600 h-2 rounded-full transition-all duration-300"
            :style="{ width: `${progress.progress}%` }"
          />
        </div>
      </div>
    </div>
  </div>
</template>
