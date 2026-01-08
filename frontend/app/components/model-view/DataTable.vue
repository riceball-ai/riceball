<script setup lang="ts" generic="T extends Record<string, any>">
import { ref, computed, watch, onMounted } from 'vue'
import { useDebounceFn } from '@vueuse/core'

import {
  useVueTable,
  getCoreRowModel,
  getSortedRowModel,
  getPaginationRowModel,
  FlexRender,
  type ColumnDef,
  type SortingState,
  type PaginationState,
  type RowSelectionState,
} from '@tanstack/vue-table'
import {
  Plus,
  Filter,
  RotateCcw,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  MoreVertical,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Database as DatabaseIcon,
  X,
} from 'lucide-vue-next'

import { Button } from '~/components/ui/button'
import { Input } from '~/components/ui/input'
import { Label } from '~/components/ui/label'
import { Card, CardContent } from '~/components/ui/card'
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '~/components/ui/table'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '~/components/ui/dropdown-menu'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '~/components/ui/select'
import {
  Collapsible,
  CollapsibleContent,
} from '~/components/ui/collapsible'
import type { FilterConfig, ActionConfig } from './types'

interface Props {
  data: T[]
  columns: ColumnDef<T>[]
  totalCount: number
  loading?: boolean
  selectable?: boolean
  canCreate?: boolean
  showFilters?: boolean
  filters?: Record<string, FilterConfig>
  rowActions?: ActionConfig[]
  bulkActions?: ActionConfig[]
  emptyMessage?: string
  initialPageSize?: number
  initialSorting?: SortingState
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  selectable: false,
  canCreate: true,
  showFilters: false,
  filters: () => ({}),
  rowActions: () => [],
  bulkActions: () => [],
  emptyMessage: '',
  initialPageSize: 20,
  initialSorting: () => [],
})

const emit = defineEmits<{
  create: []
  refresh: []
  search: [query: string]
  filter: [filters: Record<string, any>]
  sort: [sorting: SortingState]
  paginate: [pagination: PaginationState]
  bulkAction: [action: ActionConfig, rows: T[]]
  rowAction: [action: ActionConfig, row: T]
}>()

const { t } = useI18n()

const searchQuery = ref('')
const filterValues = ref<Record<string, any>>({})
const showFilterPanel = ref(false)
const sorting = ref<SortingState>([...props.initialSorting])
const pagination = ref<PaginationState>({
  pageIndex: 0,
  pageSize: props.initialPageSize,
})
const rowSelection = ref<RowSelectionState>({})

// Internal flag: track whether initialized to avoid duplicate paginate events on init
const isInitialized = ref(false)

// Table configuration
const table = useVueTable({
  get data() { return props.data },
  get columns() { return props.columns },
  getCoreRowModel: getCoreRowModel(),
  getSortedRowModel: getSortedRowModel(),
  getPaginationRowModel: getPaginationRowModel(),
  onSortingChange: (updater) => {
    sorting.value = typeof updater === 'function' ? updater(sorting.value) : updater
    emit('sort', sorting.value)
  },
  onPaginationChange: (updater) => {
    const oldPagination = { ...pagination.value }
    pagination.value = typeof updater === 'function' ? updater(pagination.value) : updater
    
    // Only trigger event when actually changed and after initialization
    const hasChanged = 
      oldPagination.pageIndex !== pagination.value.pageIndex ||
      oldPagination.pageSize !== pagination.value.pageSize
    
    if (isInitialized.value && hasChanged) {
      emit('paginate', pagination.value)
    }
  },
  onRowSelectionChange: (updater) => {
    rowSelection.value = typeof updater === 'function' ? updater(rowSelection.value) : updater
  },
  state: {
    get sorting() { return sorting.value },
    get pagination() { return pagination.value },
    get rowSelection() { return rowSelection.value },
  },
  manualSorting: true,
  manualPagination: true,
  get pageCount() { return Math.ceil(props.totalCount / pagination.value.pageSize) },
})

// Computed properties
const selectedRows = computed(() => {
  return Object.keys(rowSelection.value)
    .filter(key => rowSelection.value[key])
    .map(key => props.data[parseInt(key)])
    .filter((item): item is T => item !== undefined)
})

const isAllSelected = computed(() => {
  return props.data.length > 0 && selectedRows.value.length === props.data.length
})

const isIndeterminate = computed(() => {
  return selectedRows.value.length > 0 && selectedRows.value.length < props.data.length
})

const activeFiltersCount = computed(() => {
  return Object.values(filterValues.value).filter(value => 
    value !== '' && value !== null && value !== undefined
  ).length
})

const totalColumns = computed(() => {
  let count = props.columns.length
  if (props.selectable) count++
  if (props.rowActions.length > 0) count++
  return count
})

const visiblePages = computed(() => {
  const total = Math.ceil(props.totalCount / pagination.value.pageSize)
  const current = pagination.value.pageIndex + 1
  const range = 2
  
  let start = Math.max(1, current - range)
  let end = Math.min(total, current + range)
  
  if (end - start < 4) {
    if (start === 1) {
      end = Math.min(total, start + 4)
    } else {
      start = Math.max(1, end - 4)
    }
  }
  
  return Array.from({ length: end - start + 1 }, (_, i) => start + i)
})

// Methods
const refresh = () => {
  emit('refresh')
}

const onSearch = useDebounceFn(() => {
  emit('search', searchQuery.value)
}, 300)

const toggleFilters = () => {
  showFilterPanel.value = !showFilterPanel.value
}

const applyFilters = useDebounceFn(() => {
  emit('filter', filterValues.value)
}, 300)

const clearFilters = () => {
  filterValues.value = {}
  emit('filter', {})
}

const onPageSizeChange = (size: any) => {
  if (size) {
    pagination.value.pageSize = parseInt(size.toString())
    pagination.value.pageIndex = 0
    emit('paginate', pagination.value)
  }
}

const toggleSelectAll = () => {
  if (isAllSelected.value) {
    rowSelection.value = {}
  } else {
    const newSelection: RowSelectionState = {}
    props.data.forEach((_, index) => {
      newSelection[index] = true
    })
    rowSelection.value = newSelection
  }
}

const handleBulkAction = (action: ActionConfig) => {
  emit('bulkAction', action, selectedRows.value)
}

const handleRowAction = (action: ActionConfig, row: T) => {
  emit('rowAction', action, row)
}

const getSortIcon = (sortDirection: false | 'asc' | 'desc') => {
  if (sortDirection === 'asc') return ArrowUp
  if (sortDirection === 'desc') return ArrowDown
  return ArrowUpDown
}

const getColumnClass = (columnDef: any) => {
  const classes = [columnDef.meta?.className]
  // Automatically apply truncate if width is specified, or if explicitly requested
  if (columnDef.meta?.width || columnDef.meta?.truncate) {
    classes.push('truncate')
  }
  return classes.filter(Boolean).join(' ')
}

const getColumnStyle = (columnDef: any) => {
  const style: Record<string, any> = { ...columnDef.meta?.style }
  if (columnDef.meta?.width) {
    const width = typeof columnDef.meta.width === 'number' 
      ? `${columnDef.meta.width}px` 
      : columnDef.meta.width
    style.width = width
    // Automatically apply max-width to ensure ellipsis works
    style.maxWidth = width
  }
  return style
}

// Watchers
watch(() => props.totalCount, () => {
  table.setPageCount(Math.ceil(props.totalCount / pagination.value.pageSize))
})

// Lifecycle
onMounted(() => {
  // Mark as initialized, subsequent pagination changes will trigger paginate events
  isInitialized.value = true
  emit('refresh')
})
</script>

<template>
  <div class="space-y-4">
    <!-- Search and filter bar -->
    <div class="flex items-center justify-between gap-4">
      <div class="flex items-center gap-2 flex-1">
        <div class="relative w-full max-w-sm">
          <Input
            v-model="searchQuery"
            :placeholder="t('components.dataTable.search')"
            class="pr-8"
            @input="onSearch"
          />
          <Button
            v-if="searchQuery"
            variant="ghost"
            size="sm"
            class="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
            @click="searchQuery = ''; onSearch()"
          >
            <X class="h-4 w-4 text-muted-foreground" />
          </Button>
        </div>
        <Button
          v-if="showFilters && Object.keys(filters).length > 0"
          variant="outline"
          @click="toggleFilters"
        >
          <Filter class="h-4 w-4 mr-2" />
          {{ t('components.dataTable.filter') }} {{ activeFiltersCount > 0 ? `(${activeFiltersCount})` : '' }}
        </Button>
      </div>
      
      <div class="flex items-center gap-2">
        <!-- Bulk actions -->
        <DropdownMenu v-if="bulkActions.length > 0 && selectedRows.length > 0">
          <DropdownMenuTrigger as-child>
            <Button variant="outline" size="sm">
              {{ t('components.dataTable.bulkActions') }} ({{ selectedRows.length }})
              <ChevronDown class="h-4 w-4 ml-2" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem
              v-for="action in bulkActions"
              :key="action.key"
              @click="handleBulkAction(action)"
            >
              <component :is="action.icon" v-if="action.icon" class="h-4 w-4 mr-2" />
              {{ action.label }}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <!-- Create button -->
        <Button v-if="canCreate" @click="$emit('create')">
          <Plus class="h-4 w-4 mr-2" />
          {{ t('components.dataTable.create') }}
        </Button>

        <!-- Refresh button -->
        <Button variant="outline" size="sm" @click="refresh" :disabled="loading">
          <RotateCcw class="h-4 w-4" :class="{ 'animate-spin': loading }" />
        </Button>
      </div>
    </div>

    <!-- Filter panel -->
    <Collapsible v-model:open="showFilterPanel">
      <CollapsibleContent class="space-y-2">
        <Card v-if="showFilters && Object.keys(filters).length > 0">
          <CardContent class="pt-6">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div v-for="(filter, key) in filters" :key="key" class="space-y-2">
                <Label :for="`filter-${key}`">{{ filter.label }}</Label>
                
                <div v-if="filter.type === 'text'" class="relative">
                  <Input
                    :id="`filter-${key}`"
                    v-model="filterValues[key]"
                    :placeholder="filter.placeholder"
                    class="pr-8"
                    @input="applyFilters"
                  />
                  <Button
                    v-if="filterValues[key]"
                    variant="ghost"
                    size="sm"
                    class="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                    @click="filterValues[key] = ''; applyFilters()"
                  >
                    <X class="h-4 w-4 text-muted-foreground" />
                  </Button>
                </div>
                
                <div v-else-if="filter.type === 'select'" class="relative">
                  <Select
                    v-model="filterValues[key]"
                    @update:model-value="applyFilters"
                  >
                    <SelectTrigger class="pr-8">
                      <SelectValue :placeholder="filter.placeholder" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem
                        v-for="option in filter.options"
                        :key="option.value"
                        :value="option.value"
                      >
                        {{ option.label }}
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  <Button
                    v-if="filterValues[key]"
                    variant="ghost"
                    size="sm"
                    class="absolute right-6 top-0 h-full px-2 hover:bg-transparent z-10"
                    @click.stop="filterValues[key] = undefined; applyFilters()"
                  >
                    <X class="h-4 w-4 text-muted-foreground" />
                  </Button>
                </div>

                <div v-else-if="filter.type === 'daterange'" class="flex gap-2">
                  <div class="relative flex-1">
                    <Input
                      type="date"
                      v-model="filterValues[`${key}_start`]"
                      class="pr-8"
                      @change="applyFilters"
                    />
                    <Button
                      v-if="filterValues[`${key}_start`]"
                      variant="ghost"
                      size="sm"
                      class="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                      onclick="event.stopPropagation()"
                      @click="filterValues[`${key}_start`] = ''; applyFilters()"
                    >
                      <X class="h-4 w-4 text-muted-foreground" />
                    </Button>
                  </div>
                  <div class="relative flex-1">
                    <Input
                      type="date"
                      v-model="filterValues[`${key}_end`]"
                      class="pr-8"
                      @change="applyFilters"
                    />
                    <Button
                      v-if="filterValues[`${key}_end`]"
                      variant="ghost"
                      size="sm"
                      class="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                      onclick="event.stopPropagation()"
                      @click="filterValues[`${key}_end`] = ''; applyFilters()"
                    >
                      <X class="h-4 w-4 text-muted-foreground" />
                    </Button>
                  </div>
                </div>
              </div>
            </div>
            
            <div class="flex justify-end gap-2 mt-4">
              <Button variant="outline" size="sm" @click="clearFilters">
                {{ t('components.dataTable.clearFilters') }}
              </Button>
            </div>
          </CardContent>
        </Card>
      </CollapsibleContent>
    </Collapsible>

    <!-- Data table -->
    <div class="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <!-- Checkbox column -->
            <TableHead v-if="selectable" class="w-12">
              <input
                type="checkbox"
                :checked="isAllSelected"
                :indeterminate="isIndeterminate"
                @change="toggleSelectAll"
                class="rounded border-gray-300"
              />
            </TableHead>
            
            <!-- Data columns -->
            <TableHead
              v-for="column in table.getHeaderGroups()[0]?.headers || []"
              :key="column.id"
              :class="getColumnClass(column.column.columnDef)"
              :style="getColumnStyle(column.column.columnDef)"
            >
              <div
                v-if="column.column.getCanSort()"
                class="flex items-center gap-2 cursor-pointer select-none"
                @click="column.column.toggleSorting()"
              >
                <span>{{ column.column.columnDef.header }}</span>
                <component
                  :is="getSortIcon(column.column.getIsSorted())"
                  class="h-4 w-4"
                />
              </div>
              <span v-else>{{ column.column.columnDef.header }}</span>
            </TableHead>

            <!-- Actions column -->
            <TableHead v-if="rowActions.length > 0" class="w-20 sticky right-0 z-20 bg-background border-l text-center">{{ t('components.dataTable.actions') }}</TableHead>
          </TableRow>
        </TableHeader>

        <TableBody>
          <TableRow
            v-for="row in table.getRowModel().rows"
            :key="row.id"
            class="group"
            :class="{ 'bg-muted/50': row.getIsSelected() }"
          >
            <!-- Checkbox column -->
            <TableCell v-if="selectable">
              <input
                type="checkbox"
                :checked="row.getIsSelected()"
                @change="row.toggleSelected()"
                class="rounded border-gray-300"
              />
            </TableCell>

            <!-- Data columns -->
            <TableCell
              v-for="cell in row.getVisibleCells()"
              :key="cell.id"
              :class="getColumnClass(cell.column.columnDef)"
              :style="getColumnStyle(cell.column.columnDef)"
            >
              <FlexRender 
                :render="cell.column.columnDef.cell" 
                :props="cell.getContext()" 
              />
            </TableCell>

            <!-- Actions column -->
            <TableCell
              v-if="rowActions.length > 0"
              class="sticky right-0 z-20 border-l text-center"
              :class="row.getIsSelected() ? 'bg-muted' : 'bg-background group-hover:bg-muted'"
            >
              <DropdownMenu>
                <DropdownMenuTrigger as-child>
                  <Button variant="ghost" size="sm" class="h-8 w-8 p-0">
                    <MoreVertical class="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem
                    v-for="action in rowActions"
                    :key="action.key"
                    @click="handleRowAction(action, row.original)"
                    :class="{
                      'text-destructive': action.variant === 'destructive'
                    }"
                  >
                    <component :is="action.icon" v-if="action.icon" class="h-4 w-4 mr-2" />
                    {{ action.label }}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </TableCell>
          </TableRow>

          <!-- Empty state -->
          <TableRow v-if="table.getRowModel().rows.length === 0">
            <TableCell :colspan="totalColumns" class="h-24 text-center">
              <div class="flex flex-col items-center gap-2">
                <DatabaseIcon class="h-8 w-8 text-muted-foreground" />
                <span class="text-muted-foreground">{{ emptyMessage || t('components.dataTable.noData') }}</span>
              </div>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>

    <!-- Pagination -->
    <div class="flex items-center justify-between">
      <div class="text-sm text-muted-foreground">
        {{ t('components.dataTable.showing') }} {{ ((pagination.pageIndex) * pagination.pageSize) + 1 }} {{ t('components.dataTable.to') }}
        {{ Math.min((pagination.pageIndex + 1) * pagination.pageSize, totalCount) }} {{ t('components.dataTable.of') }}
        {{ totalCount }} {{ t('components.dataTable.items') }}
      </div>

      <div class="flex items-center gap-2">
        <Select
          :model-value="pagination.pageSize.toString()"
          @update:model-value="onPageSizeChange"
        >
          <SelectTrigger class="w-20">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem
              v-for="size in [10, 20, 50, 100]"
              :key="size"
              :value="size.toString()"
            >
              {{ size }}
            </SelectItem>
          </SelectContent>
        </Select>

        <div class="flex items-center gap-1">
          <Button
            variant="outline"
            size="sm"
            :disabled="!table.getCanPreviousPage()"
            @click="table.previousPage()"
          >
            <ChevronLeft class="h-4 w-4" />
          </Button>

          <div class="flex items-center gap-1">
            <Button
              v-for="page in visiblePages"
              :key="page"
              :variant="page === pagination.pageIndex + 1 ? 'default' : 'outline'"
              size="sm"
              class="w-8 h-8 p-0"
              @click="table.setPageIndex(page - 1)"
            >
              {{ page }}
            </Button>
          </div>

          <Button
            variant="outline"
            size="sm"
            :disabled="!table.getCanNextPage()"
            @click="table.nextPage()"
          >
            <ChevronRight class="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>