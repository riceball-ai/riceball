<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Card, CardContent, CardHeader, CardTitle } from '~/components/ui/card'
import { Input } from '~/components/ui/input'
import { Label } from '~/components/ui/label'
import { Textarea } from '~/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '~/components/ui/select'
import { Switch } from '~/components/ui/switch'

import { Button } from '~/components/ui/button'

const { t } = useI18n()

interface ModelSettingsData {
  system_prompt: string
  model_id: string
  temperature: number
  max_history_messages: number | null
  model_parameters?: Record<string, any>
}

interface CommonOption {
  label: string
  value: string | number
  provider?: string
}

interface Props {
  modelValue: ModelSettingsData
  loading?: boolean
  modelOptions: CommonOption[]
  errors?: Record<string, string>
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  modelOptions: () => [],
  errors: () => ({})
})

const emit = defineEmits<{
  'update:modelValue': [value: ModelSettingsData]
}>()

const updateField = <K extends keyof ModelSettingsData>(key: K, value: ModelSettingsData[K]) => {
  const newValue = { ...props.modelValue, [key]: value }
  emit('update:modelValue', newValue)
}

// Max history toggle state
const enableMaxHistory = ref(false)

// Init enableMaxHistory based on prop
watch(() => props.modelValue.max_history_messages, (val) => {
  enableMaxHistory.value = val !== null && val !== undefined
}, { immediate: true })

const handleMaxHistoryToggle = (enabled: boolean) => {
  enableMaxHistory.value = enabled
  if (enabled) {
    if (props.modelValue.max_history_messages === undefined || props.modelValue.max_history_messages === null) {
      updateField('max_history_messages', 10)
    }
  } else {
    updateField('max_history_messages', null)
  }
}

// Advanced Parameters (JSON)
const showAdvanced = ref(false)
const modelParametersJson = ref('{}')
const jsonError = ref('')

// Initialize JSON string from prop
watch(() => props.modelValue.model_parameters, (val) => {
  if (val) {
    try {
      // Only update if structurally different to avoid cursor jumps
      const current = JSON.parse(modelParametersJson.value || '{}')
      if (JSON.stringify(current) !== JSON.stringify(val)) {
        modelParametersJson.value = JSON.stringify(val, null, 2)
      }
    } catch {
      modelParametersJson.value = JSON.stringify(val, null, 2)
    }
  } else {
      if (modelParametersJson.value !== '{}') modelParametersJson.value = '{}'
  }
}, { immediate: true, deep: true })

const updateModelParametersJson = (val: string) => {
  modelParametersJson.value = val
  if (!val.trim()) {
    updateField('model_parameters', {})
    jsonError.value = ''
    return
  }
  try {
    const parsed = JSON.parse(val)
    updateField('model_parameters', parsed)
    jsonError.value = ''
  } catch (e) {
    jsonError.value = t('assistantForm.invalidJson')
  }
}

</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle>{{ t('assistantForm.modelConfig') }}</CardTitle>
    </CardHeader>
    <CardContent class="grid gap-6">
      
      <!-- System Prompt -->
      <div class="space-y-2">
        <Label for="system_prompt">
          {{ t('assistantForm.systemPrompt') }} <span class="text-destructive">*</span>
        </Label>
        <Textarea
          id="system_prompt"
          :model-value="modelValue.system_prompt"
          @update:model-value="updateField('system_prompt', $event as string)"
          :placeholder="t('assistantForm.systemPromptPlaceholder')"
          :rows="5"
          :class="{ 'border-destructive': errors.system_prompt }"
          :disabled="loading"
        />
        <div v-if="errors.system_prompt" class="text-sm text-destructive">
          {{ errors.system_prompt }}
        </div>
        <div class="text-sm text-muted-foreground">
          {{ t('assistantForm.systemPromptHelp') }}
        </div>
      </div>

      <!-- Model Selection -->
      <div class="space-y-2">
        <Label for="model_id">
          {{ t('assistantForm.model') }} <span class="text-destructive">*</span>
        </Label>
        <Select 
          :model-value="modelValue.model_id" 
          @update:model-value="updateField('model_id', $event as string)"
          :disabled="loading"
        >
          <SelectTrigger :class="{ 'border-destructive': errors.model_id }">
            <SelectValue :placeholder="t('assistantForm.modelPlaceholder')" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem
              v-for="model in modelOptions"
              :key="model.value"
              :value="String(model.value)"
            >
              {{ model.label }}
            </SelectItem>
          </SelectContent>
        </Select>
        <div v-if="errors.model_id" class="text-sm text-destructive">
          {{ errors.model_id }}
        </div>
        <div class="text-sm text-muted-foreground">
          {{ t('assistantForm.modelHelp') }}
        </div>
      </div>

      <!-- Parameters -->
      <div class="grid grid-cols-2 gap-4">
        <div class="space-y-2">
          <Label for="temperature">{{ t('assistantForm.temperature') }}</Label>
          <Input
            id="temperature"
            :model-value="modelValue.temperature"
            @update:model-value="(val) => updateField('temperature', Number(val))"
            type="number"
            placeholder="0.7"
            min="0"
            max="2"
            step="0.1"
            :disabled="loading"
          />
          <div class="text-sm text-muted-foreground">
            {{ t('assistantForm.temperatureHelp') }}
          </div>
        </div>
        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <Label for="max_history_messages">{{ t('assistantForm.maxHistory') }}</Label>
            <Switch
              :model-value="enableMaxHistory"
              @update:model-value="handleMaxHistoryToggle"
              :disabled="loading"
            />
          </div>
          <div v-if="enableMaxHistory" class="pt-2">
            <Input
              id="max_history_messages"
              :model-value="modelValue.max_history_messages ?? ''"
              @update:model-value="(val) => updateField('max_history_messages', (val === '' || val === null || val === undefined) ? null : Number(val))"
              type="number"
              placeholder="10"
              min="0"
              :disabled="loading"
            />
          </div>
          <div class="text-sm text-muted-foreground">
            {{ t('assistantForm.maxHistoryHelp') }}
          </div>
        </div>
      </div>

      <!-- Advanced Parameters (JSON) -->
      <div class="space-y-4 pt-4 border-t">
         <div class="flex items-center justify-between">
            <Label>{{ t('assistantForm.advancedParams') }}</Label>
            <Button variant="ghost" size="sm" @click="showAdvanced = !showAdvanced">
                {{ showAdvanced ? t('common.hide') : t('common.show') }}
            </Button>
         </div>
         
         <div v-if="showAdvanced" class="space-y-2">
            <Textarea
              :model-value="modelParametersJson"
              @update:model-value="updateModelParametersJson"
              :class="{ 'border-destructive': jsonError, 'font-mono text-xs': true }"
              placeholder="{ &quot;top_p&quot;: 0.9 }"
              rows="8"
            />
            <div v-if="jsonError" class="text-sm text-destructive">
                {{ jsonError }}
            </div>
             <div class="text-sm text-muted-foreground">
                {{ t('assistantForm.advancedParamsHelp') }}
            </div>
         </div>
      </div>
    </CardContent>
  </Card>
</template>
