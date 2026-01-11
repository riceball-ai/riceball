<script setup lang="ts">
import { computed } from 'vue'
import { Card, CardContent, CardHeader, CardTitle } from '~/components/ui/card'
import { Label } from '~/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '~/components/ui/select'

const { t } = useI18n()

interface PublishData {
  is_public: boolean
  status: string
}

interface Props {
  modelValue: PublishData
  loading?: boolean
  isAdmin?: boolean
  errors?: Record<string, string>
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  isAdmin: false,
  errors: () => ({})
})

const emit = defineEmits<{
  'update:modelValue': [value: PublishData]
}>()

const updateField = <K extends keyof PublishData>(key: K, value: PublishData[K]) => {
  const newValue = { ...props.modelValue, [key]: value }
  emit('update:modelValue', newValue)
}
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle>{{ t('assistantForm.publishSettings') }}</CardTitle>
    </CardHeader>
    <CardContent class="grid gap-6">
      <!-- Is Public -->
      <div class="flex items-center space-x-2">
        <input
          id="is_public"
          type="checkbox"
          :checked="modelValue.is_public"
          @change="updateField('is_public', ($event.target as HTMLInputElement).checked)"
          :disabled="loading"
          class="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
        />
        <Label for="is_public" class="text-sm cursor-pointer">
          {{ t('assistantForm.isPublic') }}
        </Label>
      </div>

      <!-- Status -->
      <div class="space-y-2">
        <Label for="status">
          {{ t('assistantForm.status') }} <span class="text-destructive">*</span>
        </Label>
        <Select 
          :model-value="modelValue.status" 
          @update:model-value="updateField('status', $event as string)"
          :disabled="loading"
        >
          <SelectTrigger :class="{ 'border-destructive': errors.status }">
            <SelectValue :placeholder="t('assistantForm.statusPlaceholder')" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ACTIVE">{{ t('assistantForm.statusActive') }}</SelectItem>
            <SelectItem v-if="isAdmin" value="INACTIVE">{{ t('admin.pages.assistants.create.publishSettings.statuses.inactive') }}</SelectItem>
            <SelectItem value="DRAFT">{{ t('assistantForm.statusDraft') }}</SelectItem>
          </SelectContent>
        </Select>
        <div v-if="errors.status" class="text-sm text-destructive">
          {{ errors.status }}
        </div>
      </div>
    </CardContent>
  </Card>
</template>
