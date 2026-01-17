<script setup lang="ts">
import { computed, h } from 'vue'
import { Badge } from '~/components/ui/badge'
import type { ModelViewConfig } from '~/components/model-view/types'
import type { Provider } from '~/types/api'

const { t } = useI18n()

definePageMeta({
  breadcrumb: 'admin.pages.modelProviders.breadcrumb',
  layout: 'admin'
})

// Provider configuration
const providerConfig = computed((): ModelViewConfig<Provider> => ({
  title: t('admin.pages.modelProviders.title'),
  description: t('admin.pages.modelProviders.description'),
  apiEndpoint: '/v1/admin/providers',
  
  columns: [
    {
      accessorKey: 'display_name',
      header: t('admin.pages.modelProviders.columns.displayName')
    },
    {
      accessorKey: 'api_base_url',
      header: t('admin.pages.modelProviders.fields.apiBaseUrl'),
      cell: (context) => {
        const value = context.getValue() as string
        return value.length > 30 ? value.substring(0, 30) + '...' : value
      }
    },
    {
      accessorKey: 'status',
      header: t('admin.pages.modelProviders.columns.status'),
      cell: (context) => {
        const value = context.getValue() as string
        // Based on status
        const variant = value === 'ACTIVE' ? 'default' : value === 'MAINTENANCE' ? 'outline' : 'secondary'
        const statusKey = value === 'ACTIVE' ? 'active' : value === 'MAINTENANCE' ? 'maintenance' : 'inactive'
        return h(Badge, { variant }, () => t(`admin.pages.modelProviders.status.${statusKey}`))
      }
    },
    {
      accessorKey: 'created_at',
      header: t('admin.pages.modelProviders.columns.createdAt'),
      cell: (context) => {
        const value = context.getValue() as string
        return new Date(value).toLocaleDateString()
      }
    },
  ],

  detailFields: [
    {
      name: 'display_name',
      label: t('admin.pages.modelProviders.fields.displayName'),
      type: 'text'
    },
    {
      name: 'description',
      label: t('admin.pages.modelProviders.fields.description'),
      type: 'textarea'
    },
    {
      name: 'website',
      label: t('admin.pages.modelProviders.fields.website'),
      type: 'text'
    },
    {
      name: 'api_base_url',
      label: t('admin.pages.modelProviders.fields.apiBaseUrl'),
      type: 'text'
    },
    {
      name: 'interface_type',
      label: t('admin.pages.modelProviders.fields.interfaceType'),
      type: 'text'
    },
    {
      name: 'status',
      label: t('admin.pages.modelProviders.fields.statusLabel'),
      type: 'text'
    },
    {
      name: 'created_at',
      label: t('admin.pages.modelProviders.columns.createdAt'),
      type: 'datetime'
    }
  ],

  formFields: [
    {
      name: 'display_name',
      label: t('admin.pages.modelProviders.fields.displayName'),
      type: 'text',
      required: true,
      placeholder: t('admin.pages.modelProviders.fields.displayNamePlaceholder')
    },
    {
      name: 'description',
      label: t('admin.pages.modelProviders.fields.description'),
      type: 'textarea',
      placeholder: t('admin.pages.modelProviders.fields.descriptionPlaceholder')
    },
    {
      name: 'website',
      label: t('admin.pages.modelProviders.fields.website'),
      type: 'text',
      placeholder: 'https://example.com'
    },
    {
      name: 'api_base_url',
      label: t('admin.pages.modelProviders.fields.apiBaseUrl'),
      type: 'text',
      placeholder: 'https://api.example.com/v1'
    },
    {
      name: 'api_key',
      label: t('admin.pages.modelProviders.fields.apiKey'),
      type: 'text',
      required: false,
      placeholder: t('admin.pages.modelProviders.fields.apiKeyPlaceholder')
    },
    {
      name: 'interface_type',
      label: t('admin.pages.modelProviders.fields.interfaceType'),
      type: 'select',
      required: true,
      options: [
        { label: 'Anthropic', value: 'ANTHROPIC' },
        { label: 'DashScope', value: 'DASHSCOPE' },
        { label: 'Google', value: 'GOOGLE' },
        { label: 'Ollama', value: 'OLLAMA' },
        { label: 'OpenAI', value: 'OPENAI' },
        { label: 'xAI', value: 'XAI' },
      ],
      defaultValue: 'OPENAI'
    },
    {
      name: 'status',
      label: t('admin.pages.modelProviders.fields.statusLabel'),
      type: 'select',
      required: true,
      options: [
        { label: t('admin.pages.modelProviders.status.active'), value: 'ACTIVE' },
        { label: t('admin.pages.modelProviders.status.inactive'), value: 'INACTIVE' },
        { label: t('admin.pages.modelProviders.status.maintenance'), value: 'MAINTENANCE' }
      ],
      defaultValue: 'ACTIVE'
    }
  ],

}))

</script>

<template>
  <ModelView :config="providerConfig" />
</template>
