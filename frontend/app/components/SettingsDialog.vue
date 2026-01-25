<script setup lang="ts">
import { Loader2, Smartphone } from "lucide-vue-next"
import { toTypedSchema } from "@vee-validate/zod"
import * as z from "zod"
import { toast } from "vue-sonner"
import UserBindingList from '~/components/channels/UserBindingList.vue'

const { $api } = useNuxtApp()
const { t } = useI18n()

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
}>()

const activeTab = ref('profile')

const userStore = useUserStore()
const hasChanges = ref(false)

const formSchema = toTypedSchema(z.object({
  nickname: z.string().max(50, t('profile.nicknameMaxLength'))
    .optional().nullable(),
  avatar_url: z.string().optional(),
}))

// Check if the form has changes
function checkForChanges(values: any) {
  const user = userStore.user
  if (!user) {
    hasChanges.value = false
    return
  }

  // Compare each field for changes (including non-empty to empty)
  const changed = (
    (values.nickname || '') !== (user.name || '') ||
    (values.avatar_url || '') !== (user.avatar_url || '')
  )

  hasChanges.value = changed
}

const loading = ref(false)

// Add initial values computed property
const initialValues = computed(() => {
  const user = userStore.user
  if (!user) return {}

  return {
    nickname: user.name || '',
    avatar_url: user.avatar_url || ''
  }
})

async function onSubmit(values: any) {
  loading.value = true
  try {
    // Prepare update data, include all fields (including empty values)
    const updateData = {
      nickname: values.nickname || '',
      avatar_url: values.avatar_url || ''
    }

    const response = await $api('/api/v1/users/profile', {
      method: 'PUT',
      body: updateData
    })

    // Update user store with new data
    await userStore.fetchUser()

    // Reset changes state
    hasChanges.value = false

    toast.success(t('profile.updateSuccess'))
  } catch (error) {
    console.error('Failed to update profile:', error)
    toast.error(t('profile.updateFailed'))
  } finally {
    loading.value = false
  }
}

// Change password related
const passwordFormSchema = toTypedSchema(z.object({
  old_password: z.string().min(1, t('profile.security.oldPasswordRequired')),
  new_password: z.string().min(8, t('profile.security.passwordMinLength')),
  confirm_password: z.string().min(1, t('profile.security.confirmPasswordRequired'))
}).refine((data: any) => data.new_password === data.confirm_password, {
  message: t('profile.security.passwordMismatch'),
  path: ['confirm_password']
}))

const passwordLoading = ref(false)

async function onPasswordSubmit(values: any) {
  passwordLoading.value = true
  try {
    await $api('/v1/auth/change-password', {
      method: 'POST',
      body: {
        old_password: values.old_password,
        new_password: values.new_password
      }
    })

    toast.success(t('profile.security.passwordChangeSuccess'))
    
    // Reset the form
    values.old_password = ''
    values.new_password = ''
    values.confirm_password = ''
  } catch (error: any) {
    console.error('Failed to change password:', error)
    
    // Handle specific errors
    if (error?.data?.detail === 'CHANGE_PASSWORD_INCORRECT_OLD_PASSWORD') {
      toast.error(t('profile.security.incorrectOldPassword'))
    } else if (error?.data?.detail?.code === 'CHANGE_PASSWORD_INVALID_PASSWORD') {
      toast.error(t('profile.security.invalidPassword') + ': ' + error.data.detail.reason)
    } else {
      toast.error(t('profile.security.passwordChangeFailed'))
    }
  } finally {
    passwordLoading.value = false
  }
}
</script>

<template>
  <Dialog :open="open" @update:open="emit('update:open', $event)">
    <DialogContent class="sm:max-w-[700px] max-h-[85vh] p-0">
      <DialogHeader class="px-6 pt-6 pb-4">
        <DialogTitle>{{ $t('nav.settings') }}</DialogTitle>
        <DialogDescription>
          {{ $t('settings.description') }}
        </DialogDescription>
      </DialogHeader>
      
      <div class="flex min-h-[400px]">
        <!-- Left tab navigation -->
        <div class="w-48 border-r bg-muted/10 p-4">
          <nav class="flex flex-col gap-2">
            <button
              @click="activeTab = 'profile'"
              :class="[
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors text-left',
                activeTab === 'profile'
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:bg-background/50 hover:text-foreground'
              ]"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
              {{ $t('profile.tabs.profile') }}
            </button>

            <button
              @click="activeTab = 'preferences'"
              :class="[
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors text-left',
                activeTab === 'preferences'
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:bg-background/50 hover:text-foreground'
              ]"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              {{ $t('profile.tabs.preferences') }}
            </button>
            
            <button
              @click="activeTab = 'security'"
              :class="[
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors text-left',
                activeTab === 'security'
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:bg-background/50 hover:text-foreground'
              ]"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect width="18" height="11" x="3" y="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
              {{ $t('profile.tabs.security') }}
            </button>

            <button
              @click="activeTab = 'channels'"
              :class="[
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors text-left',
                activeTab === 'channels'
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:bg-background/50 hover:text-foreground'
              ]"
            >
              <Smartphone class="w-4 h-4" />
              {{ $t('channels.title') }}
            </button>
          </nav>
        </div>

        <!-- Right content area -->
        <div class="flex-1 overflow-y-auto px-6 py-4">
          <!-- Profile -->
          <div v-if="activeTab === 'profile'" class="space-y-6">
            <Form v-slot="{ handleSubmit, values }" as="" keep-values :validation-schema="formSchema"
              :initial-values="initialValues">
              <form id="profileForm" @submit="handleSubmit($event, onSubmit)" class="space-y-4">
                <FormField v-slot="{ componentField }" name="avatar_url">
                  <FormItem>
                    <FormLabel>{{ $t('profile.avatar') }}</FormLabel>
                    <FormControl>
                      <AvatarUpload 
                        :model-value="componentField.modelValue || ''"
                        :initial-url="userStore.user?.avatar_url || ''"
                        @update:model-value="(val) => {
                          componentField['onUpdate:modelValue']?.(val)
                          checkForChanges({ ...values, avatar_url: val })
                        }"
                      />
                    </FormControl>
                    <FormDescription>
                      {{ $t('profile.avatarDescription') }}
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                </FormField>
                
                <FormField v-slot="{ componentField }" name="nickname">
                  <FormItem>
                    <FormLabel>{{ $t('profile.nickname') }}</FormLabel>
                    <FormControl>
                      <Input type="text" :placeholder="$t('profile.nicknamePlaceholder')" v-bind="componentField" @input="checkForChanges(values)" />
                    </FormControl>
                    <FormDescription>
                      {{ $t('profile.nicknameDescription') }}
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                </FormField>

                <div class="flex justify-end pt-4">
                  <Button type="submit" :disabled="!hasChanges || loading">
                    <Loader2 v-if="loading" class="w-4 h-4 mr-2 animate-spin" />
                    {{ loading ? $t('common.updating') : $t('common.saveChanges') }}
                  </Button>
                </div>
              </form>
            </Form>
          </div>

          <!-- Preferences -->
          <div v-if="activeTab === 'preferences'" class="space-y-6">
            <div class="space-y-2">
              <h3 class="text-sm font-medium">{{ $t('profile.preferences.language') }}</h3>
              <p class="text-sm text-muted-foreground">{{ $t('profile.preferences.languageDescription') }}</p>
              <LanguageSelector />
            </div>

            <div class="space-y-2">
              <h3 class="text-sm font-medium">{{ $t('profile.preferences.theme') }}</h3>
              <p class="text-sm text-muted-foreground">{{ $t('profile.preferences.themeDescription') }}</p>
              <ColorModeSelector />
            </div>
          </div>

          <!-- Account Security -->
          <div v-if="activeTab === 'security'">
            <Form v-slot="{ handleSubmit, values, resetForm }" as="" :validation-schema="passwordFormSchema">
              <form @submit="handleSubmit($event, async (vals: any) => { await onPasswordSubmit(vals); resetForm(); })" class="space-y-4">
                <div class="space-y-2 mb-4">
                  <h3 class="text-sm font-medium">{{ $t('profile.security.changePassword') }}</h3>
                  <p class="text-sm text-muted-foreground">{{ $t('profile.security.changePasswordDescription') }}</p>
                </div>

                <FormField v-slot="{ componentField }" name="old_password">
                  <FormItem>
                    <FormLabel>{{ $t('profile.security.oldPassword') }}</FormLabel>
                    <FormControl>
                      <Input type="password" :placeholder="$t('profile.security.oldPasswordPlaceholder')" v-bind="componentField" autocomplete="current-password" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                </FormField>

                <FormField v-slot="{ componentField }" name="new_password">
                  <FormItem>
                    <FormLabel>{{ $t('profile.security.newPassword') }}</FormLabel>
                    <FormControl>
                      <Input type="password" :placeholder="$t('profile.security.newPasswordPlaceholder')" v-bind="componentField" autocomplete="new-password" />
                    </FormControl>
                    <FormDescription>
                      {{ $t('profile.security.passwordRequirement') }}
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                </FormField>

                <FormField v-slot="{ componentField }" name="confirm_password">
                  <FormItem>
                    <FormLabel>{{ $t('profile.security.confirmPassword') }}</FormLabel>
                    <FormControl>
                      <Input type="password" :placeholder="$t('profile.security.confirmPasswordPlaceholder')" v-bind="componentField" autocomplete="new-password" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                </FormField>

                <div class="flex justify-end pt-4">
                  <Button type="submit" :disabled="passwordLoading">
                    <Loader2 v-if="passwordLoading" class="w-4 h-4 mr-2 animate-spin" />
                    {{ passwordLoading ? $t('common.updating') : $t('profile.security.changePasswordButton') }}
                  </Button>
                </div>
              </form>
            </Form>
          </div>

          <!-- Channels -->
          <div v-if="activeTab === 'channels'" class="space-y-6">
              <UserBindingList />
          </div>
        </div>
      </div>
    </DialogContent>
  </Dialog>
</template>
