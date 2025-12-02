<script setup lang="ts">
import { FetchError } from 'ofetch'
import { toast } from "vue-sonner"

const { t } = useI18n()

definePageMeta({
    layout: 'auth'
})

useHead({
  title: t('pageTitle.resetPassword')
})

const route = useRoute()
const { $api } = useNuxtApp()

const token = ref(route.query.token as string || '')
const password = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const success = ref(false)

const redirectCountdown = ref(0)
let redirectTimer: ReturnType<typeof setInterval> | null = null

const startRedirectCountdown = () => {
    redirectCountdown.value = 3
    redirectTimer = setInterval(() => {
        redirectCountdown.value--
        if (redirectCountdown.value <= 0) {
            clearInterval(redirectTimer!)
            redirectTimer = null
            navigateTo('/sign-in')
        }
    }, 1000)
}

const resetPassword = async () => {
    if (!token.value) {
        toast.error(t('resetPassword.invalidToken'))
        return
    }

    if (!password.value) {
        toast.error(t('resetPassword.enterPassword'))
        return
    }

    if (password.value.length < 8) {
        toast.error(t('resetPassword.passwordTooShort'))
        return
    }

    if (password.value !== confirmPassword.value) {
        toast.error(t('resetPassword.passwordMismatch'))
        return
    }

    loading.value = true

    try {
        await $api('/v1/auth/reset-password', {
            method: 'POST',
            body: {
                token: token.value,
                password: password.value
            }
        })

        success.value = true
        toast.success(t('resetPassword.success'))
        startRedirectCountdown()
    } catch (err) {
        if (err instanceof FetchError) {
            if (err.statusCode === 400) {
                const detail = err.data?.detail
                if (detail === 'RESET_PASSWORD_INVALID_TOKEN') {
                    toast.error(t('resetPassword.tokenExpired'))
                } else if (detail === 'RESET_PASSWORD_BAD_TOKEN') {
                    toast.error(t('resetPassword.invalidToken'))
                } else {
                    toast.error(t('resetPassword.failed'))
                }
            } else {
                toast.error(t('resetPassword.failed'))
            }
        } else {
            toast.error(t('resetPassword.failed'))
        }
    } finally {
        loading.value = false
    }
}

onUnmounted(() => {
    if (redirectTimer) {
        clearInterval(redirectTimer)
    }
})
</script>

<template>
    <div class="flex flex-col gap-6">
        <div class="flex flex-col items-center gap-2 text-center">
            <h1 class="text-2xl font-bold">{{ $t('resetPassword.title') }}</h1>
            <p class="text-balance text-sm text-muted-foreground">
                {{ $t('resetPassword.description') }}
            </p>
        </div>

        <div v-if="success" class="p-3 text-sm text-green-600 bg-green-50 border border-green-200 rounded-md">
            {{ $t('resetPassword.successMessage') }}
            <p class="mt-2 text-xs">{{ $t('resetPassword.autoRedirect', { seconds: redirectCountdown }) }}</p>
        </div>

        <div v-if="!success && !token" class="p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md">
            {{ $t('resetPassword.missingToken') }}
        </div>

        <div v-if="!success && token" class="space-y-4">
            <div class="space-y-2">
                <label for="password" class="text-sm font-medium">
                    {{ $t('resetPassword.newPasswordLabel') }}
                </label>
                <input
                    id="password"
                    v-model="password"
                    type="password"
                    :placeholder="$t('resetPassword.passwordPlaceholder')"
                    class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                />
                <p class="text-xs text-muted-foreground">
                    {{ $t('resetPassword.passwordHint') }}
                </p>
            </div>

            <div class="space-y-2">
                <label for="confirmPassword" class="text-sm font-medium">
                    {{ $t('resetPassword.confirmPasswordLabel') }}
                </label>
                <input
                    id="confirmPassword"
                    v-model="confirmPassword"
                    type="password"
                    :placeholder="$t('resetPassword.confirmPasswordPlaceholder')"
                    class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    @keyup.enter="resetPassword"
                />
            </div>

            <Button
                type="button"
                class="w-full"
                :disabled="loading"
                @click="resetPassword"
            >
                <span v-if="loading" class="flex items-center gap-2">
                    <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    {{ $t('resetPassword.resetting') }}
                </span>
                <span v-else>
                    {{ $t('resetPassword.resetButton') }}
                </span>
            </Button>

            <div class="text-center">
                <Button type="button" variant="link" @click="navigateTo('/sign-in')">
                    {{ $t('resetPassword.backToLogin') }}
                </Button>
            </div>
        </div>
    </div>
</template>
