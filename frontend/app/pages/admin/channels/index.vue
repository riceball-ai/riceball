<script setup lang="ts">
import { ref } from 'vue'
import { Plus, Pencil, Trash2, Sliders, Smartphone, MessageSquare, Bot } from 'lucide-vue-next'
import { v4 as uuidv4 } from 'uuid'
import { toast } from 'vue-sonner'
import { Button } from '~/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '~/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '~/components/ui/dialog'
import { Badge } from '~/components/ui/badge'
import ChannelForm from '~/components/admin/channels/ChannelForm.vue'
import type { Channel } from '~/composables/useChannels'

definePageMeta({
  layout: 'admin',
  breadcrumb: 'channels.title'
})

const { t } = useI18n()
const { $api } = useNuxtApp()

// Fetch Data
const { data: channels, refresh: refreshChannels, status } = await useAPI<Channel[]>('/v1/channels')
const isLoading = computed(() => status.value === 'pending')

// State
const isDialogOpen = ref(false)
const selectedChannel = ref<Channel | null>(null)
const formLoading = ref(false)

// Actions
const openCreateDialog = () => {
    selectedChannel.value = null
    isDialogOpen.value = true
}

const openEditDialog = (channel: Channel) => {
    selectedChannel.value = channel
    isDialogOpen.value = true
}

const handleSubmit = async (data: Partial<Channel>) => {
    formLoading.value = true
    try {
        if (selectedChannel.value) {
            await $api(`/v1/channels/${selectedChannel.value.id}`, {
                method: 'PUT',
                body: data
            })
            toast.success(t('common.success'), { description: t('common.saveSuccess') })
        } else {
            await $api('/v1/channels', {
                method: 'POST',
                body: data
            })
            toast.success(t('common.success'), { description: t('common.createSuccess') })
        }
        isDialogOpen.value = false
        refreshChannels()
    } catch (e: any) {
        toast.error(t('common.error'), { description: e.message })
    } finally {
        formLoading.value = false
    }
}

const handleDelete = async (id: string) => {
    if (!confirm(t('channels.delete_confirm'))) return
    try {
        await $api(`/v1/channels/${id}`, { method: 'DELETE' })
        toast.success(t('common.success'), { description: t('channels.delete_success') })
        refreshChannels()
    } catch (e: any) {
        toast.error(t('common.error'), { description: e.message })
    }
}

const getProviderIcon = (provider: string) => {
    if (provider === 'telegram') return Smartphone
    if (provider === 'wecom') return MessageSquare
    if (provider === 'wecom_smart_bot') return Bot
    return Sliders
}

const getWebhookUrl = (channelId: string) => {
    const config = useRuntimeConfig()
    // Fallback logic
    const baseUrl = typeof window !== "undefined" ? window.location.origin : ""
    return `${baseUrl}/api/v1/channels/webhook/${channelId}`
}

const copyWebhook = (id: string, provider: string) => {
    const url = getWebhookUrl(id)
    navigator.clipboard.writeText(url)
    toast.success(t('channels.webhook_copied'))
}
</script>

<template>
  <div class="h-full flex-1 flex-col space-y-8 p-8 md:flex">
    <div class="flex items-center justify-between space-y-2">
      <div>
        <h2 class="text-2xl font-bold tracking-tight">{{ $t('channels.title') }}</h2>
        <p class="text-muted-foreground">{{ $t('channels.list_description') }}</p>
      </div>
      <div class="flex items-center space-x-2">
        <Button @click="openCreateDialog">
          <Plus class="mr-2 h-4 w-4" /> {{ $t('channels.add') }}
        </Button>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="!channels || channels.length === 0" class="flex h-[400px] shrink-0 items-center justify-center rounded-md border border-dashed">
      <div class="mx-auto flex max-w-[420px] flex-col items-center justify-center text-center">
        <div class="flex h-20 w-20 items-center justify-center rounded-full bg-muted">
          <Sliders class="h-10 w-10 text-muted-foreground" />
        </div>
        <h3 class="mt-4 text-lg font-semibold">{{ $t('channels.empty') }}</h3>
        <p class="mb-4 mt-2 text-sm text-muted-foreground">
          {{ $t('channels.list_description') }}
        </p>
        <Button size="sm" @click="openCreateDialog">
          <Plus class="mr-2 h-4 w-4" /> {{ $t('channels.add') }}
        </Button>
      </div>
    </div>

    <!-- Table -->
    <div v-else class="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead class="w-[300px]">{{ $t('channels.form.name') }}</TableHead>
            <TableHead>{{ $t('channels.form.platform') }}</TableHead>
            <TableHead>Webhook</TableHead>
            <TableHead>{{ $t('tasks.status') }}</TableHead>
            <TableHead class="text-right">{{ $t('common.actions') }}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="channel in channels" :key="channel.id">
            <TableCell class="font-medium">
               <div class="flex items-center gap-2">
                    <component :is="getProviderIcon(channel.provider)" class="h-4 w-4 text-muted-foreground" />
                    <span>{{ channel.name }}</span>
               </div>
            </TableCell>
            <TableCell class="capitalize">{{ channel.provider }}</TableCell>
            <TableCell>
                <code 
                    class="relative rounded bg-muted px-[0.3rem] py-[0.2rem] font-mono text-xs cursor-pointer hover:bg-muted/80"
                    title="Click to copy"
                    @click="copyWebhook(channel.id, channel.provider)"
                >
                    .../webhook/{{ channel.id }}
                </code>
            </TableCell>
            <TableCell>
                 <Badge :variant="channel.is_active ? 'default' : 'secondary'">
                    {{ channel.is_active ? $t('tasks.active') : $t('tasks.inactive') }}
                </Badge>
            </TableCell>
            <TableCell class="text-right">
                <Button variant="ghost" size="icon" @click="openEditDialog(channel)">
                    <Pencil class="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="icon" class="text-destructive" @click="handleDelete(channel.id)">
                    <Trash2 class="h-4 w-4" />
                </Button>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>

    <!-- Dialog -->
    <Dialog v-model:open="isDialogOpen">
        <DialogContent class="sm:max-w-[600px]">
            <DialogHeader>
                <DialogTitle>{{ selectedChannel ? $t('channels.form.edit_title') : $t('channels.form.add_title') }}</DialogTitle>
                <DialogDescription>{{ $t('channels.form.description') }}</DialogDescription>
            </DialogHeader>
            <ChannelForm 
                :key="selectedChannel ? selectedChannel.id : 'create'"
                :initial-data="selectedChannel"
                :loading="formLoading"
                @submit="handleSubmit"
            />
        </DialogContent>
    </Dialog>
  </div>
</template>
