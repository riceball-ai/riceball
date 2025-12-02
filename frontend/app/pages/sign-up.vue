<script setup lang="ts">
const { t } = useI18n()

definePageMeta({
  layout: 'auth',
  middleware: 'guest'
})

useHead({
  title: t('pageTitle.signUp')
})

</script>

<template>
  <AuthForm scene="sign-up" />
</template>

<style scoped></style>
