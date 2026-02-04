<script setup lang="ts">
import { ref, reactive } from 'vue'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { 
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue, 
} from '@/components/ui/select'
import { Loader2 } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { MCPServerTypeEnum } from '~/types/mcp'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'success'): void
}>()

const { createServer } = useMCP()
const { t } = useI18n()

const loading = ref(false)

const form = reactive({
  name: '',
  description: '',
  url: '',
  headers: '{}'
})

const serverType = ref<MCPServerTypeEnum>(MCPServerTypeEnum.HTTP)

const resetForm = () => {
  form.name = ''
  form.description = ''
  form.url = ''
  form.headers = '{}'
  serverType.value = MCPServerTypeEnum.HTTP
}

const handleSubmit = async () => {
  loading.value = true
  try {
    let connectionConfig = {}
    
    if (!form.url) {
      toast.error(t('admin.mcp.custom.error.urlRequired'))
      loading.value = false
      return
    }
    
    let headers = {}
    try {
      headers = JSON.parse(form.headers || '{}')
    } catch (e) {
      toast.error(t('admin.mcp.custom.error.invalidHeaders'))
      loading.value = false
      return
    }

    connectionConfig = {
      url: form.url,
      headers: headers
    }

    const payload = {
      name: form.name,
      description: form.description,
      server_type: serverType.value,
      connection_config: connectionConfig,
      is_active: true
    }

    await createServer(payload)
    toast.success(t('admin.mcp.custom.success'))
    emit('success')
    emit('update:open', false)
    resetForm()
  } catch (error: any) {
    console.error(error)
    toast.error(error.message || t('admin.mcp.custom.error.failed'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <Dialog :open="open" @update:open="$emit('update:open', $event)">
    <DialogContent class="sm:max-w-[500px]">
      <DialogHeader>
        <DialogTitle>{{ t('admin.mcp.custom.title') }}</DialogTitle>
        <DialogDescription>
          {{ t('admin.mcp.custom.description') }}
        </DialogDescription>
      </DialogHeader>

      <div class="grid gap-4 py-4">
        <div class="grid gap-2">
          <Label for="server-name">{{ t('admin.mcp.custom.name') }}</Label>
          <Input id="server-name" v-model="form.name" :placeholder="t('admin.mcp.custom.namePlaceholder')" />
        </div>
        
        <div class="grid gap-2">
          <Label for="server-desc">{{ t('admin.mcp.custom.desc') }}</Label>
          <Input id="server-desc" v-model="form.description" :placeholder="t('admin.mcp.custom.descPlaceholder')" />
        </div>

        <div class="grid gap-2">
           <Label>{{ t('admin.mcp.custom.transport') }}</Label>
           <Select v-model="serverType">
            <SelectTrigger>
              <SelectValue :placeholder="t('admin.mcp.custom.transportPlaceholder')" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem :value="MCPServerTypeEnum.HTTP">{{ t('admin.mcp.custom.http') }}</SelectItem>
              <SelectItem :value="MCPServerTypeEnum.SSE">{{ t('admin.mcp.custom.sse') }}</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div class="grid gap-4">
            <div class="grid gap-2">
                <Label for="server-url">{{ t('admin.mcp.custom.url') }}</Label>
                <Input id="server-url" v-model="form.url" :placeholder="t('admin.mcp.custom.urlPlaceholder')" />
            </div>
            <div class="grid gap-2">
                <Label for="server-headers">{{ t('admin.mcp.custom.headers') }}</Label>
                <Textarea 
                    id="server-headers" 
                    v-model="form.headers" 
                    class="font-mono text-xs" 
                    placeholder='{ "Authorization": "Bearer key" }'
                />
            </div>
        </div>

      </div>

      <DialogFooter>
        <Button variant="outline" @click="$emit('update:open', false)">
          {{ t('common.cancel') }}
        </Button>
        <Button @click="handleSubmit" :disabled="loading || !form.name">
          <Loader2 v-if="loading" class="mr-2 h-4 w-4 animate-spin" />
          {{ t('admin.mcp.custom.add') }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
