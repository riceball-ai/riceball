<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'
import { Button } from '~/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card'
import { Input } from '~/components/ui/input'
import { Label } from '~/components/ui/label'
import { Switch } from '~/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '~/components/ui/tabs'
import { Alert, AlertDescription, AlertTitle } from '~/components/ui/alert'
import type { SystemConfigListResponse, SystemConfigItem } from '~/types/api'

definePageMeta({
  layout: 'admin',
  breadcrumb: 'admin.systemConfig.title'
})

const { t } = useI18n()
const { showError, showSuccess } = useNotifications()
const { $api } = useNuxtApp()

const isSaving = ref(false)

// API Data
const {
  data,
  error,
  refresh
} = await useAPI<SystemConfigListResponse>('/v1/admin/config', { server: false })

const configs = computed(() => data.value?.configs ?? [])

// Group configs by config_group
const groupedConfigs = computed(() => {
  const groups: Record<string, SystemConfigItem[]> = {}
  configs.value.forEach(config => {
    const group = config.config_group || 'general'
    if (!groups[group]) {
      groups[group] = []
    }
    groups[group].push(config)
  })
  return groups
})

const groupOrder = ['branding', 'security', 'ai', 'general']
const sortedGroups = computed(() => {
  return Object.keys(groupedConfigs.value).sort((a, b) => {
    const indexA = groupOrder.indexOf(a)
    const indexB = groupOrder.indexOf(b)
    if (indexA === -1 && indexB === -1) return a.localeCompare(b)
    if (indexA === -1) return 1
    if (indexB === -1) return -1
    return indexA - indexB
  })
})

// Generic Save Handler
const updateConfig = async (config: SystemConfigItem, newValue: any) => {
  isSaving.value = true
  try {
    await $api(`/v1/admin/config/${config.key}`, {
      method: 'PUT',
      body: { 
        value: newValue,
        is_enabled: true
      }
    })
    showSuccess(t('common.saveSuccess'))
    refresh()
  } catch (err: any) {
    showError(err)
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-3xl font-bold tracking-tight">{{ $t('admin.systemConfig.title') }}</h1>
    </div>

    <Alert v-if="error" variant="destructive">
      <AlertTitle>Error</AlertTitle>
      <AlertDescription>{{ error }}</AlertDescription>
    </Alert>

    <div v-else-if="!configs.length" class="flex justify-center py-8">
      <Loader2 class="h-8 w-8 animate-spin text-muted-foreground" />
    </div>

    <Tabs v-else :default-value="sortedGroups[0]" class="space-y-4">
      <TabsList>
        <TabsTrigger v-for="group in sortedGroups" :key="group" :value="group" class="capitalize">
          {{ group }}
        </TabsTrigger>
      </TabsList>

      <TabsContent v-for="group in sortedGroups" :key="group" :value="group" class="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle class="capitalize">{{ group }} Settings</CardTitle>
            <CardDescription>Manage your {{ group }} configuration.</CardDescription>
          </CardHeader>
          <CardContent class="space-y-6">
            <div v-for="config in groupedConfigs[group]" :key="config.key" class="grid gap-2">
              
              <!-- Boolean Type -->
              <div v-if="config.config_type === 'boolean'" class="flex items-center justify-between space-x-2">
                <div class="space-y-0.5">
                  <Label :for="config.key">{{ config.label || config.key }}</Label>
                  <p class="text-sm text-muted-foreground">{{ config.description }}</p>
                </div>
                <Switch
                  :id="config.key"
                  :model-value="String(config.value).toLowerCase() !== 'false'"
                  :disabled="isSaving"
                  @update:model-value="(val) => updateConfig(config, val)"
                />
              </div>

              <!-- Text/Image Type -->
              <div v-else class="space-y-2">
                <Label :for="config.key">{{ config.label || config.key }}</Label>
                <div class="flex gap-2">
                  <Input
                    :id="config.key"
                    :model-value="config.value"
                    :disabled="isSaving"
                    @change="(e: Event) => updateConfig(config, (e.target as HTMLInputElement).value)"
                  />
                </div>
                <p class="text-sm text-muted-foreground">{{ config.description }}</p>
                
                <!-- Image Preview -->
                <div v-if="config.config_type === 'image' && config.value" class="mt-2">
                  <img :src="config.value" class="h-12 w-auto rounded border p-1" alt="Preview" />
                </div>
              </div>

            </div>
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  </div>
</template>
