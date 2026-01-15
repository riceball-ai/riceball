<script setup lang="ts">
import { ArrowUp, Image as ImageIcon, Camera, X, Loader2, AlertTriangle, Square } from 'lucide-vue-next'
import type { ImageAttachment } from '~/composables/useStreamingChat'
import { InputGroup, InputGroupTextarea, InputGroupButton } from '~/components/ui/input-group'
import type { ComponentPublicInstance } from 'vue'

type AttachmentStatus = 'uploading' | 'ready' | 'error'

type AttachmentItem = ImageAttachment & {
  dataUrl?: string
  status: AttachmentStatus
  errorMessage?: string
}

interface Props {
  modelValue: string
  placeholder?: string
  disabled?: boolean
  sendDisabled?: boolean
  supportsVision?: boolean  // Whether the model supports image input
  loading?: boolean
  cameraCapture?: 'environment' | 'user' | 'any'
}

interface Emits {
  (e: 'update:modelValue', value: string): void
  (e: 'send', images?: ImageAttachment[]): void
  (e: 'stop'): void
  (e: 'keydown', event: KeyboardEvent): void
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  sendDisabled: false,
  supportsVision: false,
  loading: false,
  cameraCapture: 'environment'
})

const emit = defineEmits<Emits>()

const { $api } = useNuxtApp()
const { showError } = useNotifications()
const { t } = useI18n()
const textareaRef = ref<ComponentPublicInstance>()
const fileInputRef = ref<HTMLInputElement>()
const cameraInputRef = ref<HTMLInputElement>()
const attachedImages = ref<AttachmentItem[]>([])
const isDragActive = ref(false)
const dragCounter = ref(0)
const captureAttribute = computed(() => props.cameraCapture !== 'any' ? props.cameraCapture : undefined)
const placeholderText = computed(() => props.placeholder || t('chat.input.placeholder'))
const MAX_IMAGE_SIZE_MB = 5
const MAX_IMAGE_SIZE = MAX_IMAGE_SIZE_MB * 1024 * 1024

const pendingUploadsCount = computed(() => attachedImages.value.filter(img => img.status === 'uploading').length)
const hasPendingUploads = computed(() => pendingUploadsCount.value > 0)
const erroredAttachments = computed(() => attachedImages.value.filter(img => img.status === 'error'))
const readyAttachments = computed(() =>
  attachedImages.value.filter((img) => img.status === 'ready' && (img.url || img.dataUrl))
)

const buildSendPayload = (): ImageAttachment[] | undefined => {
  if (!readyAttachments.value.length) {
    return undefined
  }

  return readyAttachments.value.map(({ id, url, alt, mimeType, size, fileKey }) => ({
    id,
    url,
    alt,
    mimeType,
    size,
    fileKey
  }))
}

const resetAttachments = () => {
  attachedImages.value = []
}

const handleKeyPress = (event: KeyboardEvent) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    if (!props.sendDisabled) {
      if (hasPendingUploads.value) {
        showError(t('chat.input.pendingUploads'))
        return
      }
      const payload = buildSendPayload()
      emit('send', payload)
      resetAttachments()
    }
  }
  emit('keydown', event)
}

const handleSend = () => {
  if (props.loading) {
    emit('stop')
    return
  }

  if (hasPendingUploads.value) {
    showError(t('chat.input.pendingUploads'))
    return
  }
  const payload = buildSendPayload()
  emit('send', payload)
  resetAttachments()
}

const handleFileSelect = () => {
  fileInputRef.value?.click()
}

const handleCameraCapture = () => {
  cameraInputRef.value?.click()
}

const uploadImageFile = async (file: File, attachmentId: string) => {
  try {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('file_type', 'image')

    const response = await $api<{ url: string, id: string, file_path?: string, fileKey?: string }>("/v1/files/upload", {
      method: 'POST',
      body: formData
    })

    const image = attachedImages.value.find(img => img.id === attachmentId)
    if (image) {
      image.url = response.url
      image.fileKey = response.file_path || response.fileKey
      image.status = 'ready'
    }
  } catch (error) {
    console.error('Failed to upload image:', error)
    showError(t('chat.input.uploadFailed', { name: file.name }))
    const image = attachedImages.value.find(img => img.id === attachmentId)
    if (image) {
      image.status = 'error'
      image.errorMessage = t('chat.input.imageErrorMessage', { name: file.name })
    }
  }
}

const processFile = (file: File) => {
  if (!file.type.startsWith('image/')) {
    showError(t('chat.input.fileNotImage', { name: file.name }))
    return
  }

  if (file.size > MAX_IMAGE_SIZE) {
    showError(t('chat.input.fileTooLarge', { name: file.name, max: `${MAX_IMAGE_SIZE_MB}MB` }))
    return
  }

  const reader = new FileReader()
  reader.onload = async (e) => {
    const dataUrl = e.target?.result as string
    const imageId = `img-${Date.now()}-${Math.random()}`

    attachedImages.value.push({
      id: imageId,
      dataUrl,
      alt: file.name,
      mimeType: file.type,
      size: file.size,
      status: 'uploading'
    })

    await uploadImageFile(file, imageId)
  }
  reader.readAsDataURL(file)
}

const processFiles = (files: FileList | File[] | Iterable<File>) => {
  const list = Array.isArray(files) ? files : Array.from(files as Iterable<File>)
  for (const file of list) {
    processFile(file)
  }
}

const processFileList = (files: FileList | null) => {
  if (files && files.length > 0) {
    processFiles(files)
  }
}

const handleFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  processFileList(target.files)
  target.value = ''
}

const handleCameraChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  processFileList(target.files)
  target.value = ''
}

const handlePaste = (event: ClipboardEvent) => {
  if (!props.supportsVision) return
  const items = event.clipboardData?.items
  if (!items || items.length === 0) return

  const imageFiles: File[] = []
  for (const item of items) {
    if (item.kind === 'file') {
      const file = item.getAsFile()
      if (file && file.type.startsWith('image/')) {
        imageFiles.push(file)
      }
    }
  }

  if (imageFiles.length > 0) {
    const textData = event.clipboardData?.getData('text')
    if (!textData) {
      event.preventDefault()
    }
    processFiles(imageFiles)
  }
}

const handleDragEnter = (event: DragEvent) => {
  if (!props.supportsVision) return
  const hasFiles = event.dataTransfer?.types && Array.from(event.dataTransfer.types).includes('Files')
  if (!hasFiles) return
  event.preventDefault()
  dragCounter.value += 1
  isDragActive.value = true
}

const handleDragOver = (event: DragEvent) => {
  if (!props.supportsVision) return
  const hasFiles = event.dataTransfer?.types && Array.from(event.dataTransfer.types).includes('Files')
  if (!hasFiles) return
  event.preventDefault()
  event.dataTransfer.dropEffect = 'copy'
}

const handleDragLeave = (event: DragEvent) => {
  if (!props.supportsVision) return
  if (dragCounter.value > 0) {
    dragCounter.value -= 1
  }
  if (dragCounter.value === 0) {
    isDragActive.value = false
  }
}

const handleDrop = (event: DragEvent) => {
  if (!props.supportsVision) return
  event.preventDefault()
  dragCounter.value = 0
  isDragActive.value = false
  const files = event.dataTransfer?.files
  if (files && files.length > 0) {
    processFiles(files)
  }
}

const removeImage = (id: string) => {
  attachedImages.value = attachedImages.value.filter(img => img.id !== id)
}

// Auto-resize textarea
const adjustTextareaHeight = () => {
  const el = textareaRef.value?.$el as HTMLTextAreaElement | undefined
  if (el) {
    el.style.height = 'auto'
    const newHeight = Math.min(el.scrollHeight, 192)
    el.style.height = newHeight + 'px'
  }
}

watch(() => props.modelValue, () => {
  nextTick(() => adjustTextareaHeight())
})

onMounted(() => {
  adjustTextareaHeight()
})

defineExpose({
  focus: () => {
    const el = textareaRef.value?.$el as HTMLTextAreaElement | undefined
    el?.focus()
  }
})
</script>

<template>
  <fieldset
    class="flex w-full min-w-0 flex-col gap-2 transition-all"
    @dragenter.prevent="handleDragEnter"
    @dragover.prevent="handleDragOver"
    @dragleave.prevent="handleDragLeave"
    @drop.prevent="handleDrop"
  >
    <InputGroup
      class="flex-col h-auto bg-background items-stretch transition-all duration-200 relative cursor-text z-10 rounded-2xl hover:shadow-md"
      :class="{ 'ring-2 ring-primary/40 bg-accent/20': isDragActive }"
    >
      <!-- 1. Image previews (Top) -->
      <div v-if="attachedImages.length > 0" class="flex flex-wrap gap-2 px-3 pt-3">
        <div
          v-for="image in attachedImages"
          :key="image.id"
          class="relative group w-20 h-20 rounded-lg overflow-hidden border border-border"
        >
          <img
            :src="image.dataUrl"
            :alt="image.alt || t('chat.input.previewAlt')"
            class="w-full h-full object-cover"
          />
          <div
            v-if="image.status === 'uploading'"
            class="absolute inset-0 bg-background/70 flex items-center justify-center"
          >
            <Loader2 class="w-4 h-4 animate-spin text-muted-foreground" />
          </div>
          <div
            v-else-if="image.status === 'error'"
            class="absolute inset-0 bg-destructive/75 text-destructive-foreground text-[11px] font-medium flex items-center justify-center text-center px-1"
          >
            {{ t('chat.input.uploadFailedLabel') }}
          </div>
          <button
            @click="removeImage(image.id)"
            class="absolute top-1 right-1 p-1.5 rounded-full border border-border bg-background/90 text-destructive shadow-sm opacity-0 group-hover:opacity-100 transition-all hover:bg-destructive/10 hover:text-destructive hover:border-destructive"
            type="button"
          >
            <X class="w-3 h-3" />
          </button>
        </div>
      </div>

      <!-- 2. Text input area (Middle) -->
      <InputGroupTextarea
        ref="textareaRef"
        :model-value="modelValue"
        @update:model-value="(val) => emit('update:modelValue', String(val))"
        @keydown="handleKeyPress"
        @paste="handlePaste"
        :placeholder="placeholderText"
        :disabled="disabled"
        autofocus
        class="w-full resize-none border-0 outline-none bg-transparent text-base leading-6 placeholder:text-muted-foreground min-h-[3rem] max-h-48 py-3 px-3 shadow-none focus-visible:ring-0"
        rows="1"
      />

      <!-- 3. Bottom controls area (Bottom) -->
      <div class="flex gap-2.5 w-full items-center p-2 pl-2">
        <div class="relative flex-1 flex items-center gap-2 shrink min-w-0">
          <!-- Left side controls -->
          <div class="flex flex-row items-center gap-1 min-w-0">
            <template v-if="supportsVision">
              <InputGroupButton
                @click="handleFileSelect"
                type="button"
                :disabled="disabled"
                variant="ghost"
                size="icon-sm"
                :title="t('chat.input.uploadButton')"
                class="text-muted-foreground hover:text-foreground"
              >
                <ImageIcon class="size-5" />
              </InputGroupButton>
              <InputGroupButton
                @click="handleCameraCapture"
                type="button"
                :disabled="disabled"
                variant="ghost"
                size="icon-sm"
                :title="t('chat.input.cameraButton')"
                class="text-muted-foreground hover:text-foreground"
              >
                <Camera class="size-5" />
              </InputGroupButton>
            </template>
            <input
              ref="fileInputRef"
              type="file"
              accept="image/*"
              multiple
              class="hidden"
              @change="handleFileChange"
            />
            <input
              ref="cameraInputRef"
              type="file"
              accept="image/*"
              :capture="captureAttribute"
              class="hidden"
              @change="handleCameraChange"
            />
          </div>

          <!-- Status Text -->
          <div class="text-muted-foreground text-xs ml-1 space-y-1">
            <span v-if="hasPendingUploads" class="flex items-center gap-1">
              <Loader2 class="w-3 h-3 animate-spin" />
              {{ t('chat.input.uploadingStatus', { count: pendingUploadsCount }) }}
            </span>
            <span v-else-if="attachedImages.length > 0">
              {{ t('chat.input.readyStatus', { count: readyAttachments.length }) }}
            </span>
            <span v-if="erroredAttachments.length" class="flex items-center gap-1 text-destructive">
              <AlertTriangle class="w-3 h-3" />
              {{ t('chat.input.failedStatus', { count: erroredAttachments.length }) }}
            </span>
            <span v-if="supportsVision && attachedImages.length === 0 && !modelValue" class="block text-muted-foreground">
              {{ t('chat.input.visionHint') }}
            </span>
          </div>
        </div>

        <!-- Send button -->
        <div class="overflow-hidden shrink-0">
          <InputGroupButton
            @click="handleSend"
            :disabled="(sendDisabled && !loading) || hasPendingUploads"
            variant="default"
            size="icon-sm"
            class="rounded-full"
          >
            <Loader2 v-if="hasPendingUploads" class="animate-spin size-4" />
            <Square v-else-if="loading" class="fill-current size-4" />
            <ArrowUp v-else class="size-4" />
          </InputGroupButton>
        </div>
      </div>
    </InputGroup>
  </fieldset>
</template>
