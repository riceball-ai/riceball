<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'
import { Button } from '~/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card'
import { Input } from '~/components/ui/input'
import { Label } from '~/components/ui/label'
import { Switch } from '~/components/ui/switch'
import { Alert, AlertDescription, AlertTitle } from '~/components/ui/alert'
import type { SystemConfigListResponse } from '~/types/api'

definePageMeta({
  layout: 'admin',
  breadcrumb: 'admin.systemConfig.title'
})

const { t } = useI18n()
const { showError, showSuccess } = useNotifications()
const { $api } = useNuxtApp()

// Configuration Definitions
const BOOLEAN_CONFIGS = [
  {
    key: 'registration_enabled',
    titleKey: 'admin.systemConfig.registration.title',
    descKey: 'admin.systemConfig.registration.description',
    labelKey: 'admin.systemConfig.registration.enabledLabel',
    configDescKey: 'admin.systemConfig.registration.configDescription',
    isPublic: true,
    defaultValue: true
  },
  {
    key: 'allow_user_create_assistants',
    titleKey: 'admin.systemConfig.assistants.title',
    descKey: 'admin.systemConfig.assistants.description',
    labelKey: 'admin.systemConfig.assistants.allowCreateLabel',
    configDescKey: 'admin.systemConfig.assistants.configDescription',
    isPublic: true,
    defaultValue: true
  }
] as const

const TITLE_MODEL_KEY = 'conversation_title_model_id'

// State
const configState = reactive<Record<string, any>>({
  [TITLE_MODEL_KEY]: '',
  ...Object.fromEntries(BOOLEAN_CONFIGS.map(c => [c.key, c.defaultValue]))
})

const isSaving = ref(false)

// API Data
const {
  data,
  error,
  refresh
} = await useAPI<SystemConfigListResponse>('/v1/admin/config', { server: false })

const configs = computed(() => data.value?.configs ?? [])

// Watcher to sync state from API
watch(configs, (newConfigs) => {
  // Sync Boolean Configs
  BOOLEAN_CONFIGS.forEach(def => {
    const cfg = newConfigs.find(c => c.key === def.key)
    // Only use config value if it exists AND is enabled
    if (cfg && cfg.is_enabled) {
      configState[def.key] = String(cfg.value).toLowerCase() !== 'false'
    } else {
      configState[def.key] = def.defaultValue
    }
  })

  // Sync Title Model
  const titleCfg = newConfigs.find(c => c.key === TITLE_MODEL_KEY)
  configState[TITLE_MODEL_KEY] = (titleCfg?.is_enabled && titleCfg?.value as string) || ''
}, { immediate: true })

// Generic Save Handler
const updateConfig = async (key: string, value: any, meta: { description: string, isPublic: boolean }) => {
  isSaving.value = true
  try {
    const existing = configs.value.find(c => c.key === key)
    const isUpdate = !!existing

    const payload = isUpdate
      ? { value, is_enabled: true }
      : {
          key,
          value,
          description: meta.description,
          is_public: meta.isPublic,
          is_enabled: true
        }

    await $api(isUpdate ? `/v1/admin/config/${key}` : '/v1/admin/config', {
      method: isUpdate ? 'PUT' : 'POST',
      body: payload
    })

    await refresh()
    showSuccess(t('admin.systemConfig.messages.saveSuccess'))
  } catch (err: any) {
    console.error(`Failed to save config ${key}`, err)
    showError(err.message || t('admin.systemConfig.messages.saveFailed'))
    
    // Revert state on error for boolean toggles
    const original = configs.value.find(c => c.key === key)
    if (typeof value === 'boolean') {
       const def = BOOLEAN_CONFIGS.find(c => c.key === key)
       const defaultVal = def ? def.defaultValue : true
       configState[key] = original ? String(original.value).toLowerCase() !== 'false' : defaultVal
    }
  } finally {
    isSaving.value = false
  }
}

// Specific Handlers
const handleSwitchChange = (config: typeof BOOLEAN_CONFIGS[number], value: boolean) => {
  configState[config.key] = value
  updateConfig(config.key, value, {
    description: t(config.configDescKey),
    isPublic: config.isPublic
  })
}

const handleSaveTitleModel = () => {
  const value = (configState[TITLE_MODEL_KEY] as string).trim()
  if (!value) {
    showError(t('admin.systemConfig.messages.modelIdRequired'))
    return
  }
  
  updateConfig(TITLE_MODEL_KEY, value, {
    description: t('admin.systemConfig.titleModel.heading'),
    isPublic: false
  })
}
</script>

<template>
  <div class="space-y-6">
    <Alert v-if="error" variant="destructive">
      <AlertTitle>{{ t('common.error') }}</AlertTitle>
      <AlertDescription>
        {{ error?.message || t('admin.systemConfig.messages.saveFailed') }}
      </AlertDescription>
    </Alert>

    <!-- Boolean Configs -->
    <Card v-for="config in BOOLEAN_CONFIGS" :key="config.key">
      <CardHeader>
        <CardTitle>{{ t(config.titleKey) }}</CardTitle>
        <CardDescription>{{ t(config.descKey) }}</CardDescription>
      </CardHeader>
      <CardContent>
        <div class="flex items-center space-x-2">
          <Switch
            :id="config.key"
            :model-value="configState[config.key]"
            @update:model-value="(val) => handleSwitchChange(config, val)"
            :disabled="isSaving"
          />
          <Label :for="config.key">{{ t(config.labelKey) }}</Label>
        </div>
      </CardContent>
    </Card>

    <!-- Title Model Config -->
    <Card>
      <CardHeader>
        <CardTitle>{{ t('admin.systemConfig.titleModel.heading') }}</CardTitle>
        <CardDescription>{{ t('admin.systemConfig.description') }}</CardDescription>
      </CardHeader>
      <CardContent>
        <form class="space-y-4" @submit.prevent="handleSaveTitleModel">
          <div class="space-y-2">
            <Label for="title-model-id">{{ t('admin.systemConfig.titleModel.label') }}</Label>
            <Input
              id="title-model-id"
              v-model="configState[TITLE_MODEL_KEY]"
              :placeholder="t('admin.systemConfig.titleModel.placeholder')"
            />
            <p class="text-sm text-muted-foreground">
              {{ t('admin.systemConfig.titleModel.helper') }}
            </p>
          </div>
          <div class="flex flex-wrap gap-2">
            <Button type="submit" :disabled="isSaving">
              <Loader2 v-if="isSaving" class="mr-2 h-4 w-4 animate-spin" />
              {{ t('admin.systemConfig.actions.save') }}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  </div>
</template>
