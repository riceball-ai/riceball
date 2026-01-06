<script setup lang="ts">
import FilePreviewSheet from '@/components/file-preview/FilePreviewSheet.vue'
import { Toaster } from '@/components/ui/sonner'
import 'vue-sonner/style.css' // vue-sonner v2 requires this import

const runtimeConfig = useRuntimeConfig()
const { t } = useI18n()
const i18nHead = import.meta.server 
  ? useLocaleHead({ addSeoAttributes: true }) 
  : ref({ htmlAttrs: {} })
const appName = computed(() => runtimeConfig.public.appName as string)
const configStore = useConfigStore()

// Ensure config is loaded
await configStore.getConfig()

useHead(() => ({
  titleTemplate: (titleChunk?: string): string => {
    const siteName = configStore.config.site_title || appName.value || t('common.app_name')
    const siteSlogan = configStore.config.site_slogan || t('common.slogan')
    return titleChunk ? `${titleChunk} | ${siteName} - ${siteSlogan}` : `${siteName} - ${siteSlogan}`
  },
  link: [
    ...(configStore.config.pwa_enabled ? [{ rel: 'manifest', href: '/api/v1/config/manifest.json' }] : []),
    ...(configStore.config.site_favicon ? [{ rel: 'icon', href: configStore.config.site_favicon }] : [])
  ],
  htmlAttrs: {
    lang: i18nHead.value.htmlAttrs?.lang
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