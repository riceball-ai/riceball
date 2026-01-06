<script setup lang="ts" generic="T extends Record<string, any>">
import { ref, computed, onMounted, watch, isVNode } from 'vue'
import type { ColumnDef, SortingState, PaginationState } from '@tanstack/vue-table'
import {
  Download,
  Upload,
  Trash2,
  Edit,
  Eye,
  Copy,
} from 'lucide-vue-next'
import { FetchError } from 'ofetch'
import { Button } from '~/components/ui/button'
import { Label } from '~/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '~/components/ui/dialog'
import { toast } from 'vue-sonner'

import DataTable from './DataTable.vue'
import DynamicForm from './DynamicForm.vue'
import { useModelViewAPI } from '~/composables/useModelViewAPI'
import type { ModelViewConfig, ActionConfig } from './types'

const { t } = useI18n()

interface Props {
  config: ModelViewConfig<T>
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'row-action': [action: ActionConfig, row: T]
  'bulk-action': [action: ActionConfig, rows: T[]]
}>()

// Initialize API
let api = useModelViewAPI<T>(props.config.apiEndpoint, props.config.apiEndpoints)

// State management
const data = ref<T[]>([])
const totalCount = ref(0)
const loading = ref(false)
const formLoading = ref(false)
const deleteLoading = ref(false)

// Dialog states
const showFormDialog = ref(false)
const showDeleteDialog = ref(false)
const showDetailDialog = ref(false)

const formMode = ref<'create' | 'edit'>('create')
const selectedItem = ref<T | null>(null)
const formRef = ref()

const itemsToDelete = ref<T[]>([])

const searchQuery = ref('')
const filters = ref<Record<string, any>>({})
const sorting = ref<SortingState>([])
const pagination = ref<PaginationState>({
  pageIndex: 0,
  pageSize: props.config.pageSize || 20,
})

const tableColumns = computed(() => props.config.columns)
const formFields = computed(() => props.config.formFields)
const detailFields = computed(() => props.config.detailFields || [])
const canCreate = computed(() => !!(props.config.formFields && props.config.canCreate !== false))
const canEdit = computed(() => props.config.canEdit !== false)
const canDelete = computed(() => props.config.canDelete !== false)
const canView = computed(() => props.config.canView !== false)
const canDuplicate = computed(() => props.config.canDuplicate !== false)
const selectable = computed(() => props.config.selectable !== false)
const showFilters = computed(() => props.config.showFilters !== false)
const showExport = computed(() => props.config.showExport !== false)
const showImport = computed(() => props.config.showImport !== false)
const emptyMessage = computed(() => props.config.emptyMessage || t('components.modelView.emptyMessage'))

const detailRenderValues = computed<Record<string, any>>(() => {
  if (!selectedItem.value) return {}
  const rendered: Record<string, any> = {}
  for (const field of detailFields.value) {
    if (typeof field.render === 'function') {
      try {
        rendered[field.name] = field.render(
          (selectedItem.value as any)[field.name],
          selectedItem.value
        )
      } catch (error) {
        console.error(`Detail field render error: ${field.name}`, error)
      }
    }
  }
  return rendered
})

const title = computed(() => props.config.title)
const description = computed(() => props.config.description)
const formDescription = computed(() => props.config.formDescription)

const deleteMessage = computed(() => {
  if (itemsToDelete.value.length === 1) {
    return t('components.modelView.deleteConfirmSingle', { title: title.value })
  }
  return t('components.modelView.deleteConfirmMultiple', { count: itemsToDelete.value.length, title: title.value })
})

const rowActions = computed((): ActionConfig[] => {
  const actions: ActionConfig[] = []
  
  if (canView.value) {
    actions.push({
      key: 'view',
      label: t('components.modelView.view'),
      icon: Eye,
    })
  }
  
  if (canEdit.value) {
    actions.push({
      key: 'edit',
      label: t('components.modelView.edit'),
      icon: Edit,
    })
  }
  
  if (canDuplicate.value) {
    actions.push({
      key: 'duplicate',
      label: t('components.modelView.duplicate'),
      icon: Copy,
    })
  }
  
  if (canDelete.value) {
    actions.push({
      key: 'delete',
      label: t('components.modelView.delete'),
      icon: Trash2,
      variant: 'destructive',
    })
  }
  
  if (props.config.customActions) {
    actions.push(...props.config.customActions)
  }
  
  return actions
})

const bulkActions = computed((): ActionConfig[] => {
  const actions: ActionConfig[] = []
  
  if (canDelete.value) {
    actions.push({
      key: 'bulkDelete',
      label: t('components.modelView.bulkDelete'),
      icon: Trash2,
      variant: 'destructive',
    })
  }
  
  return actions
})

const loadData = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.value.pageIndex + 1,
      size: pagination.value.pageSize,
      search: searchQuery.value || undefined,
      sort_by: sorting.value[0]?.id,
      sort_desc: sorting.value[0]?.desc,
      ...filters.value
    }
    
    const response = await api.getList(params)
    data.value = response.items
    totalCount.value = response.total
    
  } catch (error) {
    console.error('Load data failed:', error)
    toast.error(t('components.modelView.loadDataFailed'))
  } finally {
    loading.value = false
  }
}

const createItem = async (itemData: T) => {
  formLoading.value = true
  try {
    await api.create(itemData)
    toast.success(t('components.modelView.createSuccess', { title: title.value }))
    closeFormDialog()
    loadData()
    
  } catch (error) {
    console.error('Create failed:', error)
    toast.error(t('components.modelView.createFailed'))
  } finally {
    formLoading.value = false
  }
}

const updateItem = async (id: string | number, itemData: Partial<T>) => {
  formLoading.value = true
  try {
    await api.update(id, itemData)
    toast.success(t('components.modelView.updateSuccess', { title: title.value }))
    closeFormDialog()
    loadData()
    
  } catch (error) {
    if (!(error instanceof FetchError)) throw error;
    if (error.statusCode === 400 && error.data?.detail) {
      // Display detailed error message from backend
      toast.error(t('components.modelView.updateFailedDetail', { detail: error.data?.detail }))
      return
    }
    toast.error(t('components.modelView.updateFailed'))
  } finally {
    formLoading.value = false
  }
}

const deleteItems = async (items: T[]) => {
  deleteLoading.value = true
  try {
    for (const item of items) {
      await api.remove((item as any).id)
    }
    
    toast.success(t('components.modelView.deleteSuccess', { title: title.value }))
    closeDeleteDialog()
    loadData()
    
  } catch (error) {
    console.error('Delete failed:', error)
    toast.error(t('components.modelView.deleteFailed'))
  } finally {
    deleteLoading.value = false
  }
}

const handleSearch = (query: string) => {
  searchQuery.value = query
  pagination.value.pageIndex = 0
  loadData()
}

const handleFilter = (filterValues: Record<string, any>) => {
  filters.value = filterValues
  pagination.value.pageIndex = 0
  loadData()
}

const handleSort = (sortingState: SortingState) => {
  sorting.value = sortingState
  loadData()
}

const handlePaginate = (paginationState: PaginationState) => {
  pagination.value = paginationState
  loadData()
}

const handleRefresh = () => {
  loadData()
}

const handleBulkAction = (action: ActionConfig, rows: T[]) => {
  switch (action.key) {
    case 'bulkDelete':
      itemsToDelete.value = rows
      showDeleteDialog.value = true
      break
    default:
      emit('bulk-action', action, rows)
      console.log('Bulk action:', action.key, rows)
  }
}

const handleRowAction = (action: ActionConfig, row: T) => {
  switch (action.key) {
    case 'view':
      selectedItem.value = row
      showDetailDialog.value = true
      break
    case 'edit':
      openEditForm(row)
      break
    case 'duplicate':
      const duplicateData = { ...row }
      delete (duplicateData as any).id
      selectedItem.value = duplicateData as T
      formMode.value = 'create'
      showFormDialog.value = true
      break
    case 'delete':
      itemsToDelete.value = [row]
      showDeleteDialog.value = true
      break
    default:
      emit('row-action', action, row)
  }
}

const openCreateForm = () => {
  selectedItem.value = null
  formMode.value = 'create'
  showFormDialog.value = true
}

const openEditForm = (item: T) => {
  selectedItem.value = item
  formMode.value = 'edit'
  showFormDialog.value = true
}

const handleFormSubmit = (formData: T) => {
  if (formMode.value === 'create') {
    createItem(formData)
  } else if (selectedItem.value) {
    updateItem((selectedItem.value as any).id, formData)
  }
}

const closeFormDialog = () => {
  showFormDialog.value = false
  selectedItem.value = null
}

const confirmDelete = () => {
  deleteItems(itemsToDelete.value as T[])
}

const closeDeleteDialog = () => {
  showDeleteDialog.value = false
  itemsToDelete.value = []
}

const closeDetailDialog = () => {
  showDetailDialog.value = false
  selectedItem.value = null
}

const editFromDetail = () => {
  if (selectedItem.value) {
    closeDetailDialog()
    openEditForm(selectedItem.value)
  }
}

const handleExport = () => {
  console.log('Exporting data...')
  toast.info(t('components.modelView.exportInProgress'))
}

const handleImport = () => {
  console.log('Importing data...')
  toast.info(t('components.modelView.importInProgress'))
}

const formatValue = (value: any, type?: string): string => {
  if (value === null || value === undefined) return '-'
  
  switch (type) {
    case 'date':
      return new Date(value).toLocaleDateString()
    case 'datetime':
      return new Date(value).toLocaleString()
    case 'boolean':
      return value ? t('components.modelView.yes') : t('components.modelView.no')
    case 'json':
      return JSON.stringify(value, null, 2)
    default:
      return value.toString()
  }
}

onMounted(() => {
  // loadData()
})

watch(() => [props.config.apiEndpoint, props.config.apiEndpoints], (newVal, oldVal) => {
  if (oldVal && (newVal[0] !== oldVal[0] || JSON.stringify(newVal[1]) !== JSON.stringify(oldVal[1]))) {
    api = useModelViewAPI<T>(props.config.apiEndpoint, props.config.apiEndpoints)
    loadData()
  }
}, { deep: true })

defineExpose({
  loadData,
  openCreateForm
})
</script>

<template>
  <div class="model-view space-y-6">
    <!-- Title bar -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold">{{ title }}</h1>
        <p v-if="description" class="text-muted-foreground">{{ description }}</p>
      </div>
      
      <div class="flex items-center gap-2">
        <slot name="actions"></slot>
        <Button
          v-if="showExport"
          variant="outline"
          @click="handleExport"
          :disabled="loading"
        >
          <Download class="h-4 w-4 mr-2" />
          {{ t('components.modelView.export') }}
        </Button>
        
        <Button
          v-if="showImport"
          variant="outline"
          @click="handleImport"
          :disabled="loading"
        >
          <Upload class="h-4 w-4 mr-2" />
          {{ t('components.modelView.import') }}
        </Button>
      </div>
    </div>

    <!-- Data table -->
    <DataTable
      :data="data as any[]"
      :columns="tableColumns as any[]"
      :total-count="totalCount"
      :loading="loading"
      :selectable="selectable"
      :can-create="canCreate"
      :show-filters="showFilters"
      :filters="config.filters || {}"
      :row-actions="rowActions"
      :bulk-actions="bulkActions"
      :empty-message="emptyMessage"
      @create="openCreateForm"
      @refresh="handleRefresh"
      @search="handleSearch"
      @filter="handleFilter"
      @sort="handleSort"
      @paginate="handlePaginate"
      @bulk-action="(action: any, rows: any) => handleBulkAction(action, rows)"
      @row-action="(action: any, row: any) => handleRowAction(action, row)"
    />

    <!-- Create/Edit form dialog -->
    <Dialog v-model:open="showFormDialog">
      <DialogContent class="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {{ formMode === 'create' ? t('components.modelView.createTitle', { title }) : t('components.modelView.editTitle', { title }) }}
          </DialogTitle>
          <DialogDescription>
            {{ formDescription || (formMode === 'create' ? t('components.modelView.createDescription', { title }) : t('components.modelView.editDescription', { title })) }}
          </DialogDescription>
        </DialogHeader>

        <DynamicForm
          ref="formRef"
          v-if="formFields && formFields.length"
          :fields="formFields"
          :initial-data="(selectedItem as any) || undefined"
          :loading="formLoading"
          :submit-text="formMode === 'create' ? t('components.modelView.create') : t('components.modelView.save')"
          @submit="(data: any) => handleFormSubmit(data)"
          @cancel="closeFormDialog"
        />
      </DialogContent>
    </Dialog>

    <!-- Confirm delete dialog -->
    <Dialog v-model:open="showDeleteDialog">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{{ t('components.modelView.confirmDelete') }}</DialogTitle>
          <DialogDescription>
            {{ deleteMessage }}
          </DialogDescription>
        </DialogHeader>

        <div class="flex justify-end gap-2">
          <Button variant="outline" @click="closeDeleteDialog">
            {{ t('components.modelView.cancel') }}
          </Button>
          <Button variant="destructive" @click="confirmDelete" :disabled="deleteLoading">
            <Trash2 class="h-4 w-4 mr-2" />
            {{ t('components.modelView.delete') }}
          </Button>
        </div>
      </DialogContent>
    </Dialog>

    <!-- Detail view dialog -->
    <Dialog v-model:open="showDetailDialog">
      <DialogContent class="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{{ t('components.modelView.detailTitle', { title }) }}</DialogTitle>
          <DialogDescription>
            {{ t('components.modelView.viewDescription', { title }) }}
          </DialogDescription>
        </DialogHeader>

        <div v-if="selectedItem" class="space-y-4">
          <div
            v-for="field in detailFields"
            :key="field.name"
            class="grid grid-cols-3 gap-4"
          >
            <Label class="font-medium">{{ field.label }}:</Label>
            <div class="col-span-2">
              <template v-if="field.render">
                <component
                  v-if="isVNode(detailRenderValues[field.name])"
                  :is="detailRenderValues[field.name]"
                />
                <span v-else class="block">
                  {{ detailRenderValues[field.name] ?? '-' }}
                </span>
              </template>
              <template v-else-if="field.type === 'json'">
                <pre class="whitespace-pre-wrap rounded bg-muted/40 p-3 font-mono text-xs">{{ formatValue(selectedItem[field.name], field.type) }}</pre>
              </template>
              <span v-else class="block">
                {{ formatValue(selectedItem[field.name], field.type) }}
              </span>
            </div>
          </div>
        </div>

        <div class="flex justify-end gap-2 mt-6">
          <Button variant="outline" @click="closeDetailDialog">
            {{ t('common.cancel') }}
          </Button>
          <Button v-if="canEdit" @click="editFromDetail">
            <Edit class="h-4 w-4 mr-2" />
            {{ t('components.modelView.edit') }}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  </div>
</template>