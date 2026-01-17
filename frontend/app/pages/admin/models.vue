<script setup lang="ts">

import { computed, h } from 'vue'
import { Badge } from '~/components/ui/badge'
import OllamaScanner from '~/components/model-view/extra/OllamaScanner.vue'
import type { ModelViewConfig } from '~/components/model-view/types'
import type { Model, Provider } from '~/types/api'

const { t } = useI18n()

definePageMeta({
  breadcrumb: 'admin.pages.models.breadcrumb',
  layout: 'admin'
})

// Fetch provider list
const { data: providers } = useAPI<Provider[]>('/v1/admin/all-providers', { server: false })
const providerOptions = computed(() =>
  (providers.value ?? []).map(p => ({ label: p.display_name, value: p.id }))
)
const providerMap = computed(() => {
  const map: Record<string, Provider> = {}
  ;(providers.value ?? []).forEach(p => { map[p.id] = p })
  return map
})

// Model capability options
const capabilityOptions = computed(() => [
  { label: t('admin.pages.models.capabilities.chat'), value: 'chat' },
  { label: t('admin.pages.models.capabilities.completion'), value: 'completion' },
  { label: t('admin.pages.models.capabilities.embedding'), value: 'embedding' },
  { label: t('admin.pages.models.capabilities.vision'), value: 'vision' },
  { label: t('admin.pages.models.capabilities.audio'), value: 'audio' },
  { label: t('admin.pages.models.capabilities.function_calling'), value: 'function_calling' },
  { label: t('admin.pages.models.capabilities.tool_use'), value: 'tool_use' },
  { label: t('admin.pages.models.capabilities.code'), value: 'code' },
  { label: t('admin.pages.models.capabilities.image_generation'), value: 'image_generation' }
])

// Model configuration
const providerConfig = computed((): ModelViewConfig<Model> => ({
  title: t('admin.pages.models.title'),
  description: t('admin.pages.models.description'),
  apiEndpoint: '/v1/admin/models',
  
  columns: [
    {
      accessorKey: 'name',
      header: t('admin.pages.models.columns.modelName')
    },
    {
      accessorKey: 'display_name',
      header: t('admin.pages.models.columns.displayName')
    },
    {
      accessorKey: 'provider_id',
      header: t('admin.pages.models.columns.provider'),
      cell: (ctx) => {
        const id = ctx.getValue() as string
        const provider = providerMap.value[id]
        return provider ? provider.display_name : id
      }
    },
    {
      accessorKey: 'capabilities',
      header: t('admin.pages.models.columns.capabilities'),
      cell: (ctx) => {
        const capabilities = ctx.getValue() as string[] || []
        return h('div', { class: 'flex flex-wrap gap-1' }, 
          capabilities.map(cap => {
            const option = capabilityOptions.value.find(opt => opt.value === cap)
            return h(Badge, { 
              key: cap, 
              variant: 'secondary',
              class: 'text-xs'
            }, () => option?.label || cap)
          })
        )
      }
    },
    {
      accessorKey: 'created_at',
      header: t('admin.pages.models.columns.createdAt'),
      cell: (context) => {
        const value = context.getValue() as string
        return new Date(value).toLocaleDateString()
      }
    },
  ],

  detailFields: [
    {
      name: 'id',
      label: t('admin.pages.models.detailFields.id'),
      type: 'text'
    },
    {
      name: 'name',
      label: t('admin.pages.models.detailFields.modelName'),
      type: 'text'
    },
    {
      name: 'display_name',
      label: t('admin.pages.models.detailFields.displayName'),
      type: 'text'
    },
    {
      name: 'provider_id',
      label: t('admin.pages.models.detailFields.provider'),
      type: 'text',
      render: (val: string) => providerMap.value[val]?.display_name || val
    },
    {
      name: 'description',
      label: t('admin.pages.models.detailFields.description'),
      type: 'textarea'
    },
    {
      name: 'capabilities',
      label: t('admin.pages.models.detailFields.capabilities'),
      type: 'text',
      render: (val: string[]) => {
        if (!val || val.length === 0) return t('admin.pages.models.detailFields.capabilitiesNotSet')
        return val.map(cap => {
          const option = capabilityOptions.value.find(opt => opt.value === cap)
          return option?.label || cap
        }).join(', ')
      }
    },
    {
      name: 'generation_config',
      label: t('admin.pages.models.detailFields.generationConfig'),
      type: 'json'
    },
    {
      name: 'status',
      label: t('admin.pages.models.detailFields.status'),
      type: 'text'
    },
    {
      name: 'max_context_tokens',
      label: t('admin.pages.models.detailFields.maxContextTokens'),
      type: 'text',
      render: (val: number) => val ? val.toLocaleString() : t('admin.pages.models.detailFields.notSet')
    },
    {
      name: 'max_output_tokens',
      label: t('admin.pages.models.detailFields.maxOutputTokens'),
      type: 'text',
      render: (val: number) => val ? val.toLocaleString() : t('admin.pages.models.detailFields.notSet')
    },
    {
      name: 'created_at',
      label: t('admin.pages.models.detailFields.createdAt'),
      type: 'datetime'
    }
  ],

  formFields: [
    {
      name: 'name',
      label: t('admin.pages.models.formFields.modelName'),
      type: 'text',
      required: true,
      placeholder: t('admin.pages.models.formFields.modelNamePlaceholder')
    },
    {
      name: 'display_name',
      label: t('admin.pages.models.formFields.displayName'),
      type: 'text',
      required: true,
      placeholder: t('admin.pages.models.formFields.displayNamePlaceholder')
    },
    {
      name: 'provider_id',
      label: t('admin.pages.models.formFields.provider'),
      type: 'select',
      required: true,
      options: providerOptions.value,
      placeholder: t('admin.pages.models.formFields.providerPlaceholder')
    },
    {
      name: 'description',
      label: t('admin.pages.models.formFields.description'),
      type: 'textarea',
      placeholder: t('admin.pages.models.formFields.descriptionPlaceholder')
    },
    {
      name: 'capabilities',
      label: t('admin.pages.models.formFields.capabilities'),
      type: 'multiselect',
      required: true,
      options: capabilityOptions.value,
      placeholder: t('admin.pages.models.formFields.capabilitiesPlaceholder'),
      help: t('admin.pages.models.formFields.capabilitiesHelp')
    },
    {
      name: 'generation_config',
      label: t('admin.pages.models.formFields.generationConfig'),
      type: 'json',
      placeholder: t('admin.pages.models.formFields.generationConfigPlaceholder'),
      help: t('admin.pages.models.formFields.generationConfigHelp'),
      defaultValue: {}
    },
    {
      name: 'max_context_tokens',
      label: t('admin.pages.models.formFields.maxContextTokens'),
      type: 'number',
      placeholder: t('admin.pages.models.formFields.maxContextTokensPlaceholder'),
      help: t('admin.pages.models.formFields.maxContextTokensHelp')
    },
    {
      name: 'max_output_tokens',
      label: t('admin.pages.models.formFields.maxOutputTokens'),
      type: 'number',
      placeholder: t('admin.pages.models.formFields.maxOutputTokensPlaceholder'),
      help: t('admin.pages.models.formFields.maxOutputTokensHelp')
    },
    {
      name: 'status',
      label: t('admin.pages.models.formFields.status'),
      type: 'select',
      required: true,
      options: [
        { label: t('admin.pages.models.formFields.statusActive'), value: 'ACTIVE' },
        { label: t('admin.pages.models.formFields.statusInactive'), value: 'INACTIVE' },
        { label: t('admin.pages.models.formFields.statusUnavailable'), value: 'UNAVAILABLE' },
        { label: t('admin.pages.models.formFields.statusDeprecated'), value: 'DEPRECATED' },
      ],
      defaultValue: 'ACTIVE'
    }
  ],

}))

</script>

<template>
  <ModelView :config="providerConfig">
    <template #actions="{ refresh }">
        <OllamaScanner @scanned="refresh" />
    </template>
  </ModelView>
</template>
