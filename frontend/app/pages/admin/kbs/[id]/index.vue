<script setup lang="ts">
import { ref, h, onMounted, computed } from 'vue'
import { Badge } from '~/components/ui/badge'
import { Button } from '~/components/ui/button'
import { FileText, Upload, Trash2, Eye, Split, ChevronLeft, ChevronRight } from 'lucide-vue-next'
import type { ColumnDef, SortingState, PaginationState } from '@tanstack/vue-table'
import type { ActionConfig } from '~/components/model-view/DataTable.vue'
import DocIcon from '~/components/file-type-icon/Doc.vue'
import PdfIcon from '~/components/file-type-icon/Pdf.vue'
import MdIcon from '~/components/file-type-icon/Md.vue'
import TxtIcon from '~/components/file-type-icon/Txt.vue'
import XlsIcon from '~/components/file-type-icon/Xls.vue'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '~/components/ui/dialog'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '~/components/ui/card'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '~/components/ui/alert-dialog'
import FileUploadToKB from '~/components/admin/FileUploadToKB.vue'
import { toast } from 'vue-sonner'
import type { KnowledgeBase, Document } from '~/types/api'
const { $api } = useNuxtApp()
const { t } = useI18n()

// Get route parameters
const route = useRoute()
const router = useRouter()
const kbId = route.params.id as string

// Page metadata
definePageMeta({
  breadcrumb: 'admin.pages.kbs.detail.breadcrumb',
  layout: 'admin'
})

// State
const showUploadDialog = ref(false)
const knowledgeBase = ref<KnowledgeBase | null>(null)
const documentsKey = ref(0) // Force refresh document list
const loading = ref(false)
const deleteLoading = ref(false)
const showDeleteDialog = ref(false)
const documentToDelete = ref<Document | null>(null)

// Chunk-related state
const showChunksDialog = ref(false)
const chunksLoading = ref(false)
const currentDocument = ref<Document | null>(null)
const chunks = ref<any[]>([])
const chunksTotal = ref(0)
const chunksPage = ref(1)
const chunksPageSize = ref(50)

// Load knowledge base info
const loadKnowledgeBase = async () => {
  loading.value = true
  try {
    const response: any = await $api(`/v1/admin/rag/knowledge-bases/${kbId}`)
    knowledgeBase.value = response as KnowledgeBase
  } catch (error) {
    console.error('Failed to load knowledge base info:', error)
    toast.error(t('admin.pages.kbs.detail.loadFailed'))
    // Return to previous page if load failed
    router.push('/admin/kbs')
  } finally {
    loading.value = false
  }
}

// Initialize API
const api = useModelViewAPI<Document>(
  `/v1/admin/rag/knowledge-bases/${kbId}/documents`,
  {
    update: "/v1/admin/rag/documents",
    delete: "/v1/admin/rag/documents"
  }
)

// State management
const data = ref<Document[]>([])
const totalCount = ref(0)

// Query parameters
const searchQuery = ref('')
const filters = ref<Record<string, any>>({})
const sorting = ref<SortingState>([])
const pagination = ref<PaginationState>({
  pageIndex: 0,
  pageSize: 20,
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
    console.error('Failed to load data:', error)
    toast.error(t('admin.pages.kbs.detail.loadDataFailed'))
  } finally {
    loading.value = false
  }
}

const tableColumns: ColumnDef<Document>[] = [
    {
      accessorKey: 'title',
      header: () => t('admin.pages.kbs.detail.columns.title'),
      cell: (context) => {
        const row = context.row.original
        
        // Select icon based on file type
        const getFileIcon = (fileType: string) => {
          const type = fileType?.toLowerCase()
          switch (type) {
            case 'pdf':
              return PdfIcon
            case 'doc':
            case 'docx':
              return DocIcon
            case 'md':
            case 'markdown':
              return MdIcon
            case 'txt':
              return TxtIcon
            case 'xls':
            case 'xlsx':
              return XlsIcon
            default:
              return FileText
          }
        }
        
        const IconComponent = getFileIcon(row.file_type)
        
        return h('div', { class: 'flex items-center' }, [
          h(IconComponent, { class: 'size-8 mr-1' }),
          row.title
        ])
      }
    },
    {
      accessorKey: 'file_size',
      header: () => t('admin.pages.kbs.detail.columns.size'),
      cell: (context) => {
        const size = context.getValue() as number
        if (!size) return '-'
        
        if (size < 1024) return `${size} B`
        if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
        return `${(size / (1024 * 1024)).toFixed(1)} MB`
      }
    },
    {
      accessorKey: 'file_type',
      header: () => t('admin.pages.kbs.detail.columns.type')
    },
    {
      accessorKey: 'status',
      header: () => t('admin.pages.kbs.detail.columns.status'),
      cell: (context) => {
        const status = context.getValue() as string
        const variants = {
          'PROCESSING': 'secondary',
          'COMPLETED': 'default',
          'FAILED': 'destructive'
        } as const
        
        const labels = {
          'PROCESSING': t('admin.pages.kbs.detail.status.processing'),
          'COMPLETED': t('admin.pages.kbs.detail.status.completed'),
          'FAILED': t('admin.pages.kbs.detail.status.failed')
        } as const
        
        return h(Badge, {
          variant: variants[status as keyof typeof variants] || 'secondary'
        }, () => labels[status as keyof typeof labels] || status)
      }
    },
    {
      accessorKey: 'created_at',
      header: () => t('admin.pages.kbs.detail.columns.createdAt'),
      cell: (context) => {
        const date = new Date(context.getValue() as string)
        return date.toLocaleString()
      }
    }
]

const rowActions: ActionConfig[] = [
  // {
  //   key: 'view',
  //   label: 'View',
  //   icon: Eye,
  // },
  {
    key: 'view-chunks',
    label: () => t('admin.pages.kbs.detail.viewChunks'),
    icon: Split,
  },
  {
    key: 'delete',
    label: () => t('admin.pages.kbs.detail.delete'),
    icon: Trash2,
    variant: 'destructive',
  }
]

// Handle file upload complete
const handleUploadComplete = () => {
  showUploadDialog.value = false
  documentsKey.value++ // Refresh document list
  loadData()
  toast.success(t('admin.pages.kbs.detail.uploadSuccess'))
}

// Handle document actions
const resetDeleteDialog = () => {
  showDeleteDialog.value = false
  documentToDelete.value = null
}

const handleDocumentAction = (action: ActionConfig, row: Document) => {  
  switch (action.key) {
    case 'view':
      downloadDocument(row)
      break
    case 'view-chunks':
      openChunksDialog(row)
      break
    case 'delete':
      documentToDelete.value = row
      showDeleteDialog.value = true
      break
    case 'download':
      downloadDocument(row)
      break
    default:
      console.log('Unhandled document action:', action.key)
  }
}

const confirmDeleteDocument = async () => {
  if (!documentToDelete.value) return

  deleteLoading.value = true
  try {
    await api.remove(documentToDelete.value.id)
    toast.success(t('admin.pages.kbs.detail.deleteConfirm.success'))
    resetDeleteDialog()
    loadData()
  } catch (error) {
    console.error('Failed to delete document:', error)
    toast.error(t('admin.pages.kbs.detail.deleteConfirm.failed'))
  } finally {
    deleteLoading.value = false
  }
}


// Event handler methods
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

const handleDeleteDialogOpenChange = (open: boolean) => {
  showDeleteDialog.value = open
}

// Get document chunks
const loadDocumentChunks = async (documentId: string, page: number = 1) => {
  chunksLoading.value = true
  try {
    const response: any = await $api(`/v1/admin/rag/documents/${documentId}/chunks?page=${page}&size=${chunksPageSize.value}`)
    chunks.value = response.items || []
    chunksTotal.value = response.total || 0
    chunksPage.value = page
  } catch (error) {
    console.error('Failed to load document chunks:', error)
    toast.error(t('admin.pages.kbs.detail.chunks.loadFailed'))
  } finally {
    chunksLoading.value = false
  }
}

// Open chunk dialog
const openChunksDialog = (document: Document) => {
  currentDocument.value = document
  showChunksDialog.value = true
  chunksPage.value = 1
  loadDocumentChunks(document.id, 1)
}

// Close chunk dialog
const closeChunksDialog = () => {
  showChunksDialog.value = false
  currentDocument.value = null
  chunks.value = []
  chunksTotal.value = 0
  chunksPage.value = 1
}

// Pagination handling
const totalPages = computed(() => Math.ceil(chunksTotal.value / chunksPageSize.value))
const canGoPrevious = computed(() => chunksPage.value > 1)
const canGoNext = computed(() => chunksPage.value < totalPages.value)

const goToPreviousPage = () => {
  if (canGoPrevious.value && currentDocument.value) {
    loadDocumentChunks(currentDocument.value.id, chunksPage.value - 1)
  }
}

const goToNextPage = () => {
  if (canGoNext.value && currentDocument.value) {
    loadDocumentChunks(currentDocument.value.id, chunksPage.value + 1)
  }
}

// Download document
const downloadDocument = async (doc: Document) => {
  if (!doc.file_path) {
    toast.error(t('admin.pages.kbs.detail.noFile'))
    return
  }
  
  try {
    // Should call download API or construct download link
    const downloadUrl = `/v1/files/download?path=${encodeURIComponent(doc.file_path)}`
    
    // Create temporary link for download
    const link = window.document.createElement('a')
    link.href = downloadUrl
    link.download = doc.file_name || doc.title
    window.document.body.appendChild(link)
    link.click()
    window.document.body.removeChild(link)
    
    toast.success(t('admin.pages.kbs.detail.downloadStarted'))
  } catch (error) {
    console.error('Failed to download document:', error)
    toast.error(t('admin.pages.kbs.detail.downloadFailed'))
  }
}


// Lifecycle
onMounted(() => {
  loadKnowledgeBase()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header Actions -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold">{{ t('admin.pages.kbs.detail.title') }}</h1>
        <p class="text-muted-foreground">{{ t('admin.pages.kbs.detail.kbName', { name: knowledgeBase?.name }) }}</p>
      </div>
      <Dialog v-model:open="showUploadDialog">
          <DialogTrigger asChild>
            <Button>
              <Upload class="h-4 w-4 mr-2" />
              {{ t('admin.pages.kbs.detail.upload') }}
            </Button>
          </DialogTrigger>
          <DialogContent class="max-w-2xl">
            <DialogHeader>
              <DialogTitle>{{ t('admin.pages.kbs.detail.uploadDialog.title') }}</DialogTitle>
              <DialogDescription>
                {{ t('admin.pages.kbs.detail.uploadDialog.description', { name: knowledgeBase?.name }) }}
              </DialogDescription>
            </DialogHeader>
            <FileUploadToKB 
              :default-knowledge-base-id="kbId"
              @upload-complete="handleUploadComplete" 
            />
          </DialogContent>
        </Dialog>
    </div>

    <DataTable 
      :data="data"
      :columns="tableColumns"
      :total-count="totalCount"
      :loading="loading"
      :selectable="false"
      :can-create="false"
      :show-filters="true"
      :bulk-actions="[]"
      :row-actions="rowActions"
      :empty-message="t('admin.pages.kbs.detail.noDocuments')"
      @refresh="handleRefresh"
      @search="handleSearch"
      @filter="handleFilter"
      @sort="handleSort"
      @paginate="handlePaginate"
      @row-action="handleDocumentAction"
    />
      <AlertDialog :open="showDeleteDialog" @update:open="handleDeleteDialogOpenChange">
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{{ t('admin.pages.kbs.detail.deleteConfirm.title') }}</AlertDialogTitle>
            <AlertDialogDescription>
              {{ t('admin.pages.kbs.detail.deleteConfirm.description', { title: documentToDelete?.title }) }}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{{ t('common.cancel') }}</AlertDialogCancel>
            <AlertDialogAction
              class="bg-destructive hover:bg-destructive/90"
              :disabled="deleteLoading"
              @click="confirmDeleteDocument"
            >
              {{ deleteLoading ? t('common.deleting') : t('common.confirmDelete') }}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <!-- Chunks Dialog -->
      <Dialog :open="showChunksDialog" @update:open="(open) => { if (!open) closeChunksDialog() }">
        <DialogContent class="max-w-4xl max-h-[80vh] grid-rows-[auto_minmax(0,1fr)_auto] p-0">
          <DialogHeader class="p-6 pb-0">
            <DialogTitle>{{ t('admin.pages.kbs.detail.chunks.title') }}</DialogTitle>
            <DialogDescription>
              {{ t('admin.pages.kbs.detail.chunks.description', { title: currentDocument?.title, count: chunksTotal }) }}
            </DialogDescription>
          </DialogHeader>
          <div class="gap-4 py-4 px-6 flex-1 overflow-y-auto">
            <div v-if="chunksLoading" class="flex items-center justify-center py-8">
              <div class="text-muted-foreground">{{ t('admin.pages.kbs.detail.chunks.loading') }}</div>
            </div>
            <div v-else-if="chunks.length === 0" class="flex items-center justify-center py-8">
              <div class="text-muted-foreground">{{ t('admin.pages.kbs.detail.chunks.empty') }}</div>
            </div>
            <div v-else class="space-y-4">
              <Card v-for="(chunk, index) in chunks" :key="chunk.id || index" class="w-full">
                <CardHeader class="pb-3">
                  <CardTitle class="text-sm font-medium">
                    {{ t('admin.pages.kbs.detail.chunks.chunkIndex', { index: index + 1 }) }}
                  </CardTitle>
                  <CardDescription class="text-xs">
                    <span v-if="chunk.metadata?.page">{{ t('admin.pages.kbs.detail.chunks.page', { page: chunk.metadata.page }) }}</span>
                    {{ t('admin.pages.kbs.detail.chunks.chars', { count: chunk.content?.length || 0 }) }}
                    <span v-if="chunk.score">{{ t('admin.pages.kbs.detail.chunks.similarity', { score: (chunk.score * 100).toFixed(1) }) }}</span>
                  </CardDescription>
                </CardHeader>
                <CardContent class="pt-0">
                  <div class="text-sm text-foreground whitespace-pre-wrap">
                    {{ chunk.content || t('admin.pages.kbs.detail.chunks.noContent') }}
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
          <DialogFooter class="p-6 pt-0 border-t">
            <div class="flex items-center justify-between w-full">
              <div class="text-sm text-muted-foreground">
                {{ t('admin.pages.kbs.detail.chunks.pagination', { page: chunksPage, totalPages: totalPages, total: chunksTotal }) }}
              </div>
              <div class="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  :disabled="!canGoPrevious || chunksLoading"
                  @click="goToPreviousPage"
                >
                  <ChevronLeft class="h-4 w-4 mr-1" />
                  {{ t('admin.pages.kbs.detail.chunks.prev') }}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  :disabled="!canGoNext || chunksLoading"
                  @click="goToNextPage"
                >
                  {{ t('admin.pages.kbs.detail.chunks.next') }}
                  <ChevronRight class="h-4 w-4 ml-1" />
                </Button>
              </div>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
  </div>
</template>
