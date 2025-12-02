<script setup>
const { locale } = useI18n()

const { data: doc } = await useAsyncData(
  `terms-${locale.value}`,
  () => queryCollection('content').path(`/${locale.value.toLowerCase()}/terms`).first(),
  {
    watch: [locale]
  }
)

definePageMeta({
  layout: 'legal',
})
</script>

<template>
  <div v-if="doc">
    <h1 class="text-h6">{{ doc.title }}</h1>
    <Separator class="mt-3 mb-5"></Separator>
    <ContentRenderer :value="doc" />
  </div>
  <div v-else class="text-center py-10">
    <h1 class="text-xl font-bold">Document not found</h1>
    <p class="text-gray-500">Could not find terms for locale: {{ locale }}</p>
  </div>
</template>