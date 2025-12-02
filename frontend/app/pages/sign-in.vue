<script setup lang="ts">
const { t } = useI18n()

definePageMeta({
  layout: 'auth',
  middleware: 'guest'
})

useHead({
  title: t('pageTitle.signIn')
})

const route = useRoute()
const redirect = computed(() => {
  const target = route.query.redirect
  return typeof target === 'string' && target.length > 0 ? target : undefined
})

</script>

<template>
  <AuthForm scene="sign-in" :redirect-url="redirect" />
</template>
