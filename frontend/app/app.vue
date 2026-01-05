<script setup lang="ts">
import FilePreviewSheet from '@/components/file-preview/FilePreviewSheet.vue'
import { Toaster } from '@/components/ui/sonner'
import 'vue-sonner/style.css' // vue-sonner v2 requires this import

const runtimeConfig = useRuntimeConfig()
const { t } = useI18n()
const i18nHead = useLocaleHead()
const appName = computed(() => runtimeConfig.public.appName as string)
const configStore = useConfigStore()

// Ensure config is loaded
await configStore.getConfig()

useHead(() => ({
  titleTemplate: (titleChunk?: string): string => {
    const siteName = configStore.config.site_title || appName.value || ''
    const siteSlogan = t('common.slogan')
    return titleChunk ? `${titleChunk} | ${siteName} - ${siteSlogan}` : `${siteName} - ${siteSlogan}`
  },
  link: [
    ...(configStore.config.site_favicon ? [{ rel: 'icon', href: configStore.config.site_favicon }] : [])
  ],
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