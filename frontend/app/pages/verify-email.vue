<script setup lang="ts">
import { FetchError } from 'ofetch'
import { toast } from "vue-sonner"

const { t } = useI18n()

definePageMeta({
    layout: 'auth'
})

useHead({
  title: t('pageTitle.verifyEmail')
})


const route = useRoute()
const { $api } = useNuxtApp()

// Get email and activation token from URL params
const email = ref(route.query.email as string || '')
const token = ref(route.query.token as string || '')
const loading = ref(false)
const success = ref('')
const error = ref('')

// Resend activation link related
const sendingEmail = ref(false)
const resendCountdown = ref(0)

// Countdown timer
let countdownTimer: ReturnType<typeof setInterval> | null = null

// Success redirect countdown
const redirectCountdown = ref(0)
let redirectTimer: ReturnType<typeof setInterval> | null = null

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

// Activate account (via activation link)
const activateAccount = async () => {
    if (!token.value) {
        toast.error(t('verifyEmail.invalidLink'))
        return
    }

    loading.value = true

    try {
        await $api('/v1/auth/verify', {
            method: 'POST',
            body: { token: token.value }
        })

        success.value = t('verifyEmail.success')
        
        // Start countdown and redirect to sign-in page
        startRedirectCountdown()
    } catch (err) {
        if (!(err instanceof FetchError)) throw err;

        if (err.statusCode === 400 && err.data?.detail === 'VERIFY_USER_ALREADY_VERIFIED') {
            success.value = t('verifyEmail.alreadyVerified')
            startRedirectCountdown()
        } else {
            error.value = t('verifyEmail.failed')
        }
    } finally {
        loading.value = false
    }
}

// Resend activation link
const resendActivationEmail = async () => {
    if (!email.value) {
        toast.error(t('verifyEmail.missingEmail'))
        return
    }

    // Simple email format validation
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailPattern.test(email.value)) {
        toast.error(t('verifyEmail.invalidEmailFormat'))
        return
    }

    sendingEmail.value = true

    try {
        await $api('/v1/auth/request-verify-token', {
            method: 'POST',
            body: { email: email.value }
        })

        // Show success message and start countdown
        toast.success(t('verifyEmail.resendSuccess'))
        startResendCountdown()
    } catch (err) {
        if (err instanceof FetchError) {
            // Handle 429 rate limit error
            if (err.statusCode === 429) {
                const detail = err.data?.detail || ''
                // Try to extract wait time (seconds) from error message
                const secondsMatch = detail.match(/(\d+)\s*seconds?/)
                const waitSeconds = secondsMatch ? secondsMatch[1] : '60'
                
                toast.error(t('verifyEmail.rateLimitError', { seconds: waitSeconds }))
            } else {
                toast.error(err.data?.message || t('verifyEmail.resendFailed'))
            }
        } else {
            toast.error(t('verifyEmail.resendFailed'))
        }
    } finally {
        sendingEmail.value = false
    }
}

// Auto process activation link
onMounted(() => {
    if (token.value) {
        activateAccount()
    } else if (email.value) {
        resendActivationEmail()
    }
})

onUnmounted(() => {
    if (countdownTimer) {
        clearInterval(countdownTimer)
    }
    if (redirectTimer) {
        clearInterval(redirectTimer)
    }
})
</script>

<template>
    <div class="flex flex-col gap-6">
        <div class="flex flex-col items-center gap-2 text-center">
            <h1 class="text-2xl font-bold">{{ $t('verifyEmail.title') }}</h1>
            <p class="text-balance text-sm text-muted-foreground">
                <span v-if="loading">{{ $t('verifyEmail.verifying') }}</span>
                <span v-else-if="email">{{ $t('verifyEmail.sentTo', { email }) }}</span>
                <span v-else>{{ $t('verifyEmail.processing') }}</span>
            </p>
        </div>

        <div v-if="success" class="p-3 text-sm text-green-600 bg-green-50 border border-green-200 rounded-md">
            {{ success }}
            <p class="mt-2 text-xs">{{ $t('verifyEmail.autoRedirect', { seconds: redirectCountdown }) }}</p>
        </div>

        <!-- Error message -->
        <div v-if="error" class="p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md">
            {{ error }}
        </div>

        <!-- Loading state -->
        <div v-if="loading" class="flex justify-center py-4">
            <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
        </div>

        <!-- If no token, show prompt info -->
        <div v-if="!token && !loading" class="space-y-4">
            <div class="text-center">
                <p class="text-sm text-muted-foreground">
                    {{ $t('verifyEmail.resendPrompt') }}
                </p>
            </div>

            <!-- If email exists: show resend button directly -->
            <div v-if="email" class="space-y-2">
                <Button
                    type="button"
                    class="w-full"
                    :disabled="sendingEmail || resendCountdown > 0"
                    @click="resendActivationEmail"
                >
                    <template v-if="resendCountdown > 0">{{ $t('verifyEmail.resendCountdown', { seconds: resendCountdown }) }}</template>
                    <template v-else>{{ $t('verifyEmail.resendButton') }}</template>
                </Button>
                <p class="text-xs text-muted-foreground text-center">
                    {{ $t('verifyEmail.checkSpam') }}
                </p>
            </div>

            <!-- If no email: show input for user to enter email and resend -->
            <div v-else class="space-y-2">
                <div class="space-y-2">
                    <input
                        v-model="email"
                        type="email"
                        :placeholder="$t('verifyEmail.enterEmail')"
                        class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    />
                    <Button
                        type="button"
                        class="w-full"
                        :disabled="sendingEmail || resendCountdown > 0"
                        @click="resendActivationEmail"
                    >
                        <template v-if="resendCountdown > 0">{{ $t('verifyEmail.resendCountdown', { seconds: resendCountdown }) }}</template>
                        <template v-else>{{ $t('verifyEmail.sendActivation') }}</template>
                    </Button>
                </div>
                <p class="text-xs text-muted-foreground text-center">
                    {{ $t('verifyEmail.enterEmailPrompt') }}
                </p>
            </div>

            <Button type="button" variant="outline" @click="navigateTo('/sign-up')" class="w-full">
                {{ $t('verifyEmail.backToSignUp') }}
            </Button>
        </div>
    </div>
</template>
