<script setup lang="ts">
import { ref, h, onMounted, computed, watch } from 'vue'
import { Badge } from '~/components/ui/badge'
import { Button } from '~/components/ui/button'
import { Input } from '~/components/ui/input'
import { Label } from '~/components/ui/label'
import { Textarea } from '~/components/ui/textarea'
import { FileText, Upload, Trash2, Eye, Split, ChevronLeft, ChevronRight, Settings, FlaskConical, X, Search, Save } from 'lucide-vue-next'
import type { ColumnDef, SortingState, PaginationState } from '@tanstack/vue-table'
import DataTable from '~/components/model-view/DataTable.vue'
import type { ActionConfig } from '~/components/model-view/types'
import DocIcon from '~/components/file-type-icon/Doc.vue'
import PdfIcon from '~/components/file-type-icon/Pdf.vue'
import MdIcon from '~/components/file-type-icon/Md.vue'
import TxtIcon from '~/components/file-type-icon/Txt.vue'
import XlsIcon from '~/components/file-type-icon/Xls.vue'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '~/components/ui/collapsible'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetFooter,
} from '~/components/ui/sheet'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '~/components/ui/tabs'
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
  breadcrumb: 'admin.pages.knowledgeBases.detail.breadcrumb',
  layout: 'admin'
})

// State
const showUploadArea = ref(false)
const knowledgeBase = ref<KnowledgeBase | null>(null)
const documentsKey = ref(0) // Force refresh document list
const loading = ref(false)
const deleteLoading = ref(false)
const showDeleteDialog = ref(false)
const documentToDelete = ref<Document | null>(null)

// Chunk-related state
const showChunksSheet = ref(false)
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
    toast.error(t('admin.pages.knowledgeBases.detail.loadFailed'))
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
    toast.error(t('admin.pages.knowledgeBases.detail.loadDataFailed'))
  } finally {
    loading.value = false
  }
}

const tableColumns: ColumnDef<Document>[] = [
    {
      accessorKey: 'title',
      header: t('admin.pages.knowledgeBases.detail.columns.title'),
      meta: {
        width: 200
      },
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
        
        return h('div', { 
          class: 'flex items-center cursor-pointer hover:text-primary transition-colors overflow-hidden', // Ensure overflow is hidden
          title: row.title, // Add title attribute for tooltip on hover
          onClick: () => openChunksSheet(row) // Click title to open chunks
        }, [
          h(IconComponent, { class: 'size-8 mr-1 flex-shrink-0' }), // Prevent icon from shrinking
          h('span', { class: 'truncate' }, row.title) // Apply truncate to text
        ])
      }
    },
    {
      accessorKey: 'file_size',
      header: t('admin.pages.knowledgeBases.detail.columns.size'),
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
      header: t('admin.pages.knowledgeBases.detail.columns.type')
    },
    {
      accessorKey: 'status',
      header: t('admin.pages.knowledgeBases.detail.columns.status'),
      cell: (context) => {
        const status = context.getValue() as string
        const variants = {
          'PROCESSING': 'secondary',
          'COMPLETED': 'default',
          'FAILED': 'destructive'
        } as const
        
        const labels = {
          'PROCESSING': t('admin.pages.knowledgeBases.detail.status.processing'),
          'COMPLETED': t('admin.pages.knowledgeBases.detail.status.completed'),
          'FAILED': t('admin.pages.knowledgeBases.detail.status.failed')
        } as const
        
        return h(Badge, {
          variant: variants[status as keyof typeof variants] || 'secondary'
        }, () => labels[status as keyof typeof labels] || status)
      }
    },
    {
      accessorKey: 'created_at',
      header: t('admin.pages.knowledgeBases.detail.columns.createdAt'),
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
    label: t('admin.pages.knowledgeBases.detail.viewChunks'),
    icon: Split,
  },
  {
    key: 'delete',
    label: t('admin.pages.knowledgeBases.detail.delete'),
    icon: Trash2,
    variant: 'destructive',
  }
]

// Handle file upload complete
const handleUploadComplete = () => {
  // showUploadArea.value = false // Keep open for continuous upload
  documentsKey.value++ // Refresh document list
  loadData()
  toast.success(t('admin.pages.knowledgeBases.detail.uploadSuccess'))
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
      openChunksSheet(row)
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
    toast.success(t('admin.pages.knowledgeBases.detail.deleteConfirm.success'))
    resetDeleteDialog()
    loadData()
  } catch (error) {
    console.error('Failed to delete document:', error)
    toast.error(t('admin.pages.knowledgeBases.detail.deleteConfirm.failed'))
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
    toast.error(t('admin.pages.knowledgeBases.detail.chunks.loadFailed'))
  } finally {
    chunksLoading.value = false
  }
}

// Open chunk sheet
const openChunksSheet = (document: Document) => {
  currentDocument.value = document
  showChunksSheet.value = true
  chunksPage.value = 1
  loadDocumentChunks(document.id, 1)
}

// Close chunk sheet
const closeChunksSheet = () => {
  showChunksSheet.value = false
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
    toast.error(t('admin.pages.knowledgeBases.detail.noFile'))
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
    
    toast.success(t('admin.pages.knowledgeBases.detail.downloadStarted'))
  } catch (error) {
    console.error('Failed to download document:', error)
    toast.error(t('admin.pages.knowledgeBases.detail.downloadFailed'))
  }
}

// Retrieval Testing
const testQuery = ref('')
const testK = ref(5)
const testResults = ref<any[]>([])
const testLoading = ref(false)

const handleTestRetrieval = async () => {
  if (!testQuery.value) return
  testLoading.value = true
  testResults.value = []
  try {
    const response: any = await $api('/v1/admin/rag/get_relevant_documents', {
      method: 'POST',
      body: {
        query: testQuery.value,
        knowledge_base_id: kbId,
        k: testK.value
      }
    })
    testResults.value = response.documents || []
    if (testResults.value.length === 0) {
      toast.info(t('admin.pages.knowledgeBases.testing.noResults'))
    }
  } catch (error) {
    console.error('Retrieval test failed:', error)
    toast.error('Retrieval test failed')
  } finally {
    testLoading.value = false
  }
}

// General Settings
const settingsForm = ref({
  name: '',
  description: '',
  chunk_size: 1000,
  chunk_overlap: 200
})
const settingsLoading = ref(false)

watch(knowledgeBase, (kb) => {
  if (kb) {
    settingsForm.value = {
      name: kb.name,
      description: kb.description || '',
      chunk_size: kb.chunk_size,
      chunk_overlap: kb.chunk_overlap
    }
  }
})

const handleUpdateSettings = async () => {
  settingsLoading.value = true
  try {
    await $api(`/v1/admin/rag/knowledge-bases/${kbId}`, {
      method: 'PUT',
      body: settingsForm.value
    })
    toast.success(t('admin.pages.knowledgeBases.detail.settings.updateSuccess'))
    loadKnowledgeBase() // Refresh
  } catch (error) {
    console.error('Update settings failed:', error)
    toast.error(t('admin.pages.knowledgeBases.detail.settings.updateFailed'))
  } finally {
    settingsLoading.value = false
  }
}


// Lifecycle
onMounted(() => {
  loadKnowledgeBase()
})
</script>

<template>
  <div class="flex flex-col h-[calc(100vh-6rem)] -m-6">
    <!-- Header -->
    <div class="flex items-center justify-between px-6 py-4 border-b bg-background">
      <div>
        <h1 class="text-xl font-semibold">{{ knowledgeBase?.name || t('admin.pages.knowledgeBases.detail.title') }}</h1>
        <p class="text-sm text-muted-foreground">{{ knowledgeBase?.description || t('admin.pages.knowledgeBases.detail.kbName', { name: knowledgeBase?.name }) }}</p>
      </div>
      <div class="flex items-center gap-2">
        <!-- Global Actions if any -->
      </div>
    </div>

    <!-- Main Content with Tabs -->
    <Tabs default-value="documents" class="flex-1 flex flex-col overflow-hidden">
      <div class="px-6 py-2 border-b bg-background">
        <TabsList>
          <TabsTrigger value="documents">
            <FileText class="w-4 h-4 mr-2" />
            {{ t('admin.pages.knowledgeBases.detail.tabs.documents') }}
          </TabsTrigger>
          <TabsTrigger value="testing">
            <FlaskConical class="w-4 h-4 mr-2" />
            {{ t('admin.pages.knowledgeBases.detail.tabs.testing') }}
          </TabsTrigger>
          <TabsTrigger value="settings">
            <Settings class="w-4 h-4 mr-2" />
            {{ t('admin.pages.knowledgeBases.detail.tabs.settings') }}
          </TabsTrigger>
        </TabsList>
      </div>

      <!-- Documents Tab -->
      <TabsContent value="documents" class="flex-1 overflow-auto p-6 m-0">
        <div class="space-y-4">
          <div class="flex justify-end">
            <Button 
              variant="outline" 
              :class="{ 'bg-muted': showUploadArea }"
              @click="showUploadArea = !showUploadArea"
            >
              <component :is="showUploadArea ? X : Upload" class="h-4 w-4 mr-2" />
              {{ showUploadArea ? t('common.cancel') : t('admin.pages.knowledgeBases.detail.upload') }}
            </Button>
          </div>

          <Collapsible :open="showUploadArea" class="space-y-2">
            <CollapsibleContent class="data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down overflow-hidden">
              <Card class="border-dashed border-2 shadow-none bg-muted/30">
                <CardHeader class="pb-2">
                  <CardTitle class="text-base font-medium">{{ t('admin.pages.knowledgeBases.detail.uploadDialog.title') }}</CardTitle>
                  <CardDescription>
                    {{ t('admin.pages.knowledgeBases.detail.uploadDialog.description', { name: knowledgeBase?.name }) }}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <FileUploadToKB 
                    :knowledge-base-id="kbId"
                    @upload-complete="handleUploadComplete" 
                  />
                </CardContent>
              </Card>
            </CollapsibleContent>
          </Collapsible>

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
            :empty-message="t('admin.pages.knowledgeBases.detail.noDocuments')"
            @refresh="handleRefresh"
            @search="handleSearch"
            @filter="handleFilter"
            @sort="handleSort"
            @paginate="handlePaginate"
            @row-action="handleDocumentAction"
          />
        </div>
      </TabsContent>

      <!-- Testing Tab -->
      <TabsContent value="testing" class="flex-1 overflow-auto p-6 m-0">
        <div class="max-w-4xl mx-auto space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>{{ t('admin.pages.knowledgeBases.detail.testing.title') }}</CardTitle>
              <CardDescription>{{ t('admin.pages.knowledgeBases.detail.testing.description') }}</CardDescription>
            </CardHeader>
            <CardContent class="space-y-4">
              <div class="flex gap-4">
                <div class="flex-1">
                  <Label for="query">{{ t('admin.pages.knowledgeBases.detail.testing.query') }}</Label>
                  <div class="flex gap-2 mt-1.5">
                    <Input 
                      id="query" 
                      v-model="testQuery" 
                      :placeholder="t('admin.pages.knowledgeBases.detail.testing.queryPlaceholder')" 
                      @keyup.enter="handleTestRetrieval"
                    />
                    <Button @click="handleTestRetrieval" :disabled="testLoading || !testQuery">
                      <Search class="w-4 h-4 mr-2" v-if="!testLoading" />
                      <div class="h-4 w-4 mr-2 animate-spin rounded-full border-2 border-current border-t-transparent" v-else />
                      {{ t('admin.pages.knowledgeBases.detail.testing.test') }}
                    </Button>
                  </div>
                </div>
                <div class="w-24">
                  <Label for="topK">{{ t('admin.pages.knowledgeBases.detail.testing.topK') }}</Label>
                  <Input id="topK" type="number" v-model="testK" min="1" max="20" class="mt-1.5" />
                </div>
              </div>
            </CardContent>
          </Card>

          <div v-if="testResults.length > 0" class="space-y-4">
            <h3 class="text-lg font-medium">{{ t('admin.pages.knowledgeBases.detail.testing.results') }}</h3>
            <Card v-for="(doc, index) in testResults" :key="index" class="overflow-hidden">
              <CardHeader class="py-3 bg-muted/30">
                <div class="flex justify-between items-center">
                  <CardTitle class="text-sm font-medium">
                    #{{ index + 1 }}
                    <span v-if="doc.metadata?.score" class="ml-2 text-xs font-normal text-muted-foreground">
                      {{ t('admin.pages.knowledgeBases.detail.testing.score') }}: {{ doc.metadata.score.toFixed(4) }}
                    </span>
                  </CardTitle>
                  <Badge variant="outline" v-if="doc.metadata?.source">
                    {{ doc.metadata.source }}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent class="p-4">
                <div class="text-sm whitespace-pre-wrap bg-muted/30 p-3 rounded-md font-mono text-xs">
                  {{ doc.page_content }}
                </div>
                <div class="mt-2 flex flex-wrap gap-2">
                  <Badge variant="secondary" class="text-xs font-normal" v-for="(value, key) in doc.metadata" :key="key">
                    {{ key }}: {{ value }}
                  </Badge>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </TabsContent>

      <!-- Settings Tab -->
      <TabsContent value="settings" class="flex-1 overflow-auto p-6 m-0">
        <div class="max-w-2xl space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>{{ t('admin.pages.knowledgeBases.detail.settings.title') }}</CardTitle>
              <CardDescription>{{ t('admin.pages.knowledgeBases.detail.settings.description') }}</CardDescription>
            </CardHeader>
            <CardContent class="space-y-4">
              <div class="grid gap-2">
                <Label for="name">{{ t('admin.pages.knowledgeBases.formFields.name') }}</Label>
                <Input id="name" v-model="settingsForm.name" />
              </div>
              <div class="grid gap-2">
                <Label for="description">{{ t('common.description') }}</Label>
                <Textarea id="description" v-model="settingsForm.description" />
              </div>
              <div class="grid grid-cols-2 gap-4">
                <div class="grid gap-2">
                  <Label for="chunk_size">{{ t('admin.pages.knowledgeBases.formFields.chunkSize') }}</Label>
                  <Input id="chunk_size" type="number" v-model="settingsForm.chunk_size" />
                  <p class="text-xs text-muted-foreground">{{ t('admin.pages.knowledgeBases.formFields.chunkSizeHelp') }}</p>
                </div>
                <div class="grid gap-2">
                  <Label for="chunk_overlap">{{ t('admin.pages.knowledgeBases.formFields.chunkOverlap') }}</Label>
                  <Input id="chunk_overlap" type="number" v-model="settingsForm.chunk_overlap" />
                  <p class="text-xs text-muted-foreground">{{ t('admin.pages.knowledgeBases.formFields.chunkOverlapHelp') }}</p>
                </div>
              </div>
              <div class="grid gap-2">
                <Label>{{ t('admin.pages.knowledgeBases.formFields.embeddingModel') }}</Label>
                <div class="p-2 border rounded-md bg-muted/50 text-sm text-muted-foreground">
                  {{ knowledgeBase?.embedding_model_id || t('admin.pages.knowledgeBases.notSet') }}
                  <span class="ml-2 text-xs">(Cannot be changed)</span>
                </div>
              </div>
            </CardContent>
            <CardFooter>
              <Button @click="handleUpdateSettings" :disabled="settingsLoading">
                <Save class="w-4 h-4 mr-2" v-if="!settingsLoading" />
                <div class="h-4 w-4 mr-2 animate-spin rounded-full border-2 border-current border-t-transparent" v-else />
                {{ t('admin.pages.knowledgeBases.detail.settings.save') }}
              </Button>
            </CardFooter>
          </Card>
        </div>
      </TabsContent>
    </Tabs>

    <!-- Delete Alert Dialog -->
    <AlertDialog :open="showDeleteDialog" @update:open="handleDeleteDialogOpenChange">
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{{ t('admin.pages.knowledgeBases.detail.deleteConfirm.title') }}</AlertDialogTitle>
          <AlertDialogDescription>
            {{ t('admin.pages.knowledgeBases.detail.deleteConfirm.description', { title: documentToDelete?.title }) }}
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

    <!-- Chunks Sheet -->
    <Sheet :open="showChunksSheet" @update:open="(open) => { if (!open) closeChunksSheet() }">
      <SheetContent class="w-[400px] sm:w-[600px] flex flex-col p-0 gap-0">
        <SheetHeader class="p-6 border-b">
          <SheetTitle>{{ t('admin.pages.knowledgeBases.detail.chunks.title') }}</SheetTitle>
          <SheetDescription>
            {{ t('admin.pages.knowledgeBases.detail.chunks.description', { title: currentDocument?.title, count: chunksTotal }) }}
          </SheetDescription>
        </SheetHeader>
        
        <div class="flex-1 overflow-y-auto p-6 bg-muted/10">
          <div v-if="chunksLoading" class="flex items-center justify-center py-8">
            <div class="text-muted-foreground">{{ t('admin.pages.knowledgeBases.detail.chunks.loading') }}</div>
          </div>
          <div v-else-if="chunks.length === 0" class="flex items-center justify-center py-8">
            <div class="text-muted-foreground">{{ t('admin.pages.knowledgeBases.detail.chunks.empty') }}</div>
          </div>
          <div v-else class="space-y-4">
            <Card v-for="(chunk, index) in chunks" :key="chunk.id || index" class="w-full shadow-sm hover:shadow-md transition-shadow">
              <CardHeader class="pb-2 pt-4 px-4">
                <div class="flex justify-between items-start">
                  <CardTitle class="text-sm font-medium text-primary">
                    #{{ (chunksPage - 1) * chunksPageSize + index + 1 }}
                  </CardTitle>
                  <div class="flex gap-2 text-xs text-muted-foreground">
                    <Badge variant="outline" v-if="chunk.metadata?.page">
                      {{ t('admin.pages.knowledgeBases.detail.chunks.page', { page: chunk.metadata.page }) }}
                    </Badge>
                    <Badge variant="secondary">
                      {{ chunk.content?.length || 0 }} chars
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent class="px-4 pb-4">
                <div class="text-sm text-foreground/80 whitespace-pre-wrap font-mono bg-muted/30 p-2 rounded text-xs">
                  {{ chunk.content || t('admin.pages.knowledgeBases.detail.chunks.noContent') }}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        <SheetFooter class="p-4 border-t bg-background">
          <div class="flex items-center justify-between w-full">
            <div class="text-xs text-muted-foreground">
              {{ t('admin.pages.knowledgeBases.detail.chunks.pagination', { page: chunksPage, totalPages: totalPages, total: chunksTotal }) }}
            </div>
            <div class="flex items-center space-x-2">
              <Button
                variant="outline"
                size="icon"
                class="h-8 w-8"
                :disabled="!canGoPrevious || chunksLoading"
                @click="goToPreviousPage"
              >
                <ChevronLeft class="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                class="h-8 w-8"
                :disabled="!canGoNext || chunksLoading"
                @click="goToNextPage"
              >
                <ChevronRight class="h-4 w-4" />
              </Button>
            </div>
          </div>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  </div>
</template>
