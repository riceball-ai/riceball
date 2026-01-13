<script setup lang="ts">
import { computed } from 'vue'
import { useMarkdown } from '~/composables/useMarkdown'

interface Props {
  content: string
  isStreaming?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isStreaming: false
})

const emit = defineEmits<{
  (e: 'click', event: MouseEvent): void
}>()

const { renderMarkdown } = useMarkdown()

const renderedContent = computed(() => {
  const defaultPanel = props.isStreaming ? 'code' : 'preview'
  return renderMarkdown(props.content, { defaultSvgPanel: defaultPanel })
})

const handleClick = (event: MouseEvent) => {
  emit('click', event)
}
</script>

<template>
  <article 
    class="markdown-content prose prose-zinc dark:prose-invert max-w-none"
    v-html="renderedContent"
    @click="handleClick"
  ></article>
</template>

<style scoped>
.markdown-content {
  /* Ensure content doesn't overflow flex container */
  min-width: 0;
  width: 100%;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.markdown-content > *:last-child {
  margin-bottom: 0 !important;
}

.markdown-content :deep(pre) {
  max-width: 100%;
  white-space: pre;
  overflow-x: auto;
  border-radius: 0.375rem;
}

.markdown-content :deep(.code-block-container) {
  max-width: 100%;
  min-width: 0;
}

/* Fix table overflow */
.markdown-content :deep(table) {
  display: block;
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
</style>
