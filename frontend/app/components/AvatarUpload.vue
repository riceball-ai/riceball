<template>
  <div class="space-y-4">
    <!-- Avatar upload area -->
    <div class="flex items-center space-x-4">
      <!-- Avatar preview -->
      <div
        @click="triggerFileInput"
        @dragover.prevent
        @drop.prevent="handleDrop"
        class="relative w-20 h-20 rounded-full border-2 border-dashed border-gray-300 cursor-pointer transition-colors hover:border-gray-400 flex items-center justify-center overflow-hidden bg-gray-50"
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
        
        <!-- Display when no avatar -->
        <div v-if="!previewUrl" class="text-center">
          <UserIcon class="w-8 h-8 text-gray-400 mx-auto mb-1" />
          <div class="text-xs text-gray-500">{{ t('components.avatarUpload.label') }}</div>
        </div>
        
        <!-- Avatar preview -->
        <img
          v-else
          :src="previewUrl"
          :alt="t('components.avatarUpload.previewAlt')"
          class="w-full h-full object-cover"
        />
        
        
        <!-- Upload progress overlay -->
        <div 
          v-if="uploading" 
          class="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center rounded-full"
        >
          <div class="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
        </div>
      </div>

      <!-- Action buttons -->
      <div class="flex flex-col space-y-2">
        <button
          type="button"
          @click="triggerFileInput"
          :disabled="disabled || uploading"
          class="px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Upload class="w-4 h-4 inline mr-1" />
          {{ uploading ? t('components.avatarUpload.uploading') : (previewUrl ? t('components.avatarUpload.change') : t('components.avatarUpload.select')) }}
        </button>
        
        <button
          v-if="previewUrl"
          type="button"
          @click="removeAvatar"
          :disabled="disabled || uploading"
          class="px-3 py-1.5 text-sm border border-red-300 text-red-600 rounded-md hover:bg-red-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Trash2 class="w-4 h-4 inline mr-1" />
          {{ t('components.avatarUpload.remove') }}
        </button>
      </div>
    </div>

    <!-- Upload hint -->
    <div v-if="!previewUrl && !error" class="text-xs text-gray-500">
      {{ placeholder || t('components.avatarUpload.placeholder') }}
    </div>
    
    <!-- Upload progress -->
    <div v-if="uploading" class="space-y-2">
      <div class="flex items-center justify-between text-sm">
        <span>{{ t('components.avatarUpload.uploading') }}</span>
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
import { ref, watch, computed, onMounted } from 'vue'
import { Upload, X, Trash2, User as UserIcon } from 'lucide-vue-next'

const { t } = useI18n()

interface FileUploadResponse {
  id: string
  filename: string
  content_type: string
  file_size: number
  file_type: string
  file_path: string
  created_at: string
  metadata: Record<string, any>
  url: string
}

interface Props {
  modelValue?: string | null
  initialUrl?: string | null
  disabled?: boolean
  placeholder?: string
  required?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: null,
  initialUrl: null,
  disabled: false,
  placeholder: '',
  required: false
})

const emit = defineEmits<{
  'update:modelValue': [value: string | null]
  'upload-success': [response: FileUploadResponse]
  'upload-error': [error: string]
}>()

// State
const fileInput = ref<HTMLInputElement>()
const previewUrl = ref<string>('')
const filename = ref<string>('')
const uploading = ref(false)
const uploadProgress = ref(0)
const error = ref<string>('')
const isDragging = ref(false)

// Methods
const triggerFileInput = () => {
  if (!props.disabled && !uploading.value) {
    fileInput.value?.click()
  }
}

const validateFile = (file: File): string | null => {
  // Check file type
  if (!file.type.startsWith('image/')) {
    return t('components.avatarUpload.error.type')
  }
  
  // Check file size (2MB)
  const maxSize = 2 * 1024 * 1024
  if (file.size > maxSize) {
    return t('components.avatarUpload.error.size')
  }
  
  return null
}

const uploadFile = async (file: File): Promise<FileUploadResponse> => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('file_type', 'avatar')
  
  const { $api } = useNuxtApp()
  // Use XMLHttpRequest to support upload progress monitoring
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    
    // Listen upload progress
    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable) {
        uploadProgress.value = Math.round((event.loaded / event.total) * 100)
      }
    })
    
    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const response = JSON.parse(xhr.responseText)
          resolve(response)
        } catch (err) {
          reject(new Error(t('components.avatarUpload.error.parse')))
        }
      } else {
        try {
          const errorResponse = JSON.parse(xhr.responseText)
          reject(new Error(errorResponse.message || t('components.avatarUpload.error.upload', { status: xhr.status })))
        } catch {
          reject(new Error(t('components.avatarUpload.error.upload', { status: xhr.status })))
        }
      }
    })
    
    xhr.addEventListener('error', () => {
      reject(new Error(t('components.avatarUpload.error.network')))
    })
    
    xhr.addEventListener('timeout', () => {
      reject(new Error(t('components.avatarUpload.error.timeout')))
    })
    
    xhr.addEventListener('abort', () => {
      reject(new Error(t('components.avatarUpload.error.cancel')))
    })
    
    // Use same base config as $api
    xhr.open('POST', '/api/v1/files/upload')
    
    // Set timeout (30s)
    xhr.timeout = 30000
    
    // Set request headers to match $api behavior
    xhr.setRequestHeader('Accept', 'application/json')
    
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
  
  if (props.disabled || uploading.value) return
  
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
    
    // Update values
    emit('update:modelValue', response.file_path)
    emit('upload-success', response)
    
    // Use server returned URL as preview
    previewUrl.value = response.url
    filename.value = response.filename
    
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : t('components.avatarUpload.error.generic')
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

const removeAvatar = () => {
  if (props.disabled || uploading.value) return
  
  previewUrl.value = ''
  filename.value = ''
  error.value = ''
  emit('update:modelValue', null)
  
  // Clear file input
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

// Drag event handlers
const handleDragEnter = () => {
  if (!props.disabled && !uploading.value) {
    isDragging.value = true
  }
}

const handleDragLeave = () => {
  isDragging.value = false
}

// Load preview from path
const loadPreviewFromPath = async (path: string) => {
  try {
    const { $api } = useNuxtApp()
    // Encode path to prevent slashes causing route issues
    const encodedPath = encodeURIComponent(path)
    const response: any = await $api(`/v1/files/url/${encodedPath}`)
    
    if (response && response.url) {
      previewUrl.value = response.url
      filename.value = response.filename || ''
    }
  } catch (err) {
    console.warn('Failed to load avatar preview:', err)
  }
}
// Initialize
onMounted(() => {
  if (props.modelValue) {
    if (props.initialUrl) {
      previewUrl.value = props.initialUrl
    } else {
      loadPreviewFromPath(props.modelValue)
    }
  }
})

// Watch for external modelValue changes
watch(() => props.modelValue, async (newValue) => {
  if (!newValue) {
    previewUrl.value = ''
    filename.value = ''
    return
  }
  
  // If an initial URL is provided and preview isn't set, prefer the initial URL
  if (props.initialUrl && !previewUrl.value) {
    previewUrl.value = props.initialUrl
    return
  }
  
  // If there's a file path but no preview (and no initial URL), try fetching file info to display preview
  if (newValue && !previewUrl.value) {
    loadPreviewFromPath(newValue)
  }
})

// Watch for initialUrl changes
watch(() => props.initialUrl, (newUrl) => {
  if (newUrl && !previewUrl.value) {
    previewUrl.value = newUrl
  }
})

// Expose methods
defineExpose({
  removeAvatar,
  triggerFileInput
})
</script>