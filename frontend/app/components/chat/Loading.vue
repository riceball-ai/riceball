<script setup lang="ts">
import { useMarkdown } from '~/composables/useMarkdown'

interface Props {
  assistant?: Assistant | null
  message?: string
  isStreaming?: boolean
  streamingContent?: string
}

const props = withDefaults(defineProps<Props>(), {
  message: '...',
  isStreaming: false,
  streamingContent: ''
})

const { renderMarkdown } = useMarkdown()

const renderedStreamingContent = computed(() => {
  return renderMarkdown(props.streamingContent || '')
})
</script>

<template>
  <div class="flex">
    <div class="w-full">
      <div v-if="isStreaming && streamingContent" class="markdown-content">
        <div v-html="renderedStreamingContent"></div>
        <span class="inline-block w-2 h-4 bg-current animate-pulse ml-1"></span>
      </div>
      <div v-else class="flex items-center space-x-2">
        <div class="flex space-x-1">
          <div class="w-2 h-2 bg-current rounded-full animate-bounce" style="animation-delay: 0ms"></div>
          <div class="w-2 h-2 bg-current rounded-full animate-bounce" style="animation-delay: 150ms"></div>
          <div class="w-2 h-2 bg-current rounded-full animate-bounce" style="animation-delay: 300ms"></div>
        </div>
        <p class="text-sm text-muted-foreground">{{ message }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
@keyframes bounce {

  0%,
  80%,
  100% {
    transform: translateY(0);
  }

  40% {
    transform: translateY(-6px);
  }
}

.animate-bounce {
  animation: bounce 1.4s infinite;
}

.markdown-content>*:last-child {
  margin-bottom: 0 !important;
}
</style>
