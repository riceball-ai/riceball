<script setup lang="ts">
import { ref, computed, h } from 'vue'
import { NuxtLink } from '#components'
import { FileText } from 'lucide-vue-next'
import type { ModelViewConfig } from '~/components/model-view/types'
import type { KnowledgeBase, Model } from '~/types/api'

const { t } = useI18n()

// Page metadata
definePageMeta({
  breadcrumb: 'admin.pages.knowledgeBases.breadcrumb',
  layout: 'admin'
})

const router = useRouter()

// State
const activeTab = ref('knowledge-bases')

// Get embedding model list
const { data: models } = useAPI<Model[]>('/v1/admin/all-models?capabilities=embedding', { server: false })
const embeddingModelOptions = computed(() =>
  (models.value ?? []).map(m => ({ label: m.display_name, value: m.id }))
)
const modelMap = computed(() => {
  const map: Record<string, Model> = {}
  ;(models.value ?? []).forEach(m => { map[m.id] = m })
  return map
})

// Knowledge base configuration
const knowledgeBaseConfig = computed((): ModelViewConfig<KnowledgeBase> => ({
  title: t('admin.pages.knowledgeBases.title'),
  description: t('admin.pages.knowledgeBases.description'),
  apiEndpoint: '/v1/admin/rag/knowledge-bases',
  columns: [
    {
      accessorKey: 'name',
      header: t('admin.pages.knowledgeBases.columns.name'),
      cell: (context) => {
        const row = context.row.original
        return h(NuxtLink, {
          to: `/admin/kbs/${row.id}`,
          class: 'font-medium text-primary underline underline-offset-4'
        }, () => row.name)
      }
    },
    {
      accessorKey: 'description',
      header: t('common.description')
    },
    {
      accessorKey: 'created_at',
      header: t('admin.pages.knowledgeBases.columns.createdAt'),
      cell: (context) => {
        const date = new Date(context.getValue() as string)
        return date.toLocaleString()
      }
    }
  ],
  detailFields: [
    {
      name: 'id',
      label: t('common.id'),
      type: 'text'
    },
    {
      name: 'name',
      label: t('admin.pages.knowledgeBases.detailFields.name'),
      type: 'text'
    },
    {
      name: 'description',
      label: t('common.description'),
      type: 'textarea'
    },
    {
      name: 'embedding_model_id',
      label: t('admin.pages.knowledgeBases.detailFields.embeddingModel'),
      type: 'text',
      render: (val: string) => val ? (modelMap.value[val]?.display_name || val) : t('admin.pages.knowledgeBases.notSet')
    },
    {
      name: 'chunk_size',
      label: t('admin.pages.knowledgeBases.detailFields.chunkSize'),
      type: 'text',
      render: (val: number) => val ? t('admin.pages.knowledgeBases.charactersCount', { count: val }) : t('admin.pages.knowledgeBases.useDefault')
    },
    {
      name: 'chunk_overlap',
      label: t('admin.pages.knowledgeBases.detailFields.chunkOverlap'),
      type: 'text',
      render: (val: number) => val ? t('admin.pages.knowledgeBases.charactersCount', { count: val }) : t('admin.pages.knowledgeBases.useDefault')
    },
    {
      name: 'created_at',
      label: t('admin.pages.knowledgeBases.columns.createdAt'),
      type: 'datetime'
    },
    {
      name: 'updated_at',
      label: t('admin.pages.knowledgeBases.columns.updatedAt'),
      type: 'datetime'
    }
  ],
  formFields: [
    {
      name: 'name',
      label: t('admin.pages.knowledgeBases.formFields.name'),
      type: 'text',
      required: true,
      placeholder: t('admin.pages.knowledgeBases.formFields.namePlaceholder')
    },
    {
      name: 'description',
      label: t('common.description'),
      type: 'textarea',
      placeholder: t('admin.pages.knowledgeBases.formFields.descriptionPlaceholder')
    },
    {
      name: 'embedding_model_id',
      label: t('admin.pages.knowledgeBases.formFields.embeddingModel'),
      type: 'select',
      required: true,
      options: embeddingModelOptions.value,
      placeholder: t('admin.pages.knowledgeBases.formFields.embeddingModelPlaceholder')
    },
    {
      name: 'chunk_size',
      label: t('admin.pages.knowledgeBases.formFields.chunkSize'),
      type: 'number',
      required: true,
      placeholder: t('admin.pages.knowledgeBases.formFields.chunkSizePlaceholder'),
      help: t('admin.pages.knowledgeBases.formFields.chunkSizeHelp')
    },
    {
      name: 'chunk_overlap',
      label: t('admin.pages.knowledgeBases.formFields.chunkOverlap'),
      type: 'number',
      required: true,
      placeholder: t('admin.pages.knowledgeBases.formFields.chunkOverlapPlaceholder'),
      help: t('admin.pages.knowledgeBases.formFields.chunkOverlapHelp')
    }
  ],
  customActions: [
    {
      key: 'view-documents',
      label: t('admin.pages.knowledgeBases.viewDocuments'),
      icon: FileText,
      variant: 'default'
    }
  ],
  canCreate: true,
  canEdit: true,
  canDelete: true,
  canView: true,
  showFilters: true,
  emptyMessage: t('admin.pages.knowledgeBases.emptyMessage'),
  pageSize: 20
}))

// Handle row actions
const handleKnowledgeBaseAction = (action: any, row: KnowledgeBase) => {
  if (action.key === 'view-documents') {
    // Navigate to document management page
    router.push(`/admin/kbs/${row.id}`)
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Knowledge Base Management -->
    <ModelView
      :config="knowledgeBaseConfig"
      @row-action="handleKnowledgeBaseAction"
    />
  </div>
</template>