<script setup lang="ts">
import FilePreviewSheet from '@/components/file-preview/FilePreviewSheet.vue'
import { Toaster } from '@/components/ui/sonner'
import 'vue-sonner/style.css' // vue-sonner v2 requires this import

const runtimeConfig = useRuntimeConfig()
const { t } = useI18n()
const i18nHead = useLocaleHead()
const appName = computed(() => runtimeConfig.public.appName as string)

useHead(() => ({
  titleTemplate: (titleChunk?: string): string => {
    const siteName = appName.value || 'RiceBall'
    const siteSlogan = t('common.slogan')
    return titleChunk ? `${titleChunk} | ${siteName} - ${siteSlogan}` : `${siteName} - ${siteSlogan}`
  },
  htmlAttrs: {
    lang: i18nHead.value.htmlAttrs.lang
  }
}))

</script>

<template>
  <Toaster />
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
  <FilePreviewSheet />
</template>