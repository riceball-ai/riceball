<script setup lang="ts">
import { computed } from 'vue'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { useFilePreview } from '@/composables/useFilePreview'

const { previewState, closePreview } = useFilePreview()
const { t } = useI18n()

const isSvg = computed(() => previewState.value.type === 'svg')
const drawerTitle = computed(() => previewState.value.title || t('chat.preview.drawerTitle'))
const unsupportedText = computed(() => t('chat.preview.unsupportedType'))
const svgPreviewAlt = computed(() => previewState.value.title || t('chat.preview.svgTitle'))

const svgDataUrl = computed(() => {
  if (!isSvg.value || !previewState.value.content) {
    return null
  }
  return `data:image/svg+xml;utf8,${encodeURIComponent(previewState.value.content)}`
})

const handleOpenChange = (open: boolean) => {
  if (!open) {
    closePreview()
  }
}
</script>

<template>
  <Sheet :open="previewState.open" @update:open="handleOpenChange">
    <SheetContent side="right" class="sm:max-w-3xl w-full max-w-[520px]">
      <SheetHeader>
        <SheetTitle>{{ drawerTitle }}</SheetTitle>
        <SheetDescription v-if="previewState.description">
          {{ previewState.description }}
        </SheetDescription>
      </SheetHeader>

      <div class="mt-4 flex-1 overflow-hidden rounded-md border border-border bg-muted/30">
        <div
          v-if="isSvg && svgDataUrl"
          class="flex h-full min-h-[300px] items-center justify-center bg-white dark:bg-gray-950 p-4"
        >
          <img
            :src="svgDataUrl"
            :alt="svgPreviewAlt"
            loading="lazy"
            class="max-h-full max-w-full"
          />
        </div>
        <div v-else class="p-4 text-sm text-muted-foreground">
          {{ unsupportedText }}
        </div>
      </div>

      <div
        v-if="isSvg && previewState.content"
        class="mt-4 rounded-md border border-dashed border-border bg-background/60 p-3 text-xs text-muted-foreground whitespace-pre-wrap break-all"
      >
        {{ previewState.content }}
      </div>
    </SheetContent>
  </Sheet>
</template>
