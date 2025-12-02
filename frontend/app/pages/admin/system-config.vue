<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'
import { Button } from '~/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card'
import { Input } from '~/components/ui/input'
import { Label } from '~/components/ui/label'
import { Switch } from '~/components/ui/switch'
import { Alert, AlertDescription, AlertTitle } from '~/components/ui/alert'
import type { SystemConfigItem, SystemConfigListResponse } from '~/types/api'

const TITLE_MODEL_KEY = 'conversation_title_model_id'
const ALLOW_CREATE_ASSISTANTS_KEY = 'allow_user_create_assistants'
const REGISTRATION_ENABLED_KEY = 'registration_enabled'

definePageMeta({
	layout: 'admin',
	breadcrumb: () => useI18n().t('admin.systemConfig.title')
})

const { t } = useI18n()
const { showError, showSuccess } = useNotifications()
const { $api } = useNuxtApp()

const {
	data,
	pending,
	error,
	refresh
} = await useAPI<SystemConfigListResponse>('/v1/admin/config', { server: false })

const configs = computed<SystemConfigItem[]>(() => data.value?.configs ?? [])

// Title Model Config
const titleModelConfig = computed(() => configs.value.find(cfg => cfg.key === TITLE_MODEL_KEY))
const titleModelId = ref('')

// Allow Create Assistants Config
const allowCreateAssistantsConfig = computed(() => configs.value.find(cfg => cfg.key === ALLOW_CREATE_ASSISTANTS_KEY))
const allowCreateAssistants = ref(true)

// Registration Config
const registrationEnabledConfig = computed(() => configs.value.find(cfg => cfg.key === REGISTRATION_ENABLED_KEY))
const registrationEnabled = ref(true)

// Unified watcher for all configs
watch(configs, (newConfigs) => {
	// Update Title Model
	const titleConfig = newConfigs.find(cfg => cfg.key === TITLE_MODEL_KEY)
	titleModelId.value = typeof titleConfig?.value === 'string' ? titleConfig.value : ''

	// Update Allow Create Assistants
	const allowConfig = newConfigs.find(cfg => cfg.key === ALLOW_CREATE_ASSISTANTS_KEY)
	if (!allowConfig) {
		allowCreateAssistants.value = true
	} else {
		allowCreateAssistants.value = String(allowConfig.value).toLowerCase() !== 'false'
	}

	// Update Registration
	const regConfig = newConfigs.find(cfg => cfg.key === REGISTRATION_ENABLED_KEY)
	if (!regConfig) {
		registrationEnabled.value = true
	} else {
		registrationEnabled.value = String(regConfig.value).toLowerCase() !== 'false'
	}
}, { immediate: true })

const isSaving = ref(false)

const handleSaveTitleModel = async () => {
	const trimmed = titleModelId.value.trim()
	if (!trimmed) {
		showError(t('admin.systemConfig.messages.modelIdRequired'))
		return
	}

	isSaving.value = true
	try {
		const payload = titleModelConfig.value
			? { value: trimmed, is_enabled: true }
			: {
					key: TITLE_MODEL_KEY,
					value: trimmed,
					description: t('admin.systemConfig.titleModel.heading'),
					is_public: false,
					is_enabled: true
				}
		const url = titleModelConfig.value
			? `/v1/admin/config/${TITLE_MODEL_KEY}`
			: '/v1/admin/config'
		const method = titleModelConfig.value ? 'PUT' : 'POST'

		await $api(url, {
			method,
			body: payload
		})

		await refresh()
		showSuccess(t('admin.systemConfig.messages.saveSuccess'))
	} catch (err) {
		console.error('Failed to save system config', err)
		showError(t('admin.systemConfig.messages.saveFailed'))
	} finally {
		isSaving.value = false
	}
}

const handleSaveAllowCreateAssistants = async (value: boolean) => {
	isSaving.value = true
	try {
		const payload = allowCreateAssistantsConfig.value
			? { value: value, is_enabled: true }
			: {
					key: ALLOW_CREATE_ASSISTANTS_KEY,
					value: value,
					                                     description: t('admin.systemConfig.assistants.configDescription'),
					is_public: true,
					is_enabled: true
				}
		const url = allowCreateAssistantsConfig.value
			? `/v1/admin/config/${ALLOW_CREATE_ASSISTANTS_KEY}`
			: '/v1/admin/config'
		const method = allowCreateAssistantsConfig.value ? 'PUT' : 'POST'

		await $api(url, {
			method,
			body: payload
		})

		await refresh()
		showSuccess(t('admin.systemConfig.messages.saveSuccess'))
	} catch (err: any) {
		showError(err.message || t('admin.systemConfig.messages.saveFailed'))
		// Revert on error
		allowCreateAssistants.value = !value
	} finally {
		isSaving.value = false
	}
}

const handleSaveRegistrationEnabled = async (value: boolean) => {
	isSaving.value = true
	try {
		const payload = registrationEnabledConfig.value
			? { value: value, is_enabled: true }
			: {
					key: REGISTRATION_ENABLED_KEY,
					value: value,
					description: t('admin.systemConfig.registration.configDescription'),
					is_public: true,
					is_enabled: true
				}
		const url = registrationEnabledConfig.value
			? `/v1/admin/config/${REGISTRATION_ENABLED_KEY}`
			: '/v1/admin/config'
		const method = registrationEnabledConfig.value ? 'PUT' : 'POST'

		await $api(url, {
			method,
			body: payload
		})

		await refresh()
		showSuccess(t('admin.systemConfig.messages.saveSuccess'))
	} catch (err: any) {
		showError(err.message || t('admin.systemConfig.messages.saveFailed'))
		// Revert on error
		registrationEnabled.value = !value
	} finally {
		isSaving.value = false
	}
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

		<Card>
			<CardHeader>
				<CardTitle>{{ t('admin.systemConfig.registration.title') }}</CardTitle>
				<CardDescription>
					{{ t('admin.systemConfig.registration.description') }}
				</CardDescription>
			</CardHeader>
			<CardContent>
				<div class="flex items-center space-x-2">
					<Switch
						id="registration-enabled"
						:model-value="registrationEnabled"
						@update:model-value="handleSaveRegistrationEnabled"
						:disabled="isSaving"
					/>
					<Label for="registration-enabled">{{ t('admin.systemConfig.registration.enabledLabel') }}</Label>
				</div>
			</CardContent>
		</Card>

		<Card>
			<CardHeader>
				<CardTitle>{{ t('admin.systemConfig.assistants.title') }}</CardTitle>
				<CardDescription>
					{{ t('admin.systemConfig.assistants.description') }}
				</CardDescription>
			</CardHeader>
			<CardContent>
				<div class="flex items-center space-x-2">
					<Switch
						id="allow-create-assistants"
						:model-value="allowCreateAssistants"
						@update:model-value="handleSaveAllowCreateAssistants"
						:disabled="isSaving"
					/>
					<Label for="allow-create-assistants">{{ t('admin.systemConfig.assistants.allowCreateLabel') }}</Label>
				</div>
			</CardContent>
		</Card>

		<Card>
			<CardHeader>
				<CardTitle>{{ t('admin.systemConfig.titleModel.heading') }}</CardTitle>
				<CardDescription>
					{{ t('admin.systemConfig.description') }}
				</CardDescription>
			</CardHeader>
			<CardContent>
				<form class="space-y-4" @submit.prevent="handleSaveTitleModel">
					<div class="space-y-2">
						<Label for="title-model-id">{{ t('admin.systemConfig.titleModel.label') }}</Label>
						<Input
							id="title-model-id"
							v-model="titleModelId"
							:placeholder="t('admin.systemConfig.titleModel.placeholder')"
						/>
						<p class="text-sm text-muted-foreground">
							{{ t('admin.systemConfig.titleModel.helper') }}
						</p>
					</div>
					<div class="flex flex-wrap gap-2">
						<Button type="submit" :disabled="isSaving">
							<Loader2 v-if="isSaving" class="mr-2 h-4 w-4 animate-spin" />
							{{ t(titleModelConfig ? 'admin.systemConfig.actions.save' : 'admin.systemConfig.actions.create') }}
						</Button>
					</div>
				</form>
			</CardContent>
		</Card>
	</div>
</template>
