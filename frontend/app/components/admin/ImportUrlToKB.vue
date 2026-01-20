<script setup lang="ts">
import { ref } from 'vue'
import { Globe, FileText, ArrowRight, Loader2, Link as LinkIcon, Download } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { toast } from 'vue-sonner'

const props = defineProps<{
  knowledgeBaseId: string
}>()

const emit = defineEmits(['imported'])
const { t } = useI18n()
const { $api } = useNuxtApp()

const open = ref(false)
const url = ref('')
const loading = ref(false)
const importing = ref(false)
const previewData = ref<{ title?: string, content: string, url: string } | null>(null)

async function handleFetch() {
    if (!url.value) return
    loading.value = true
    previewData.value = null
    
    try {
        const res: any = await $api('/v1/rag/scrape', {
            method: 'POST',
            body: { url: url.value }
        })
        previewData.value = res
    } catch (e) {
        toast.error(t('admin.urlImport.fetchFailed'))
    } finally {
        loading.value = false
    }
}

async function handleImport() {
    if (!previewData.value) return
    importing.value = true
    
    try {
        // 1. Convert content to File object
        const content = `# ${previewData.value.title || 'Untitled'}\n\nSource: ${previewData.value.url}\n\n${previewData.value.content}`
        const blob = new Blob([content], { type: 'text/markdown' })
        
        // Generate filename: use title if available, otherwise domain name, fallback to timestamp
        let baseName = 'web-content'
        if (previewData.value.title) {
            baseName = previewData.value.title
        } else {
             try {
                baseName = new URL(previewData.value.url).hostname
             } catch {}
        }
        
        // Sanitize filename but allow Unicode characters (Chinese, Japanese, etc.)
        // Replace ONLY reserved filesystem characters and dangerous chars
        // Reserved: / \ : * ? " < > |
        const filename = baseName
            .replace(/[<>:"/\\|?*]/g, '_') // Replace reserved chars
            .replace(/\s+/g, '_')         // Replace spaces
            .slice(0, 50) + '.md'         // Truncate length
        
        const file = new File([blob], filename, { type: 'text/markdown' })
        
        // 2. Upload File
        const formData = new FormData()
        formData.append('file', file)
        formData.append('file_type', 'document')

        const uploadResponse: any = await $api('/v1/files/upload', {
          method: 'POST',
          body: formData
        })

        // 3. Link to KB
        await $api('/v1/admin/rag/documents/from-file', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            file_path: uploadResponse.file_path,
            knowledge_base_id: props.knowledgeBaseId,
            title: previewData.value.title || url.value
          })
        })
        
        toast.success(t('admin.urlImport.success'))
        open.value = false
        emit('imported')
        
        // Reset
        url.value = ''
        previewData.value = null

    } catch (e: any) {
        console.error(e)
        // Extract error message
        const errMsg = e.data?.detail || e.message || 'Unknown error'
        toast.error(t('admin.urlImport.importFailed') + ': ' + errMsg)
    } finally {
        importing.value = false
    }
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogTrigger as-child>
      <Button variant="outline" class="gap-2">
        <Globe class="w-4 h-4" />
        {{ t('admin.urlImport.button') }}
      </Button>
    </DialogTrigger>
    <DialogContent class="sm:max-w-[700px] max-h-[85vh] overflow-y-auto">
      <DialogHeader>
        <DialogTitle>{{ t('admin.urlImport.title') }}</DialogTitle>
        <DialogDescription>
          {{ t('admin.urlImport.description') }}
        </DialogDescription>
      </DialogHeader>

      <div class="grid gap-4 py-4">
        <!-- Input Section -->
        <div class="flex gap-2 items-end">
            <div class="grid w-full gap-1.5">
                <Label for="url">{{ t('admin.urlImport.urlLabel') }}</Label>
                <div class="relative">
                    <LinkIcon class="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input 
                        id="url" 
                        v-model="url" 
                        :placeholder="t('admin.urlImport.urlPlaceholder')" 
                        class="pl-9"
                        @keydown.enter="handleFetch"
                    />
                </div>
            </div>
            <Button @click="handleFetch" :disabled="!url || loading || importing">
                <Loader2 v-if="loading" class="w-4 h-4 mr-2 animate-spin" />
                <Download v-else class="w-4 h-4 mr-2" />
                {{ loading ? t('admin.urlImport.fetching') : t('admin.urlImport.fetch') }}
            </Button>
        </div>
        
        <!-- Preview Section -->
        <div v-if="previewData" class="space-y-4 border rounded-md p-4 bg-muted/30">
            <div class="flex items-center gap-2 font-medium">
                <FileText class="w-4 h-4 text-primary" />
                {{ t('admin.urlImport.preview') }}
            </div>
            
            <div class="grid gap-2">
                <Label>{{ t('admin.urlImport.originalUrl') }}</Label>
                <div class="text-sm text-muted-foreground truncate">{{ previewData.url }}</div>
            </div>

            <div class="grid w-full gap-1.5">
                <Label>Title</Label>
                <Input v-model="previewData.title" />
            </div>
            
            <div class="grid w-full gap-1.5">
                <Label>Content</Label>
                <Textarea 
                    v-model="previewData.content" 
                    rows="10" 
                    class="font-mono text-sm"
                />
            </div>
        </div>
      </div>

      <DialogFooter>
        <Button variant="secondary" @click="open = false">
            {{ t('common.cancel') }}
        </Button>
        <Button @click="handleImport" :disabled="!previewData || importing">
            <Loader2 v-if="importing" class="w-4 h-4 mr-2 animate-spin" />
            {{ importing ? t('admin.urlImport.importing') : t('admin.urlImport.import') }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
