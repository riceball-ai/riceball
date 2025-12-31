<script setup lang="ts">
import { computed, h } from 'vue'
import { Badge } from '~/components/ui/badge'
import type { ModelViewConfig } from '~/components/model-view/types'
import { Eye, Star, Shield } from 'lucide-vue-next'

const { t } = useI18n()

definePageMeta({
  breadcrumb: 'admin.pages.oauthProviders.breadcrumb',
  layout: 'admin'
})

// Scope options
const commonScopes = [
  { label: 'openid', value: 'openid' },
  { label: 'email', value: 'email' },
  { label: 'profile', value: 'profile' },
  { label: 'user:email', value: 'user:email' },
  { label: 'read:user', value: 'read:user' },
  { label: 'repo', value: 'repo' },
  { label: 'public_repo', value: 'public_repo' }
]

// User field mapping options
const userMappingOptions = computed(() => [
  { label: t('admin.pages.oauthProviders.userMapping.userId'), value: 'id' },
  { label: t('admin.pages.oauthProviders.userMapping.email'), value: 'email' },
  { label: t('admin.pages.oauthProviders.userMapping.name'), value: 'name' },
  { label: t('admin.pages.oauthProviders.userMapping.avatar'), value: 'avatar' },
  { label: t('admin.pages.oauthProviders.userMapping.username'), value: 'username' },
  { label: t('admin.pages.oauthProviders.userMapping.nickname'), value: 'nickname' }
])

// OAuth provider configuration
const oauthConfig = computed((): ModelViewConfig<OAuthProvider> => ({
  title: t('admin.pages.oauthProviders.title'),
  description: t('admin.pages.oauthProviders.description'),
  apiEndpoint: '/v1/admin/oauth-providers',
  
  columns: [
    {
      accessorKey: 'display_name',
      header: t('admin.pages.oauthProviders.columns.name'),
      cell: (ctx) => {
        const provider = ctx.row.original
        return h('div', { class: 'flex items-center gap-2' }, [
          provider.icon_url && h('img', { 
            src: provider.icon_url, 
            alt: provider.display_name,
            class: 'w-5 h-5 rounded'
          }),
          h('span', provider.display_name)
        ])
      }
    },
    {
      accessorKey: 'name',
      header: t('admin.pages.oauthProviders.columns.providerId')
    },
    {
      accessorKey: 'is_active',
      header: t('admin.pages.oauthProviders.columns.isActive'),
      cell: (ctx) => {
        const isActive = ctx.getValue() as boolean
        return h(Badge, { 
          variant: isActive ? 'default' : 'secondary',
          class: 'flex items-center gap-1'
        }, () => [
          h(isActive ? Shield : Eye, { class: 'w-3 h-3' }),
          isActive ? t('common.yes') : t('common.no')
        ])
      }
    },
    {
      accessorKey: 'scopes',
      header: t('admin.pages.oauthProviders.columns.scopes'),
      cell: (ctx) => {
        const scopes = ctx.getValue() as string[] || []
        if (scopes.length === 0) return '-'
        
        return h('div', { class: 'flex flex-wrap gap-1' }, 
          scopes.slice(0, 3).map(scope => 
            h(Badge, { 
              key: scope, 
              variant: 'outline',
              class: 'text-xs'
            }, () => scope)
          ).concat(
            scopes.length > 3 ? 
            [h('span', { class: 'text-xs text-muted-foreground' }, `+${scopes.length - 3}`)] : 
            []
          )
        )
      }
    },
    {
      accessorKey: 'sort_order',
      header: t('admin.pages.oauthProviders.columns.sortOrder'),
      cell: (ctx) => {
        const order = ctx.getValue() as number
        return h('div', { class: 'flex items-center gap-1' }, [
          h(Star, { class: 'w-3 h-3 text-yellow-500' }),
          h('span', order.toString())
        ])
      }
    },
    {
      accessorKey: 'created_at',
      header: t('admin.pages.oauthProviders.columns.createdAt'),
      cell: (ctx) => {
        const value = ctx.getValue() as string
        return new Date(value).toLocaleDateString()
      }
    }
  ],

  detailFields: [
    {
      name: 'name',
      label: t('admin.pages.oauthProviders.detailFields.providerId'),
      type: 'text'
    },
    {
      name: 'display_name',
      label: t('admin.pages.oauthProviders.detailFields.name'),
      type: 'text'
    },
    {
      name: 'description',
      label: t('common.description'),
      type: 'textarea'
    },
    {
      name: 'client_id',
      label: t('admin.pages.oauthProviders.detailFields.clientId'),
      type: 'text'
    },
    {
      name: 'auth_url',
      label: t('admin.pages.oauthProviders.detailFields.authorizationUrl'),
      type: 'text'
    },
    {
      name: 'token_url',
      label: t('admin.pages.oauthProviders.detailFields.tokenUrl'),
      type: 'text'
    },
    {
      name: 'user_info_url',
      label: t('admin.pages.oauthProviders.detailFields.userInfoUrl'),
      type: 'text'
    },
    {
      name: 'scopes',
      label: t('admin.pages.oauthProviders.detailFields.scopes'),
      type: 'text',
      render: (val: string[]) => {
        if (!val || val.length === 0) return t('common.noData')
        return val.join(', ')
      }
    },
    {
      name: 'user_mapping',
      label: t('admin.pages.oauthProviders.detailFields.userMapping'),
      type: 'json'
    },
    {
      name: 'icon_url',
      label: t('admin.pages.oauthProviders.detailFields.iconUrl'),
      type: 'text'
    },
    {
      name: 'sort_order',
      label: t('admin.pages.oauthProviders.detailFields.sortOrder'),
      type: 'text'
    },
    {
      name: 'is_active',
      label: t('admin.pages.oauthProviders.detailFields.isActive'),
      type: 'boolean'
    },
    {
      name: 'created_at',
      label: t('admin.pages.oauthProviders.columns.createdAt'),
      type: 'datetime'
    }
  ],

  formFields: [
    {
      name: 'name',
      label: t('admin.pages.oauthProviders.formFields.providerId'),
      type: 'text',
      required: true,
      placeholder: t('admin.pages.oauthProviders.formFields.providerIdPlaceholder'),
      help: t('admin.pages.oauthProviders.formFields.providerIdHelp')
    },
    {
      name: 'display_name',
      label: t('admin.pages.oauthProviders.formFields.name'),
      type: 'text',
      required: true,
      placeholder: t('admin.pages.oauthProviders.formFields.namePlaceholder'),
      help: t('admin.pages.oauthProviders.formFields.nameHelp')
    },
    {
      name: 'description',
      label: t('common.description'),
      type: 'textarea',
      placeholder: t('admin.pages.oauthProviders.formFields.providerIdPlaceholder'),
      help: t('admin.pages.oauthProviders.formFields.providerIdHelp')
    },
    {
      name: 'client_id',
      label: t('admin.pages.oauthProviders.formFields.clientId'),
      type: 'text',
      required: true,
      placeholder: t('admin.pages.oauthProviders.formFields.clientIdPlaceholder'),
      help: t('admin.pages.oauthProviders.formFields.clientIdHelp')
    },
    {
      name: 'client_secret',
      label: t('admin.pages.oauthProviders.formFields.clientSecret'),
      type: 'password',
      required: false,
      placeholder: t('admin.pages.oauthProviders.formFields.clientSecretPlaceholder'),
      help: t('admin.pages.oauthProviders.formFields.clientSecretHelp')
    },
    {
      name: 'auth_url',
      label: t('admin.pages.oauthProviders.formFields.authorizationUrl'),
      type: 'text',
      required: true,
      placeholder: t('admin.pages.oauthProviders.formFields.authorizationUrlPlaceholder'),
      help: t('admin.pages.oauthProviders.formFields.authorizationUrlHelp')
    },
    {
      name: 'token_url',
      label: t('admin.pages.oauthProviders.formFields.tokenUrl'),
      type: 'text',
      required: true,
      placeholder: t('admin.pages.oauthProviders.formFields.tokenUrlPlaceholder'),
      help: t('admin.pages.oauthProviders.formFields.tokenUrlHelp')
    },
    {
      name: 'user_info_url',
      label: t('admin.pages.oauthProviders.formFields.userInfoUrl'),
      type: 'text',
      required: true,
      placeholder: t('admin.pages.oauthProviders.formFields.userInfoUrlPlaceholder'),
      help: t('admin.pages.oauthProviders.formFields.userInfoUrlHelp')
    },
    {
      name: 'scopes',
      label: t('admin.pages.oauthProviders.formFields.scopes'),
      type: 'multiselect',
      required: true,
      options: commonScopes,
      placeholder: t('admin.pages.oauthProviders.formFields.scopesPlaceholder'),
      help: t('admin.pages.oauthProviders.formFields.scopesHelp')
    },
    {
      name: 'user_mapping',
      label: t('admin.pages.oauthProviders.formFields.userMapping'),
      type: 'json',
      placeholder: t('admin.pages.oauthProviders.formFields.userMappingPlaceholder'),
      help: t('admin.pages.oauthProviders.formFields.userMappingHelp'),
      defaultValue: {
        id: 'id',
        email: 'email', 
        name: 'name',
        avatar: 'avatar_url'
      }
    },
    {
      name: 'icon_url',
      label: t('admin.pages.oauthProviders.formFields.iconUrl'),
      type: 'text',
      placeholder: t('admin.pages.oauthProviders.formFields.iconUrlPlaceholder'),
      help: t('admin.pages.oauthProviders.formFields.iconUrlHelp')
    },
    {
      name: 'sort_order',
      label: t('admin.pages.oauthProviders.formFields.sortOrder'),
      type: 'number',
      placeholder: t('admin.pages.oauthProviders.formFields.sortOrderPlaceholder'),
      defaultValue: 0,
      help: t('admin.pages.oauthProviders.formFields.sortOrderHelp')
    },
    {
      name: 'is_active',
      label: t('admin.pages.oauthProviders.formFields.isActive'),
      type: 'switch',
      defaultValue: true,
      help: t('admin.pages.oauthProviders.formFields.isActiveHelp')
    }
  ]
}))
</script>

<template>
  <ModelView :config="oauthConfig" />
</template>