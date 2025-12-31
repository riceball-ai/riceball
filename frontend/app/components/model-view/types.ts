import type { ColumnDef } from '@tanstack/vue-table'
import type { ModelViewApiEndpointOverrides } from '~/composables/useModelViewAPI'

// From DynamicForm.vue
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

// From DataTable.vue
export interface FilterConfig {
  type: 'text' | 'select' | 'daterange'
  label: string
  placeholder?: string
  options?: Array<{ label: string; value: string }>
}

export interface ActionConfig {
  key: string
  label: string
  icon?: any
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link'
}

export interface DetailField {
  name: string
  label: string
  type?: string
  render?: (value: any, record: Record<string, any>) => any
}

export type ModelViewApiEndpoints = ModelViewApiEndpointOverrides

export interface ModelViewConfig<T> {
  // Basic config
  title: string
  description?: string
  
  // API config
  apiEndpoint: string
  apiEndpoints?: ModelViewApiEndpoints
  
  // Table config
  columns: ColumnDef<T>[]
  selectable?: boolean
  
  // Form config
  formFields?: FormField[]
  formDescription?: string
  
  // Detail config
  detailFields?: DetailField[]
  
  // Feature switches
  canCreate?: boolean
  canEdit?: boolean
  canDelete?: boolean
  canView?: boolean
  canDuplicate?: boolean
  showFilters?: boolean
  showExport?: boolean
  showImport?: boolean
  
  // Filter config
  filters?: Record<string, FilterConfig>
  
  // Action config
  customActions?: ActionConfig[]
  
  // Other config
  emptyMessage?: string
  pageSize?: number
}
