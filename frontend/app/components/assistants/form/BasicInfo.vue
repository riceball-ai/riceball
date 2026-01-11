<script setup lang="ts">
import { computed } from 'vue'
import { Card, CardContent, CardHeader, CardTitle } from '~/components/ui/card'
import { Input } from '~/components/ui/input'
import { Label } from '~/components/ui/label'
import { Textarea } from '~/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '~/components/ui/select'
import AvatarUpload from '~/components/AvatarUpload.vue'
import { ASSISTANT_CATEGORIES } from '~/constants/assistants'

const { t } = useI18n()

interface BasicInfoData {
  name: string
  avatar_file_path: string
  description: string
  category: string
  tags: string[]
}

interface Props {
  modelValue: BasicInfoData
  loading?: boolean
  enableCategories?: boolean
  errors?: Record<string, string>
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  enableCategories: false,
  errors: () => ({})
})

const emit = defineEmits<{
  'update:modelValue': [value: BasicInfoData]
}>()

const formData = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const updateField = <K extends keyof BasicInfoData>(key: K, value: BasicInfoData[K]) => {
  const newValue = { ...props.modelValue, [key]: value }
  emit('update:modelValue', newValue)
}

// Tag input handling
const tagsInput = computed({
  get: () => props.modelValue.tags?.join(', ') || '',
  set: (val: string) => {
    const tags = val.split(/[,，]/).map(t => t.trim()).filter(Boolean)
    updateField('tags', tags)
  }
})
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle>{{ t('assistantForm.basicInfo') }}</CardTitle>
    </CardHeader>
    <CardContent class="grid gap-6">
      <!-- Avatar -->
      <div class="space-y-2">
        <Label>{{ t('assistantForm.avatar') }}</Label>
        <AvatarUpload
          id="avatar"
          :model-value="formData.avatar_file_path"
          @update:model-value="updateField('avatar_file_path', $event)"
          :disabled="loading"
        />
        <div class="text-sm text-muted-foreground">
          {{ t('assistantForm.avatarHelp') }}
        </div>
      </div>

      <!-- Name -->
      <div class="space-y-2">
        <Label for="name">
          {{ t('assistantForm.name') }} <span class="text-destructive">*</span>
        </Label>
        <Input
          id="name"
          :model-value="formData.name"
          @update:model-value="updateField('name', $event as string)"
          :placeholder="t('assistantForm.namePlaceholder')"
          :class="{ 'border-destructive': errors.name }"
          :disabled="loading"
        />
        <div v-if="errors.name" class="text-sm text-destructive">
          {{ errors.name }}
        </div>
      </div>

      <!-- Description -->
      <div class="space-y-2">
        <Label for="description">{{ t('assistantForm.description') }}</Label>
        <Textarea
          id="description"
          :model-value="formData.description"
          @update:model-value="updateField('description', $event as string)"
          :placeholder="t('assistantForm.descriptionPlaceholder')"
          :rows="3"
          :disabled="loading"
        />
      </div>

      <!-- Category -->
      <div class="space-y-2" v-if="enableCategories">
        <Label for="category">{{ t('assistantForm.category') }}</Label>
        <Select 
          :model-value="formData.category"
          @update:model-value="updateField('category', $event as string)"
          :disabled="loading"
        >
          <SelectTrigger>
            <SelectValue :placeholder="t('assistantForm.categoryPlaceholder')" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem
              v-for="category in ASSISTANT_CATEGORIES"
              :key="category.value"
              :value="category.value"
            >
              {{ t(`assistants.categories.${category.value}`) }}
            </SelectItem>
          </SelectContent>
        </Select>
        <div class="text-sm text-muted-foreground">
          {{ t('assistantForm.categoryHelp') }}
        </div>
      </div>

      <!-- Tags -->
      <div class="space-y-2">
        <Label for="tags">{{ t('assistantForm.tags') }}</Label>
        <Input
          id="tags"
          v-model="tagsInput"
          :placeholder="t('assistantForm.tagsPlaceholder')"
          :disabled="loading"
        />
        <div class="text-sm text-muted-foreground">
          {{ t('assistantForm.tagsHelp') }}
        </div>
      </div>
    </CardContent>
  </Card>
</template>
