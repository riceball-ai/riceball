<script setup lang="ts">
import { cn } from '@/lib/utils'
import { FetchError } from 'ofetch'
import type { OAuthProvider } from '~/types/api';
import { toast } from "vue-sonner"
import { useRoute } from 'vue-router'

const props = defineProps<{
  scene: 'sign-in' | 'sign-up'
  redirectUrl?: string
}>()

const { $api } = useNuxtApp()
const configStore = useConfigStore()
const runtimeConfig = useRuntimeConfig()

const siteName = computed(() => configStore.config.site_title || runtimeConfig.public.appName)

// Form data
const formData = reactive({
  email: '',
  password: ''
})

// State management
const loading = ref(false)
const error = ref('')

const { t } = useI18n()
const { locale } = useI18n()
const route = useRoute()

const signup = async () => {
  if (!formData.email || !formData.password) {
    error.value = t('auth.fillAllFields')
    return
  }

  loading.value = true
  error.value = ''

  try {
    // Get current language and normalize (zh-Hans -> zh, en-US -> en)
    const userLanguage = locale.value.split('-')[0]
    
    // Call register API directly, backend will send activation link
    await $api('/v1/auth/register', {
      method: 'POST',
      body: {
        email: formData.email,
        password: formData.password,
        language: userLanguage,  // Pass user language preference
      }
    })
    
    // Registration successful, redirect to email verification page
    return await navigateToVerifyEmail()
  } catch (err) {
    if (!(err instanceof FetchError)) throw err;
    if (err.statusCode === 400 && err.data?.detail === 'REGISTER_USER_ALREADY_EXISTS') {
      // User already exists, prompt user to login
      error.value = t('auth.emailAlreadyExists')
      return
    }

    // Other errors
    error.value = t('auth.registrationFailed')
  } finally {
    loading.value = false
  }
}

const getRedirectPath = () => {
  const fallback = '/assistants'
  return props.redirectUrl && props.redirectUrl.length > 0
      ? props.redirectUrl
      : fallback
}

// Login
const login = async () => {
  loading.value = true
  error.value = ''

  try {
    const body = new URLSearchParams({
      username: formData.email,
      password: formData.password,
    })
    const response = await $api('/v1/auth/login', {
      method: 'POST',
      body,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    })

    // Redirect after successful login
    await navigateTo(getRedirectPath())
  } catch (err: any) {
    if (!(err instanceof FetchError)) throw err;

    if (err.statusCode === 400 && err.data?.detail === 'LOGIN_USER_NOT_VERIFIED') {
      return await navigateToVerifyEmail()
    } else if (err.statusCode === 400 && err.data?.detail === 'LOGIN_BAD_CREDENTIALS') {
      // Bad credentials or the user is inactive
      error.value = t('auth.invalidCredentials')
      return
    }
    error.value = t('auth.loginFailed')
  } finally {
    loading.value = false
  }
}


const navigateToVerifyEmail = async () => {
  await navigateTo(`/verify-email?email=${encodeURIComponent(formData.email)}`)
}

// Handle form submission
const handleSubmit = async () => {
  if (props.scene === 'sign-up') {
    // Sign up mode
    await signup()
  } else {
    // Sign in mode
    await login()
  }
}

const socialLoginLoadingProvider = ref<string | null>(null)

// Social login
const handleSocialLogin = (provider: string) => {
  if (socialLoginLoadingProvider.value) return // Prevent duplicate clicks
  
  socialLoginLoadingProvider.value = provider
  const callbackUrl = window.location.origin + getRedirectPath()
  // Redirect to social login provider
  $api<{authorization_url: string}>(`/v1/oauth/${provider}/authorize`, {
    method: 'POST',
    body: {
      redirect_uri: callbackUrl
    }
  }).then(res => {
    if (res.authorization_url) {
      window.location.href = res.authorization_url
      // Keep loading state on successful redirect, do not clear
    } else {
      toast.error(t('auth.gettingAuthUrl'))
      socialLoginLoadingProvider.value = null
    }
  }).catch((err: any) => {
    toast.error(t('auth.gettingAuthUrl'))
    socialLoginLoadingProvider.value = null
  })
}

// Toggle mode
const toggleMode = () => {
  if (props.scene === 'sign-in') {
    navigateTo('/sign-up')
  } else {
    navigateTo('/sign-in')
  }
}

const loadingConfig = computed(() => !configStore.isLoaded)

const { data: authProviders } = useAPI<OAuthProvider[]>('/v1/oauth/providers')

const isFormValid = computed(() => {
  const email = formData.email?.trim()
  const password = formData.password?.trim()
  if (!email || !password) {
    return false
  }
  return true
})

</script>

<template>
  <form @submit.prevent="handleSubmit" :class="cn('flex flex-col gap-6')">
    <div class="flex flex-col items-center gap-2 text-center">
      <h1 class="text-2xl font-bold">
        {{ props.scene === 'sign-up' ? $t('auth.signUpTitle') : $t('auth.signInTitle') }}
      </h1>
      <p class="text-balance text-sm text-muted-foreground">
      </p>
    </div>

    <!-- Error message -->
    <div v-if="error" class="p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md">
      {{ error }}
    </div>

    <!-- Loading state -->
    <div v-if="loadingConfig" class="flex justify-center py-4">
      <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
    </div>

    <div v-else class="grid gap-6">

      <!-- Social login -->
      <template v-if="authProviders && authProviders.length > 0">

        <div class="space-y-2">
          <Button v-for="provider in authProviders || []" :key="provider.id" type="button"
            :disabled="!!socialLoginLoadingProvider"
            variant="outline" class="w-full h-12 text-base" @click="handleSocialLogin(provider.name)">
            <div v-if="socialLoginLoadingProvider === provider.name" class="w-4 h-4 mr-2 border-2 border-current border-t-transparent rounded-full animate-spin" />
            <img v-else-if="provider.icon_url" :src="provider.icon_url" alt="icon" class="w-4 h-4 mr-2 rounded" />
            {{ $t(props.scene === 'sign-up' ? 'auth.signUpWithProvider' : 'auth.signInWithProvider', { provider: provider.display_name }) }}
          </Button>
        </div>

        <div
          class="relative text-center text-sm after:absolute after:inset-0 after:top-1/2 after:z-0 after:flex after:items-center after:border-t after:border-border">
          <span class="relative z-10 bg-background px-2 text-muted-foreground">
            {{ $t('common.or') }}
          </span>
        </div>
      </template>

      <!-- Regular sign in/sign up form -->
      <template v-if="!(props.scene === 'sign-up' && !configStore?.config.registration_enabled)">
        <div class="space-y-4">
          <div class="grid gap-2">
            <Label for="email">{{ $t('auth.email') }}</Label>
            <Input id="email" v-model="formData.email" type="email" :placeholder="$t('auth.emailPlaceholder')" required class="h-12 text-base" />
          </div>
          <div class="grid gap-2">
            <div class="flex items-center justify-between">
              <Label for="password">{{ $t('auth.password') }}</Label>
              <NuxtLink v-if="props.scene === 'sign-in'" to="/forgot-password" class="text-xs text-muted-foreground hover:text-primary underline-offset-4 hover:underline">
                {{ $t('auth.forgotPassword') }}
              </NuxtLink>
            </div>
            <Input id="password" v-model="formData.password" type="password" required class="h-12 text-base" />
          </div>

          <!-- Show terms agreement when signing up -->
          <div v-if="props.scene === 'sign-up'" class="text-xs text-center text-muted-foreground">
            <i18n-t keypath="auth.agreeTerms" tag="span" scope="global">
              <template #siteName>
                {{ siteName }}
              </template>
              <template #terms>
                <NuxtLink to="/terms" target="_blank" class="text-primary hover:underline">
                  {{ $t('auth.termsOfUse') }}
                </NuxtLink>
              </template>
              <template #privacy>
                <NuxtLink to="/privacy" target="_blank" class="text-primary hover:underline">
                  {{ $t('auth.privacyPolicy') }}
                </NuxtLink>
              </template>
            </i18n-t>
          </div>

          <Button type="submit" class="w-full h-12 text-base" :disabled="loading || !isFormValid">
            {{ loading ? $t('common.processing') : (props.scene === 'sign-up' ? $t('auth.signUp') : $t('auth.signIn')) }}
          </Button>
        </div>
      </template>
      
    </div>

    <!-- Toggle sign in/sign up -->
    <div v-if="!(props.scene === 'sign-in' && !configStore?.config.registration_enabled)" class="text-center text-sm">
      {{ props.scene === 'sign-up' ? $t('auth.hasAccount') : $t('auth.noAccount') }}
      <button type="button" @click="toggleMode" class="underline underline-offset-4 hover:text-primary">
        {{ props.scene === 'sign-up' ? $t('auth.signInNow') : $t('auth.signUpNow') }}
      </button>
    </div>
  </form>
</template>

<style scoped>
</style>
