<script setup lang="ts">
import { ref, computed, h } from 'vue'
import { toast } from 'vue-sonner'
import { Loader2, Upload, Copy, File as FileIcon } from 'lucide-vue-next'
import { Button } from '~/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '~/components/ui/dialog'
import { Input } from '~/components/ui/input'
import { Label } from '~/components/ui/label'
import ModelView from '~/components/model-view/ModelView.vue'
import type { ModelViewConfig, ActionConfig } from '~/components/model-view/types'

definePageMeta({
  layout: 'admin',
  breadcrumb: 'admin.sidebar.files'
})

const { t } = useI18n()

interface FileRecord {
  id: string
  filename: string
  content_type: string
  file_size: number
  file_type: string
  file_path: string
  uploaded_by: string
  uploaded_by_name?: string
  created_at: string
  metadata: Record<string, any>
  url: string
}

// Upload state
const showUploadDialog = ref(false)
const uploading = ref(false)
const selectedFile = ref<File | null>(null)
const modelViewRef = ref()

// ModelView configuration
const config = computed((): ModelViewConfig<FileRecord> => ({
  title: t('admin.sidebar.files'),
  description: 'Manage uploaded files',
  apiEndpoint: '/v1/admin/files',
  
  canCreate: false, // Disable default create button
  canEdit: false,   // Disable edit for now
  
  columns: [
    {
      accessorKey: 'filename',
      header: 'Name',
      meta: { width: 200 },
      cell: (ctx) => {
        const filename = ctx.getValue() as string
        return h('div', { class: 'flex items-center' }, [
          h(FileIcon, { class: 'mr-2 h-4 w-4 text-muted-foreground' }),
          filename
        ])
      }
    },
    {
      accessorKey: 'file_size',
      header: 'Size',
      cell: (ctx) => formatSize(ctx.getValue() as number)
    },
    {
      accessorKey: 'content_type',
      header: 'Type',
      meta: { width: 200 },
    },
    {
      accessorKey: 'uploaded_by',
      header: 'Uploaded By',
      cell: (ctx) => {
        const row = ctx.row.original as FileRecord
        return row.uploaded_by_name || row.uploaded_by
      }
    },
    {
      accessorKey: 'created_at',
      header: 'Date',
      cell: (ctx) => new Date(ctx.getValue() as string).toLocaleDateString()
    }
  ],
  
  customActions: [
    {
      key: 'copyLink',
      label: 'Copy Link',
      icon: Copy,
      variant: 'ghost'
    }
  ]
}))

const formatSize = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const handleRowAction = (action: ActionConfig, row: FileRecord) => {
  if (action.key === 'copyLink') {
    if (row.url) {
      navigator.clipboard.writeText(row.url)
      toast.success('Link copied to clipboard')
    } else {
      toast.error('No download URL available')
    }
  }
}

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files?.length) {
    selectedFile.value = target.files[0]
  }
}

const handleUpload = async () => {
  if (!selectedFile.value) return

  const formData = new FormData()
  formData.append('file', selectedFile.value)
  formData.append('file_type', 'document') // Default to document

  uploading.value = true
  try {
    const { $api } = useNuxtApp()
    await $api('/v1/admin/files/upload', {
      method: 'POST',
      body: formData
    })
    
    toast.success('File uploaded successfully')
    showUploadDialog.value = false
    selectedFile.value = null
    
    // Refresh list
    if (modelViewRef.value) {
      modelViewRef.value.loadData()
    }
  } catch (e) {
    toast.error('Upload failed')
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <ModelView 
      ref="modelViewRef"
      :config="config" 
      @row-action="handleRowAction"
    >
      <template #actions>
        <Button @click="showUploadDialog = true">
          <Upload class="mr-2 h-4 w-4" />
          Upload File
        </Button>
      </template>
    </ModelView>

    <Dialog v-model:open="showUploadDialog">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Upload File</DialogTitle>
          <DialogDescription>
            Select a file to upload to the system.
          </DialogDescription>
        </DialogHeader>
        
        <div class="grid gap-4 py-4">
          <div class="grid gap-2">
            <Label htmlFor="file">File</Label>
            <Input
              id="file"
              type="file"
              @change="handleFileSelect"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" @click="showUploadDialog = false">
            Cancel
          </Button>
          <Button :disabled="!selectedFile || uploading" @click="handleUpload">
            <Loader2 v-if="uploading" class="mr-2 h-4 w-4 animate-spin" />
            Upload
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
