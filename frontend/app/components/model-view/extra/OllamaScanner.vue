<script setup lang="ts">
import { ref, watch } from 'vue'
import { RocketIcon, RefreshCw } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { toast } from 'vue-sonner'

// Props & Emits
const emit = defineEmits(['scanned'])

const { t } = useI18n()
const { $api } = useNuxtApp()

// State
const open = ref(false)
const endpoint = ref('http://localhost:11434')
const isLoading = ref(false)
const error = ref('')
const scannedModels = ref<any[]>([])
const success = ref(false)

// Reset state when dialog opens
watch(open, (newVal) => {
  if (newVal) {
    error.value = ''
    success.value = false
    scannedModels.value = []
    isLoading.value = false
  }
})

// Actions
async function handleScan() {
  isLoading.value = true
  error.value = ''
  success.value = false
  scannedModels.value = []

  try {
    const res = await $api('/v1/admin/providers/ollama/scan', {
      method: 'POST',
      body: {
        base_url: endpoint.value,
        provider_name: 'Ollama Local'
      }
    })
    
    scannedModels.value = res as any[]
    success.value = true
    
    toast.success(t('common.success'), { 
       description: t('admin.scanner.import_success', { count: scannedModels.value.length })
    })

    // Auto close after 1.5s if success
    setTimeout(() => {
        open.value = false
        emit('scanned')
    }, 1500)

  } catch (err: any) {
    console.error(err)
    if (err.data && err.data.detail) {
        error.value = err.data.detail
    } else {
        error.value = t('admin.scanner.connection_failed')
    }
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogTrigger as-child>
      <Button variant="outline" class="gap-2">
        <RocketIcon class="w-4 h-4" />
        {{ t('admin.scanner.button') }}
      </Button>
    </DialogTrigger>
    <DialogContent class="sm:max-w-[425px]">
      <DialogHeader>
        <DialogTitle>{{ t('admin.scanner.title') }}</DialogTitle>
        <DialogDescription>
          {{ t('admin.scanner.description') }}
        </DialogDescription>
      </DialogHeader>
      
      <div class="grid gap-4 py-4">
        <!-- Error Alert -->
        <Alert v-if="error" variant="destructive">
          <AlertTitle>{{ t('admin.scanner.connection_failed') }}</AlertTitle>
          <AlertDescription>
            {{ error }}
            <div class="mt-2 text-xs opacity-90" v-html="t('admin.scanner.hint_docker', { url: 'http://host.docker.internal:11434' })">
            </div>
          </AlertDescription>
        </Alert>
        
        <!-- Success Alert -->
        <Alert v-if="success" class="bg-green-50 text-green-700 border-green-200">
          <AlertTitle class="flex items-center gap-2">
            <RefreshCw class="w-4 h-4" /> {{ t('common.success') }}
          </AlertTitle>
          <AlertDescription>
             {{ t('admin.scanner.import_success', { count: scannedModels.length }) }}
          </AlertDescription>
        </Alert>

        <div class="grid grid-cols-4 items-center gap-4">
          <Label for="endpoint" class="text-right">
             {{ t('admin.scanner.label_url') }}
          </Label>
          <Input
            id="endpoint"
            v-model="endpoint"
            class="col-span-3"
            placeholder="http://localhost:11434"
          />
        </div>
      </div>
      
      <DialogFooter>
        <Button 
            @click="handleScan" 
            :disabled="isLoading || success"
        >
            <RefreshCw v-if="isLoading" class="w-4 h-4 mr-2 animate-spin" />
            {{ isLoading ? t('admin.scanner.scanning') : t('admin.scanner.start') }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
