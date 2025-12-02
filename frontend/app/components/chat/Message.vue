<script setup lang="ts">
import { nextTick, onMounted, onUnmounted } from 'vue'
import { useMarkdown } from '~/composables/useMarkdown'
import { Copy, Share, Check, Quote } from 'lucide-vue-next'
import type { Assistant, Message } from '~/types/api'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '~/components/ui/dialog'

interface Props {
  message: Message
  assistant?: Assistant | null
  enableShare?: boolean
  forceCompleted?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  enableShare: true,
  forceCompleted: false
})

const emit = defineEmits<{
  (e: 'share', message: Message): void
  (e: 'quote', content: string): void
}>()

// Use markdown composable
const { t } = useI18n()
const { renderMarkdown } = useMarkdown()

// State management
const copySuccess = ref(false)

const isUuid = (value: string) => {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)
}

const isStreamingMessage = computed(() => {
  if (props.forceCompleted) {
    return false
  }
  if (props.message.status === 'STREAMING') {
    return true
  }
  return !isUuid(props.message.id)
})

// Compute rendered content
const renderedContent = computed(() => {
  const defaultPanel = isStreamingMessage.value ? 'code' : 'preview'
  return renderMarkdown(props.message.content, { defaultSvgPanel: defaultPanel })
})

// Copy message content
const copyMessage = async () => {
  try {
    await navigator.clipboard.writeText(props.message.content)
    copySuccess.value = true
    setTimeout(() => {
      copySuccess.value = false
    }, 2000) // Restore original icon after 2 seconds
  } catch (err) {
    console.error('Copy failed:', err)
  }
}

const handleShare = () => {
  emit('share', props.message)
}

const decodeAttr = (value: string | null): string => {
  if (!value) return ''
  try {
    return decodeURIComponent(value)
  } catch (error) {
    console.warn('Attribute decode failed:', error)
    return value
  }
}

const messageRoot = ref<HTMLElement | null>(null)

interface RenderableImage {
  id?: string
  url: string
  alt?: string
}

const imagePreviewOpen = ref(false)
const previewImage = ref<RenderableImage | null>(null)

const openImagePreview = (image: RenderableImage) => {
  previewImage.value = image
  imagePreviewOpen.value = true
}

watch(imagePreviewOpen, (open) => {
  if (!open) {
    previewImage.value = null
  }
})

const userImages = computed<RenderableImage[]>(() => {
  if (props.message.message_type !== 'USER') {
    return []
  }
  const images = props.message.extra_data?.images
  if (!Array.isArray(images)) {
    return []
  }
  return images
    .map((img: any, index: number) => {
      const url = img?.url || img?.data_url || img?.dataUrl
      if (!url) return null
      return {
        id: img?.id || `user-image-${props.message.id}-${index}`,
        url,
        alt: img?.alt || t('chat.userImageAlt', { index: index + 1 })
      }
    })
    .filter((item): item is RenderableImage => item !== null && typeof item === 'object')
})

const assistantImages = computed<RenderableImage[]>(() => {
  if (props.message.message_type !== 'ASSISTANT') {
    return []
  }
  const mediaItems = props.message.extra_data?.media
  if (!Array.isArray(mediaItems)) {
    return []
  }
  return mediaItems
    .filter(item => item?.type === 'image' && (item.url || item.data_url))
    .map(item => ({
      id: item.id,
      url: item.url || item.data_url,
      alt: item.alt || t('chat.generatedImageAlt')
    }))
})

const hasRenderableImages = computed(() => {
  return userImages.value.length > 0 || assistantImages.value.length > 0
})

const setActivePreviewPanel = (panelsElement: HTMLElement, targetPanel: string) => {
  const current = panelsElement.dataset.activePanel
  if (current === targetPanel) return
  panelsElement.dataset.activePanel = targetPanel
  const panels = panelsElement.querySelectorAll<HTMLElement>('[data-panel]')
  panels.forEach(panel => {
    const panelName = panel.getAttribute('data-panel')
    if (panelName === targetPanel) {
      panel.style.display = ''
    } else {
      panel.style.display = 'none'
    }
  })

  const relatedButtons = messageRoot.value?.querySelectorAll<HTMLElement>(`[data-preview-panels="${panelsElement.id}"]`)
  relatedButtons?.forEach(button => {
    const buttonTarget = button.getAttribute('data-preview-toggle')
    button.setAttribute('data-state', buttonTarget === targetPanel ? 'active' : 'inactive')
  })
}

const updatePreviewPanels = (mode: 'streaming' | 'final') => {
  if (!messageRoot.value) return
  const containers = messageRoot.value.querySelectorAll<HTMLElement>('[data-preview-default]')
  containers.forEach(container => {
    const target = mode === 'streaming'
      ? container.getAttribute('data-preview-streaming') || 'code'
      : container.getAttribute('data-preview-final') || 'preview'
    container.setAttribute('data-preview-default', target)
    setActivePreviewPanel(container, target)
  })
}

const handleMarkdownClick = (event: MouseEvent) => {
  const target = event.target as HTMLElement | null
  if (!target) return

  const toggleButton = target.closest('[data-preview-toggle]') as HTMLElement | null
  if (toggleButton) {
    const panelName = toggleButton.getAttribute('data-preview-toggle')
    const panelsId = toggleButton.getAttribute('data-preview-panels')
    if (panelName && panelsId) {
      const panelsElement = document.getElementById(panelsId)
      if (panelsElement) {
        setActivePreviewPanel(panelsElement, panelName)
      }
    }
    return
  }

  const downloadTrigger = target.closest('[data-preview-download]') as HTMLElement | null
  if (downloadTrigger) {
    const encodedContent = downloadTrigger.getAttribute('data-svg-content')
    if (!encodedContent) return
    const fileName = decodeAttr(downloadTrigger.getAttribute('data-download-name')) || 'preview.svg'
    const content = decodeAttr(encodedContent)
    try {
      const blob = new Blob([content], { type: 'image/svg+xml;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = fileName
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Failed to download SVG preview', error)
    }
    return
  }
}

const selectionMenuVisible = ref(false)
const selectionMenuPosition = ref({ top: 0, left: 0 })
const selectedText = ref('')

const handleSelection = () => {
  const selection = window.getSelection()
  if (!selection || selection.isCollapsed) {
    selectionMenuVisible.value = false
    return
  }

  const text = selection.toString().trim()
  if (!text) {
    selectionMenuVisible.value = false
    return
  }

  // Check if selection is within this message
  if (messageRoot.value && messageRoot.value.contains(selection.anchorNode)) {
    const range = selection.getRangeAt(0)
    const rect = range.getBoundingClientRect()
    
    selectedText.value = text
    selectionMenuPosition.value = {
      top: rect.top - 40, // Position above selection
      left: rect.left + (rect.width / 2) // Center horizontally
    }
    selectionMenuVisible.value = true
  } else {
    selectionMenuVisible.value = false
  }
}

const handleQuote = () => {
  if (selectedText.value) {
    emit('quote', selectedText.value)
    selectionMenuVisible.value = false
    window.getSelection()?.removeAllRanges()
  }
}

// Close menu when clicking outside
const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as HTMLElement
  if (selectionMenuVisible.value && !target.closest('.selection-menu')) {
    selectionMenuVisible.value = false
  }
}

onMounted(() => {
  document.addEventListener('selectionchange', handleSelection)
  document.addEventListener('mousedown', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('selectionchange', handleSelection)
  document.removeEventListener('mousedown', handleClickOutside)
})

watch(
  () => isStreamingMessage.value,
  streaming => {
    nextTick(() => updatePreviewPanels(streaming ? 'streaming' : 'final'))
  },
  { immediate: true }
)
</script>

<template>
  <div ref="messageRoot" class="flex" :class="{
    'justify-end': message.message_type === 'USER'
  }">
    <div :class="{
      'max-w-3xl': message.message_type === 'USER',
      'w-full': message.message_type === 'ASSISTANT'
    }">
      <div class="rounded-lg" :class="{
        'bg-gray-100 dark:bg-gray-800 text-foreground p-3': message.message_type === 'USER',
        'text-foreground': message.message_type === 'ASSISTANT'
      }">
        <article 
          class="markdown-content prose prose-zinc dark:prose-invert max-w-none"
          v-html="renderedContent"
          @click="handleMarkdownClick"
        ></article>
        
        <!-- Render media attachments if present -->
        <div v-if="hasRenderableImages" class="mt-3 space-y-2">
          <div 
            v-for="image in (message.message_type === 'USER' ? userImages : assistantImages)"
            :key="image.id"
            class="rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700"
          >
            <img 
              :src="image.url"
              :alt="image.alt || 'Image'"
              class="max-w-full h-auto cursor-zoom-in transition hover:opacity-90"
              loading="lazy"
              :title="t('chat.imagePreviewHint')"
              @click="openImagePreview(image)"
            />
          </div>
        </div>
      </div>
      
      <!-- Toolbar -->
      <div v-if="!isStreamingMessage" class="flex items-center gap-2">
        <Button 
          @click="copyMessage"
          class="w-8 h-8 p-0 rounded-full text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          :title="t('chat.copyContent')"
          variant="ghost"
        >
          <Check v-if="copySuccess" class="w-4 h-4" />
          <Copy v-else class="w-4 h-4" />
        </Button>
        
        <Button 
          v-if="enableShare && message.message_type === 'ASSISTANT'"
          @click="handleShare"
          class="w-8 h-8 p-0 rounded-full text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          :title="t('chat.share.titleMessage')"
          variant="ghost"
        >
          <Share class="w-4 h-4" />
        </Button>
      </div>
    </div>
  </div>

  <Dialog v-model:open="imagePreviewOpen">
    <DialogContent class="sm:max-w-[90vw] max-h-[90vh]">
      <DialogHeader class="pb-2">
        <DialogTitle>{{ t('chat.imagePreviewTitle') }}</DialogTitle>
      </DialogHeader>
      <div class="max-h-[70vh] overflow-auto">
        <img
          v-if="previewImage"
          :src="previewImage.url"
          :alt="previewImage.alt || t('chat.imagePreviewTitle')"
          class="w-full h-auto rounded-md"
        />
      </div>
    </DialogContent>
  </Dialog>

  <!-- Selection Menu -->
  <div
    v-if="selectionMenuVisible"
    class="selection-menu fixed z-50 bg-popover text-popover-foreground shadow-md rounded-md border px-2 py-1 flex items-center gap-1 animate-in fade-in zoom-in duration-200"
    :style="{
      top: `${selectionMenuPosition.top}px`,
      left: `${selectionMenuPosition.left}px`,
      transform: 'translateX(-50%)'
    }"
  >
    <button
      @click="handleQuote"
      class="flex items-center gap-1 text-xs font-medium hover:bg-accent hover:text-accent-foreground px-2 py-1 rounded transition-colors"
    >
      <Quote class="w-3 h-3" />
      {{ t('chat.quote') }}
    </button>
  </div>
</template>

<style scoped>
.markdown-content > *:last-child {
  margin-bottom: 0 !important;
}
</style>
