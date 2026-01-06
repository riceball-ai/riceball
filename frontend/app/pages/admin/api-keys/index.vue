<script setup lang="ts">
import { ref, computed, h } from 'vue'
import { toast } from 'vue-sonner'
import { Key, Plus, Copy, Check } from 'lucide-vue-next'
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
import type { ModelViewConfig } from '~/components/model-view/types'

definePageMeta({
  layout: 'admin',
  breadcrumb: 'admin.sidebar.apiKeys'
})

const { t } = useI18n()
const { $api } = useNuxtApp()

interface ApiKeyRecord {
  id: string
  name: string
  prefix: string
  created_at: string
  last_used_at: string | null
}

// Create Dialog State
const showCreateDialog = ref(false)
const creating = ref(false)
const newKeyName = ref('')

// New Key Display Dialog State
const showNewKeyDialog = ref(false)
const newPlainKey = ref('')
const copied = ref(false)

const modelViewRef = ref()

// ModelView configuration
const config = computed((): ModelViewConfig<ApiKeyRecord> => ({
  title: t('admin.sidebar.apiKeys'),
  description: t('admin.apiKeys.description'),
  apiEndpoint: '/v1/user/api-keys',
  
  canCreate: false, // We handle creation manually
  canEdit: false,   // API keys usually aren't editable
  canDuplicate: false,

  columns: [
    {
      accessorKey: 'name',
      header: t('admin.apiKeys.name'),
      cell: (ctx) => {
        const name = ctx.getValue() as string
        return h('div', { class: 'font-medium' }, name)
      }
    },
    {
      accessorKey: 'prefix',
      header: 'Key Prefix',
      cell: (ctx) => {
        const prefix = ctx.getValue() as string
        return h('code', { class: 'bg-muted px-1 py-0.5 rounded text-xs' }, prefix)
      }
    },
    {
      accessorKey: 'created_at',
      header: t('common.createdAt'),
      cell: (ctx) => new Date(ctx.getValue() as string).toLocaleDateString()
    },
    {
      accessorKey: 'last_used_at',
      header: t('admin.apiKeys.lastUsedAt'),
      cell: (ctx) => {
        const val = ctx.getValue() as string
        if (!val) return '-'
        return new Date(val).toLocaleString()
      }
    }
  ],
  
  customActions: []
}))

const openCreateDialog = () => {
  newKeyName.value = ''
  showCreateDialog.value = true
}

const handleCreateKey = async () => {
  if (!newKeyName.value.trim()) return
  
  creating.value = true
  try {
    const res = await $api<{ key: string }>('/v1/user/api-keys', {
      method: 'POST',
      body: { name: newKeyName.value }
    })
    
    showCreateDialog.value = false
    newPlainKey.value = res.key
    showNewKeyDialog.value = true
    
    // Refresh list
    modelViewRef.value?.loadData()
    toast.success(t('admin.apiKeys.createSuccess'))
  } catch (error) {
    console.error(error)
    toast.error(t('components.modelView.createFailed'))
  } finally {
    creating.value = false
  }
}

const copyToClipboard = async () => {
  try {
    await navigator.clipboard.writeText(newPlainKey.value)
    copied.value = true
    toast.success('Copied to clipboard')
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (e) {
    toast.error('Failed to copy')
  }
}
</script>

<template>
  <div>
    <ModelView ref="modelViewRef" :config="config">
      <template #actions>
        <Button @click="openCreateDialog">
          <Plus class="mr-2 h-4 w-4" />
          {{ t('admin.apiKeys.create') }}
        </Button>
      </template>
    </ModelView>

    <!-- Create Dialog -->
    <Dialog v-model:open="showCreateDialog">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{{ t('admin.apiKeys.createNew') }}</DialogTitle>
          <DialogDescription>{{ t('admin.apiKeys.createDescription') }}</DialogDescription>
        </DialogHeader>
        
        <div class="space-y-4 py-4">
          <div class="space-y-2">
            <Label for="keyName">{{ t('admin.apiKeys.name') }}</Label>
            <Input id="keyName" v-model="newKeyName" :placeholder="t('admin.apiKeys.namePlaceholder')" @keyup.enter="handleCreateKey" />
          </div>
        </div>
        
        <DialogFooter>
          <Button variant="outline" @click="showCreateDialog = false">{{ t('components.modelView.cancel') }}</Button>
          <Button @click="handleCreateKey" :disabled="creating || !newKeyName.trim()">
            {{ creating ? t('components.modelView.saving') : t('components.modelView.create') }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Show Key Dialog (Once) -->
    <Dialog v-model:open="showNewKeyDialog">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{{ t('admin.apiKeys.keyGenerated') }}</DialogTitle>
          <DialogDescription class="text-destructive font-medium">
            {{ t('admin.apiKeys.saveWarning') }}
          </DialogDescription>
        </DialogHeader>
        
        <div class="flex items-center space-x-2 py-4">
          <div class="relative flex-1">
            <Input readonly v-model="newPlainKey" class="pr-10 font-mono text-sm" />
          </div>
          <Button size="icon" variant="outline" @click="copyToClipboard">
            <Check v-if="copied" class="h-4 w-4" />
            <Copy v-else class="h-4 w-4" />
          </Button>
        </div>
        
        <DialogFooter>
          <Button @click="showNewKeyDialog = false">{{ t('admin.apiKeys.done') }}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
