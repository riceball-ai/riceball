<template>
  <div class="space-y-4">
    <!-- Upload area -->
    <div
      @click="triggerFileInput"
      @dragover.prevent
      @drop.prevent="handleDrop"
      class="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center cursor-pointer transition-colors hover:border-gray-400"
      :class="{
        'border-red-500': error,
        'border-blue-500': isDragging,
        'opacity-50 cursor-not-allowed': disabled
      }"
    >
      <input
        ref="fileInput"
        type="file"
        accept="image/*"
        class="hidden"
        @change="handleFileSelect"
        :disabled="disabled"
      />
      
      <div v-if="!previewUrl" class="space-y-2">
        <ImageIcon class="mx-auto h-12 w-12 text-gray-400" />
        <div class="text-sm text-gray-600">
          <span class="font-medium">{{ $t('components.imageUpload.clickToUpload') }}</span>
          {{ $t('components.imageUpload.orDrag') }}
        </div>
        <div class="text-xs text-gray-500">
          {{ $t('components.imageUpload.supportedFormats') }}
        </div>
      </div>
      
      <!-- Preview area -->
      <div v-else class="space-y-2">
        <div class="relative inline-block">
          <img
            :src="previewUrl"
            :alt="$t('components.imageUpload.previewAlt')"
            class="max-w-full max-h-48 rounded-lg shadow-sm"
          />
          <button
            v-if="!disabled"
            @click.stop="removeImage"
            class="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 hover:bg-red-600 transition-colors"
          >
            <X class="h-4 w-4" />
          </button>
        </div>
        <div class="text-sm text-gray-600">
          {{ filename }}
        </div>
        <div v-if="!disabled" class="text-xs text-gray-500">
          {{ $t('components.imageUpload.clickToChange') }}
        </div>
      </div>
    </div>
    
    <!-- Upload progress -->
    <div v-if="uploading" class="space-y-2">
      <div class="flex items-center justify-between text-sm">
        <span>{{ $t('components.imageUpload.uploading') }}</span>
        <span>{{ uploadProgress }}%</span>
      </div>
      <div class="w-full bg-gray-200 rounded-full h-2">
        <div
          class="bg-blue-600 h-2 rounded-full transition-all duration-300"
          :style="{ width: `${uploadProgress}%` }"
        ></div>
      </div>
    </div>
    
    <!-- Error message -->
    <div v-if="error" class="text-sm text-red-600">
      {{ error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { ImageIcon, X } from 'lucide-vue-next'

interface FileUploadResponse {
  id: string
  filename: string
  content_type: string
  file_size: number
  file_type: string
  created_at: string
  metadata: Record<string, any>
  url: string
}

interface Props {
  modelValue?: string | null
  disabled?: boolean
  placeholder?: string
  required?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: null,
  disabled: false,
  placeholder: 'Select image',
  required: false
})

const emit = defineEmits<{
  'update:modelValue': [value: string | null]
  'upload-success': [response: FileUploadResponse]
  'upload-error': [error: string]
}>()

const { $t } = useNuxtApp()

// State
const fileInput = ref<HTMLInputElement>()
const previewUrl = ref<string>('')
const filename = ref<string>('')
const uploading = ref(false)
const uploadProgress = ref(0)
const error = ref<string>('')
const isDragging = ref(false)

const hasValue = computed(() => !!props.modelValue)

const triggerFileInput = () => {
  if (!props.disabled) {
    fileInput.value?.click()
  }
}

const validateFile = (file: File): string | null => {
  // Check file type
  if (!file.type.startsWith('image/')) {
    return $t('components.imageUpload.error.selectImage')
  }
  
  // Check file size (10MB)
  const maxSize = 10 * 1024 * 1024
  if (file.size > maxSize) {
    return $t('components.imageUpload.error.maxSize')
  }
  
  return null
}

const uploadFile = async (file: File): Promise<FileUploadResponse> => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('file_type', 'avatar')
  
  const { $api } = useNuxtApp()
  
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    
    // Listen for upload progress
    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable) {
        uploadProgress.value = Math.round((event.loaded / event.total) * 100)
      }
    })
    
    xhr.addEventListener('load', () => {
      if (xhr.status === 200) {
        try {
          const response = JSON.parse(xhr.responseText)
          resolve(response)
        } catch (err) {
          reject(new Error($t('components.imageUpload.error.parseFailed')))
        }
      } else {
        reject(new Error(`${$t('components.imageUpload.error.uploadFailed')}: ${xhr.status}`))
      }
    })
    
    xhr.addEventListener('error', () => {
      reject(new Error($t('components.imageUpload.error.networkError')))
    })
    
    xhr.open('POST', '/api/v1/files/upload')
    
    xhr.send(formData)
  })
}

const handleFileSelect = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  
  if (file) {
    await processFile(file)
  }
}

const handleDrop = async (event: DragEvent) => {
  isDragging.value = false
  
  if (props.disabled) return
  
  const files = event.dataTransfer?.files
  const file = files?.[0]
  
  if (file) {
    await processFile(file)
  }
}

const processFile = async (file: File) => {
  error.value = ''
  
  // Validate file
  const validationError = validateFile(file)
  if (validationError) {
    error.value = validationError
    return
  }
  
  // Create preview
  const reader = new FileReader()
  reader.onload = (e) => {
    previewUrl.value = e.target?.result as string
    filename.value = file.name
  }
  reader.readAsDataURL(file)
  
  // Upload file
  try {
    uploading.value = true
    uploadProgress.value = 0
    
    const response = await uploadFile(file)
    
    // Update value
    emit('update:modelValue', response.id)
    emit('upload-success', response)
    
    // Use server-returned URL as preview
    previewUrl.value = response.url
    filename.value = response.filename
    
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : $t('components.imageUpload.error.uploadFailed')
    error.value = errorMessage
    emit('upload-error', errorMessage)
    
    // Clear preview
    previewUrl.value = ''
    filename.value = ''
    
  } finally {
    uploading.value = false
    uploadProgress.value = 0
  }
}

const removeImage = () => {
  previewUrl.value = ''
  filename.value = ''
  emit('update:modelValue', null)
  
  // Clear file input
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

// Watch external value changes
watch(() => props.modelValue, async (newValue) => {
  if (!newValue) {
    previewUrl.value = ''
    filename.value = ''
    return
  }
  
  // If there's a file ID, try to get file info to display preview
  if (newValue && !previewUrl.value) {
    try {
      const { $api } = useNuxtApp()
      const response: any = await $api(`/v1/files/${newValue}`)
      
      if (response && response.url) {
        previewUrl.value = response.url
        filename.value = response.filename
      }
    } catch (err) {
      console.warn($t('components.imageUpload.error.loadPreview'), err)
    }
  }
})

// Drag events events
const handleDragEnter = () => {
  if (!props.disabled) {
    isDragging.value = true
  }
}

const handleDragLeave = () => {
  isDragging.value = false
}

// Expose methods
defineExpose({
  removeImage,
  triggerFileInput
})
</script>