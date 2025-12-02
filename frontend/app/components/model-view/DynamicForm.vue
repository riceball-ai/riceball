
<script setup lang="ts" generic="T extends Record<string, any>">
import { ref, computed, watch, onMounted } from 'vue'
import { Save, Loader2 } from 'lucide-vue-next'

const { t } = useI18n()

import { Button } from '~/components/ui/button'
import { Input } from '~/components/ui/input'
import { Label } from '~/components/ui/label'
import { Textarea } from '~/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '~/components/ui/select'
import { ImageUpload } from '~/components/ui/image-upload'
import { Switch } from '~/components/ui/switch'

export interface FieldOption {
  label: string
  value: string | number
}

export interface FormField {
  name: string
  label: string
  type: 'text' | 'email' | 'password' | 'number' | 'textarea' | 'select' | 'multiselect' | 'radio' | 'switch' | 'date' | 'datetime' | 'file' | 'image' | 'avatar' | 'json'
  required?: boolean
  disabled?: boolean
  placeholder?: string
  help?: string
  description?: string
  defaultValue?: any
  
  // Number field
  min?: number
  max?: number
  step?: number
  
  // Textarea field
  rows?: number
  
  // Select field
  options?: FieldOption[]
  
  // File field
  accept?: string
  multiple?: boolean
  
  // Validation rules
  validation?: {
    minLength?: number
    maxLength?: number
    pattern?: RegExp
    custom?: (value: any) => string | null
  }
}

interface Props {
  fields: FormField[]
  initialData?: Partial<T>
  loading?: boolean
  submitText?: string
  showCancel?: boolean
  cancelText?: string
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  submitText: '',
  showCancel: false,
  cancelText: ''
})

// Computed i18n defaults
const computedSubmitText = computed(() => props.submitText || t('components.dynamicForm.save'))
const computedCancelText = computed(() => props.cancelText || t('components.dynamicForm.cancel'))

const emit = defineEmits<{
  submit: [data: T]
  cancel: []
}>()

// State management
const formData = ref<Record<string, any>>({})
const errors = ref<Record<string, string>>({})
const touchedFields = ref<Set<string>>(new Set())
const isInitialized = ref(false)

// Initialize form data
const initializeForm = () => {
  const data: Record<string, any> = {}
  
  props.fields.forEach(field => {
    if (props.initialData && props.initialData[field.name] !== undefined) {
      let value = props.initialData[field.name]
      
      // Auto convert JSON object to string
      if (field.type === 'json' && typeof value === 'object' && value !== null) {
        value = JSON.stringify(value, null, 2) as any
      }
      
      data[field.name] = value
    } else if (field.defaultValue !== undefined) {
      let value = field.defaultValue
      
      // Auto convert default value JSON object to string
      if (field.type === 'json' && typeof value === 'object' && value !== null) {
        value = JSON.stringify(value, null, 2) as any
      }
      
      data[field.name] = value
    } else {
      // Set type default value
      switch (field.type) {
        case 'multiselect':
          data[field.name] = []
          break
        case 'switch':
          data[field.name] = false
          break
        case 'number':
          data[field.name] = field.min || 0
          break
        case 'json':
          data[field.name] = '{}'
          break
        default:
          data[field.name] = ''
      }
    }
  })
  
  formData.value = data
  isInitialized.value = true
}

// Validate form
const validateField = (field: FormField, value: any): string | null => {
  if (field.required) {
    if (field.type === 'multiselect') {
      if (!value || !Array.isArray(value) || value.length === 0) {
        return t('components.dynamicForm.validation.multiselectRequired', { label: field.label })
      }
    } else if (!value || value === '') {
      return t('components.dynamicForm.validation.required', { label: field.label })
    }
  }
  
  // Special validation for JSON field
  if (field.type === 'json' && value && value !== '') {
    if (!isValidJson(value)) {
      return t('components.dynamicForm.validation.invalidJson', { label: field.label })
    }
  }
  
  if (field.validation) {
    const { minLength, maxLength, pattern, custom } = field.validation
    
    if (minLength && value && value.length < minLength) {
      return t('components.dynamicForm.validation.minLength', { label: field.label, count: minLength })
    }
    
    if (maxLength && value && value.length > maxLength) {
      return t('components.dynamicForm.validation.maxLength', { label: field.label, count: maxLength })
    }
    
    if (pattern && value && !pattern.test(value)) {
      return t('components.dynamicForm.validation.invalidFormat', { label: field.label })
    }
    
    if (custom) {
      return custom(value)
    }
  }
  
  return null
}

const validateForm = (): boolean => {
  const newErrors: Record<string, string> = {}
  
  // Mark all fields as touched
  props.fields.forEach(field => {
    touchedFields.value.add(field.name)
    const error = validateField(field, formData.value[field.name])
    if (error) {
      newErrors[field.name] = error
    }
  })
  
  errors.value = newErrors
  return Object.keys(newErrors).length === 0
}

// Computed properties
const isValid = computed(() => {
  if (!isInitialized.value) return false
  
  // Validate all required fields
  for (const field of props.fields) {
    if (field.required) {
      const value = formData.value[field.name]
      
      if (field.type === 'multiselect') {
        if (!value || !Array.isArray(value) || value.length === 0) {
          return false
        }
      } else if (!value || value === '') {
        return false
      }
    }
  }
  
  // Check for any validation errors
  return Object.keys(errors.value).length === 0
})

// Methods
const handleSubmit = () => {
  if (validateForm() && isValid.value) {
    // Process submit data, convert JSON string back to object
    const submitData = { ...formData.value }
    
    props.fields.forEach(field => {
      if (field.type === 'json' && submitData[field.name] && typeof submitData[field.name] === 'string') {
        try {
          submitData[field.name] = JSON.parse(submitData[field.name])
        } catch {
          // If parse fails, keep original string value
        }
      }
    })
    
    emit('submit', submitData as T)
  }
}

const handleCancel = () => {
  emit('cancel')
}

const markFieldAsTouched = (fieldName: string) => {
  touchedFields.value.add(fieldName)
}

// Multiselect related methods
const isMultiSelectOptionSelected = (fieldName: string, value: any): boolean => {
  if (!formData.value[fieldName]) return false
  const currentValues = formData.value[fieldName] as any[]
  return currentValues.includes(value)
}

const toggleMultiSelectOption = (fieldName: string, value: any, checked: boolean) => {
  markFieldAsTouched(fieldName)
  
  if (!formData.value[fieldName]) {
    formData.value[fieldName] = []
  }
  
  const currentValues = [...(formData.value[fieldName] as any[])]
  
  if (checked) {
    if (!currentValues.includes(value)) {
      currentValues.push(value)
    }
  } else {
    const index = currentValues.indexOf(value)
    if (index > -1) {
      currentValues.splice(index, 1)
    }
  }
  
  formData.value[fieldName] = currentValues
}

// JSON related methods
const isValidJson = (jsonString: string): boolean => {
  if (!jsonString || jsonString.trim() === '') return true // Empty string is considered valid
  
  try {
    JSON.parse(jsonString)
    return true
  } catch {
    return false
  }
}

const formatJson = (fieldName: string) => {
  const value = formData.value[fieldName]
  if (!value) return
  
  try {
    const parsed = JSON.parse(value)
    formData.value[fieldName] = JSON.stringify(parsed, null, 2)
  } catch (error) {
    // If parse fails, do nothing
  }
}

const minifyJson = (fieldName: string) => {
  const value = formData.value[fieldName]
  if (!value) return
  
  try {
    const parsed = JSON.parse(value)
    formData.value[fieldName] = JSON.stringify(parsed)
  } catch (error) {
    // If parse fails, do nothing
  }
}

// Watchers
watch(() => props.initialData, () => {
  initializeForm()
}, { deep: true })

// Real-time validation on form data change
watch(() => formData.value, () => {
  if (isInitialized.value) {
    const newErrors: Record<string, string> = {}
    
    props.fields.forEach(field => {
      if (touchedFields.value.has(field.name) || field.required) {
        const error = validateField(field, formData.value[field.name])
        if (error) {
          newErrors[field.name] = error
        }
      }
    })
    
    errors.value = newErrors
  }
}, { deep: true, immediate: false })

// Lifecycle
onMounted(() => {
  initializeForm()
})
</script>

<template>
  <form @submit.prevent="handleSubmit" class="space-y-4">
    <div v-for="field in fields" :key="field.name" class="space-y-2">
      <Label :for="field.name" class="text-sm font-medium">
        {{ field.label }}
        <span v-if="field.required" class="text-destructive">*</span>
      </Label>

      <!-- Text input -->
      <Input
        v-if="field.type === 'text' || field.type === 'email' || field.type === 'password'"
        :id="field.name"
        v-model="formData[field.name]"
        :type="field.type"
        :placeholder="field.placeholder"
        :disabled="field.disabled || loading"
        :class="{ 'border-destructive': errors[field.name] }"
        @focus="markFieldAsTouched(field.name)"
        @blur="markFieldAsTouched(field.name)"
      />

      <!-- Number input -->
      <Input
        v-else-if="field.type === 'number'"
        :id="field.name"
        v-model.number="formData[field.name]"
        type="number"
        :placeholder="field.placeholder"
        :disabled="field.disabled || loading"
        :min="field.min"
        :max="field.max"
        :step="field.step"
        :class="{ 'border-destructive': errors[field.name] }"
        @focus="markFieldAsTouched(field.name)"
        @blur="markFieldAsTouched(field.name)"
      />

      <!-- Textarea -->
      <Textarea
        v-else-if="field.type === 'textarea'"
        :id="field.name"
        v-model="formData[field.name]"
        :placeholder="field.placeholder"
        :disabled="field.disabled || loading"
        :rows="field.rows || 3"
        :class="{ 'border-destructive': errors[field.name] }"
        @focus="markFieldAsTouched(field.name)"
        @blur="markFieldAsTouched(field.name)"
      />

      <!-- Select -->
      <Select
        v-else-if="field.type === 'select'"
        v-model="formData[field.name]"
        :disabled="field.disabled || loading"
        @update:model-value="() => markFieldAsTouched(field.name)"
      >
        <SelectTrigger :class="{ 'border-destructive': errors[field.name] }">
          <SelectValue :placeholder="field.placeholder" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem
            v-for="option in field.options"
            :key="option.value"
            :value="option.value.toString()"
          >
            {{ option.label }}
          </SelectItem>
        </SelectContent>
      </Select>

      <!-- Multiselect -->
      <div v-else-if="field.type === 'multiselect'" class="space-y-3">
        <div 
          :class="[
            'grid grid-cols-1 gap-2 p-2 border rounded-md',
            errors[field.name] ? 'border-destructive bg-destructive/5' : 'border-border'
          ]"
        >
          <div 
            v-for="option in field.options" 
            :key="option.value"
            class="flex items-center space-x-2"
          >
            <input
              type="checkbox"
              :id="`${field.name}-${option.value}`"
              :checked="isMultiSelectOptionSelected(field.name, option.value)"
              @change="(event: Event) => {
                const target = event.target as HTMLInputElement
                toggleMultiSelectOption(field.name, option.value, target.checked)
              }"
              :disabled="field.disabled || loading"
              class="h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded"
            />
            <Label 
              :for="`${field.name}-${option.value}`" 
              class="text-sm font-normal cursor-pointer flex-1"
            >
              {{ option.label }}
            </Label>
          </div>
        </div>
        <div v-if="formData[field.name] && formData[field.name].length > 0" class="text-xs text-muted-foreground">
          {{ t('components.dynamicForm.selected', { count: formData[field.name].length }) }}
        </div>
      </div>

      <!-- Switch -->
      <div v-else-if="field.type === 'switch'" class="flex items-center space-x-3">
        <Switch
          :id="field.name"
          v-model="formData[field.name]"
          :disabled="field.disabled || loading"
          @update:model-value="() => markFieldAsTouched(field.name)"
        />
        <Label :for="field.name" class="text-sm cursor-pointer">
          {{ field.description || field.label }}
        </Label>
      </div>

      <!-- Avatar upload -->
      <AvatarUpload
        v-else-if="field.type === 'avatar'"
        :id="field.name"
        v-model="formData[field.name]"
        :disabled="field.disabled || loading"
        :class="{ 'border-destructive': errors[field.name] }"
      />

      <!-- JSON editor -->
      <div v-else-if="field.type === 'json'" class="space-y-2">
        <Textarea
          :id="field.name"
          v-model="formData[field.name]"
          :placeholder="field.placeholder || t('components.dynamicForm.jsonPlaceholder')"
          :disabled="field.disabled || loading"
          :rows="field.rows || 6"
          :class="{ 'border-destructive': errors[field.name] }"
          class="font-mono text-sm"
          @focus="markFieldAsTouched(field.name)"
          @blur="markFieldAsTouched(field.name)"
        />
        <div class="flex items-center justify-between text-xs">
          <span class="text-muted-foreground">
            {{ t('components.dynamicForm.jsonHint') }}
          </span>
          <div class="flex items-center gap-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              @click="formatJson(field.name)"
              :disabled="field.disabled || loading"
              class="h-6 px-2 text-xs"
            >
              {{ t('components.dynamicForm.formatJson') }}
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              @click="minifyJson(field.name)"
              :disabled="field.disabled || loading"
              class="h-6 px-2 text-xs"
            >
              {{ t('components.dynamicForm.minifyJson') }}
            </Button>
          </div>
        </div>
      </div>

      <!-- Error message -->
      <div v-if="errors[field.name]" class="text-sm text-destructive">
        {{ errors[field.name] }}
      </div>

      <!-- Help text -->
      <div v-if="field.help" class="text-sm text-muted-foreground">
        {{ field.help }}
      </div>
    </div>

    <!-- Form action buttons -->
    <slot name="actions" :onSubmit="handleSubmit" :onCancel="handleCancel">
      <div class="flex justify-end gap-2 pt-4">
        <Button
          v-if="showCancel"
          type="button"
          variant="outline"
          @click="handleCancel"
          :disabled="loading"
        >
          {{ computedCancelText }}
        </Button>
        <Button
          type="submit"
          :disabled="loading || !isValid"
        >
          <Loader2 v-if="loading" class="h-4 w-4 mr-1 animate-spin" />
          <Save v-else class="h-4 w-4 mr-1" />
          {{ computedSubmitText }}
        </Button>
      </div>
    </slot>
  </form>
</template>