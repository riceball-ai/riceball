<script setup lang="ts">
import { FetchError } from 'ofetch'
import { toast } from "vue-sonner"

const { t } = useI18n()

definePageMeta({
    layout: 'auth'
})

useHead({
  title: t('pageTitle.forgotPassword')
})

const { $api } = useNuxtApp()

const email = ref('')
const loading = ref(false)
const success = ref(false)
const resendCountdown = ref(0)

let countdownTimer: ReturnType<typeof setInterval> | null = null

const startResendCountdown = () => {
    resendCountdown.value = 60
    countdownTimer = setInterval(() => {
        resendCountdown.value--
        if (resendCountdown.value <= 0) {
            clearInterval(countdownTimer!)
            countdownTimer = null
        }
    }, 1000)
}

const requestPasswordReset = async () => {
    if (!email.value) {
        toast.error(t('forgotPassword.enterEmail'))
        return
    }

    // Simple email format validation
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailPattern.test(email.value)) {
        toast.error(t('forgotPassword.invalidEmail'))
        return
    }

    loading.value = true

    try {
        await $api('/v1/auth/forgot-password', {
            method: 'POST',
            body: { 
                email: email.value,
            }
        })

        success.value = true
        toast.success(t('forgotPassword.emailSent'))
        startResendCountdown()
    } catch (err) {
        if (err instanceof FetchError) {
            // Handle 429 rate limit error
            if (err.statusCode === 429) {
                const detail = err.data?.detail || ''
                const secondsMatch = detail.match(/(\d+)\s*seconds?/)
                const waitSeconds = secondsMatch ? secondsMatch[1] : '60'
                
                toast.error(t('forgotPassword.rateLimitError', { seconds: waitSeconds }))
            } else if (err.statusCode === 400 && err.data?.detail === 'FORGOT_PASSWORD_INVALID_EMAIL') {
                toast.error(t('forgotPassword.emailNotFound'))
            } else {
                toast.error(t('forgotPassword.sendFailed'))
            }
        } else {
            toast.error(t('forgotPassword.sendFailed'))
        }
    } finally {
        loading.value = false
    }
}

onUnmounted(() => {
    if (countdownTimer) {
        clearInterval(countdownTimer)
    }
})
</script>

<template>
    <div class="flex flex-col gap-6">
        <div class="flex flex-col items-center gap-2 text-center">
            <h1 class="text-2xl font-bold">{{ $t('forgotPassword.title') }}</h1>
            <p class="text-balance text-sm text-muted-foreground">
                {{ $t('forgotPassword.description') }}
            </p>
        </div>

        <div v-if="success" class="p-3 text-sm text-green-600 bg-green-50 border border-green-200 rounded-md">
            {{ $t('forgotPassword.successMessage', { email }) }}
        </div>

        <div class="space-y-4">
            <div class="space-y-2">
                <label for="email" class="text-sm font-medium">
                    {{ $t('forgotPassword.emailLabel') }}
                </label>
                <input
                    id="email"
                    v-model="email"
                    type="email"
                    :placeholder="$t('forgotPassword.emailPlaceholder')"
                    class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    @keyup.enter="requestPasswordReset"
                />
            </div>

            <Button
                type="button"
                class="w-full"
                :disabled="loading || resendCountdown > 0"
                @click="requestPasswordReset"
            >
                <span v-if="loading" class="flex items-center gap-2">
                    <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    {{ $t('forgotPassword.sending') }}
                </span>
                <span v-else-if="resendCountdown > 0">
                    {{ $t('forgotPassword.resendCountdown', { seconds: resendCountdown }) }}
                </span>
                <span v-else>
                    {{ $t('forgotPassword.sendButton') }}
                </span>
            </Button>

            <div class="text-center">
                <Button type="button" variant="link" @click="navigateTo('/sign-in')">
                    {{ $t('forgotPassword.backToLogin') }}
                </Button>
            </div>
        </div>
    </div>
</template>

<style scoped>
</style>
