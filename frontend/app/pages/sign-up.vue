<script setup lang="ts">
const { t } = useI18n()
const configStore = useConfigStore()

await configStore.loadConfig()

if (!configStore.config.registration_enabled) {
  throw showError({
    statusCode: 403,
    statusMessage: t('error.registrationClosed'),
    message: t('error.registrationClosedMessage'),
    fatal: true
  })
}

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
