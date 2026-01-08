<script setup lang="ts">
import { computed, h, ref } from 'vue'
import { Badge } from '~/components/ui/badge'
import { MessageSquare } from 'lucide-vue-next'
import ConversationMessagesSheet from '~/components/admin/ConversationMessagesSheet.vue'
import type { ModelViewConfig } from '~/components/model-view/types'

interface Conversation {
  id: string
  title: string
  assistant_id: string
  user_id: string
  status: string
  last_message_at: string | null
  message_count: number
  created_at: string
  updated_at: string
  assistant_name?: string
  user_name?: string
  user_email?: string
}

definePageMeta({
  breadcrumb: 'admin.pages.conversations.title',
  layout: 'admin'
})

const { t } = useI18n()

// Message dialog state
const showMessagesDialog = ref(false)
const selectedConversation = ref<Conversation | null>(null)

// Open message dialog
const openMessagesDialog = (conversation: Conversation) => {
  selectedConversation.value = conversation
  showMessagesDialog.value = true
}

// Status options
const statusOptions = computed(() => [
  { label: t('admin.pages.conversations.statusLabels.active'), value: 'ACTIVE' },
  { label: t('admin.pages.conversations.statusLabels.archived'), value: 'ARCHIVED' },
  { label: t('admin.pages.conversations.statusLabels.deleted'), value: 'DELETED' }
])

const statusColorMap: Record<string, string> = {
  ACTIVE: 'default',
  ARCHIVED: 'secondary',
  DELETED: 'destructive'
}

const statusLabelMap = computed(() => ({
  ACTIVE: t('admin.pages.conversations.statusLabels.active'),
  ARCHIVED: t('admin.pages.conversations.statusLabels.archived'),
  DELETED: t('admin.pages.conversations.statusLabels.deleted')
}))

// Conversation configuration
const conversationConfig = computed((): ModelViewConfig<Conversation> => ({
  title: t('admin.pages.conversations.title'),
  description: t('admin.pages.conversations.description'),
  apiEndpoint: '/v1/admin/conversations',
  showFilters: true,
  
  // Custom delete logic
  getDeleteParams: (item, filters) => {
    if (filters?.status === 'DELETED') {
      return { permanent: true }
    }
    return {}
  },
  getDeleteTitle: (count, filters) => {
    if (filters?.status === 'DELETED') {
      return t('admin.pages.conversations.permanentDeleteTitle')
    }
    return undefined
  },
  getDeleteDescription: (count, filters) => {
    if (filters?.status === 'DELETED') {
      return t('admin.pages.conversations.permanentDeleteDescription')
    }
    return undefined
  },

  filters: {
    status: {
      type: 'select',
      label: t('admin.pages.conversations.status'),
      options: statusOptions.value
    }
  },
  
  // Custom actions
  customActions: [
    {
      key: 'view-messages',
      label: t('admin.pages.conversations.viewMessages'),
      icon: h(MessageSquare, { class: 'h-4 w-4' }),
      variant: 'default' as const
    }
  ],
  
  columns: [
    {
      accessorKey: 'title',
      header: t('admin.pages.conversations.columns.title'),
      cell: (ctx) => {
        const title = (ctx.getValue() as string) || t('admin.pages.conversations.untitledConversation')
        return h('div', {
          class: 'max-w-[240px] truncate cursor-pointer hover:underline text-primary font-medium',
          title,
          onClick: () => openMessagesDialog(ctx.row.original)
        }, title)
      }
    },
    {
      accessorKey: 'user_name',
      header: t('admin.pages.conversations.columns.user'),
      cell: (ctx) => {
        const row = ctx.row.original
        const display = row.user_name || row.user_email || row.user_id
        return h('div', { class: 'text-sm' }, display)
      }
    },
    {
      accessorKey: 'assistant_name',
      header: t('admin.pages.conversations.columns.assistant')
    },
    {
      accessorKey: 'message_count',
      header: t('admin.pages.conversations.columns.messageCount'),
      cell: (ctx) => {
        const count = ctx.getValue() as number
        return count.toLocaleString()
      }
    },
    {
      accessorKey: 'status',
      header: t('admin.pages.conversations.columns.status'),
      cell: (ctx) => {
        const status = ctx.getValue() as string
        return h(Badge, { 
          variant: statusColorMap[status] as any
        }, () => statusLabelMap.value[status] || status)
      }
    },
    {
      accessorKey: 'last_message_at',
      header: t('admin.pages.conversations.columns.lastMessageAt'),
      cell: (ctx) => {
        const value = ctx.getValue() as string | null
        if (!value) return '-'
        return new Date(value).toLocaleString('zh-CN')
      }
    },
    {
      accessorKey: 'created_at',
      header: t('admin.pages.conversations.columns.createdAt'),
      cell: (ctx) => {
        const value = ctx.getValue() as string
        return new Date(value).toLocaleString('zh-CN')
      }
    }
  ],

  detailFields: [
    {
      name: 'id',
      label: t('admin.pages.conversations.fields.id'),
      type: 'text'
    },
    {
      name: 'title',
      label: t('admin.pages.conversations.fields.title'),
      type: 'text',
      render: (val: string) => {
        const content = val || t('admin.pages.conversations.untitledConversation')
        return h('div', {
          class: 'max-w-[320px] truncate',
          title: content
        }, content)
      }
    },
    {
      name: 'assistant_name',
      label: t('admin.pages.conversations.fields.assistant'),
      type: 'text'
    },
    {
      name: 'user_id',
      label: t('admin.pages.conversations.fields.userId'),
      type: 'text'
    },
    {
      name: 'status',
      label: t('admin.pages.conversations.columns.status'),
      type: 'text',
      render: (val: string) => statusLabelMap.value[val] || val
    },
    {
      name: 'message_count',
      label: t('admin.pages.conversations.columns.messageCount'),
      type: 'text',
      render: (val: number) => val.toLocaleString()
    },
    {
      name: 'last_message_at',
      label: t('admin.pages.conversations.columns.lastMessageAt'),
      type: 'datetime',
      render: (val: string | null) => {
        if (!val) return t('admin.pages.conversations.noLastMessage')
        return new Date(val).toLocaleString('zh-CN')
      }
    },
    {
      name: 'created_at',
      label: t('admin.pages.conversations.columns.createdAt'),
      type: 'datetime'
    },
    {
      name: 'updated_at',
      label: t('admin.pages.conversations.columns.updatedAt'),
      type: 'datetime'
    }
  ],

  formFields: [
    {
      name: 'title',
      label: t('admin.pages.conversations.fields.conversationTitle'),
      type: 'text',
      required: true,
      placeholder: t('admin.pages.conversations.fields.titlePlaceholder')
    },
    {
      name: 'status',
      label: t('admin.pages.conversations.columns.status'),
      type: 'select',
      required: true,
      options: statusOptions.value,
      defaultValue: 'ACTIVE'
    }
  ],

  // Conversation management typically only allows viewing, not creating, editing, or duplicating
  canCreate: false,
  canEdit: false,
  canDuplicate: false,
  canDelete: true
}))

// Handle custom actions
const handleRowAction = (action: any, item: Conversation) => {
  if (action.key === 'view-messages') {
    openMessagesDialog(item)
  }
}
</script>

<template>
  <ModelView 
    :config="conversationConfig" 
    @row-action="handleRowAction"
  />
  
  <!-- Message view sheet -->
  <ConversationMessagesSheet
    v-model:open="showMessagesDialog"
    :conversation-id="selectedConversation?.id || null"
    :conversation-title="selectedConversation?.title || t('admin.pages.conversations.untitledConversation')"
  />
</template>
