<script setup lang="ts">
import { ref, onMounted } from "vue"
import { v4 as uuidv4 } from "uuid"
import { toast } from "vue-sonner"
import { useClipboard } from "@vueuse/core"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { MoreVertical, Copy, Trash, Edit, RefreshCw } from "lucide-vue-next"
import { useChannels, type Channel, ChannelProvider } from "~/composables/useChannels"
import ChannelForm from "./ChannelForm.vue"

const props = defineProps<{
  assistantId: string
}>()

const { t } = useI18n()
const { listChannels, deleteChannel } = useChannels()
const { copy } = useClipboard()

const channels = ref<Channel[]>([])
const loading = ref(true)
const isFormOpen = ref(false)
const selectedChannel = ref<Channel | null>(null)

// Computed API Base for Webhooks
const getWebhookUrl = (channelId: string) => {
    // We assume the frontend knows the API base URL, or better, we construct it from window location if API is proxied
    // If we have a runtime config publicUrl, use it.
    const config = useRuntimeConfig()
    // Fallback logic
    const baseUrl = typeof window !== "undefined" ? window.location.origin : "https://your-domain.com"
    return `${baseUrl}/api/v1/channels/webhook/${channelId}`
}

const fetchChannels = async () => {
    loading.value = true
    try {
        channels.value = await listChannels(props.assistantId)
    } catch (e) {
        console.error(e)
    } finally {
        loading.value = false
    }
}

const handleEdit = (channel: Channel) => {
    selectedChannel.value = channel
    isFormOpen.value = true
}

const handleDelete = async (id: string) => {
    if (!confirm(t('assistants.channels.delete_confirm'))) return
    try {
        await deleteChannel(id)
        toast.success(t('assistants.channels.delete_success'))
        await fetchChannels()
    } catch (e) {
        toast.error(t('assistants.channels.delete_failed'))
    }
}

const handleCreate = () => {
    selectedChannel.value = null
    isFormOpen.value = true
}

const onFormSuccess = () => {
    fetchChannels()
}

// Copy helper
const copyWebhook = (id: string) => {
    const url = getWebhookUrl(id)
    copy(url)
    toast.success(t('assistants.channels.webhook_copied'))
}

onMounted(() => {
    fetchChannels()
})
</script>

<template>
<div class="space-y-6">
    <div class="flex justify-between items-center">
        <div>
            <h3 class="text-lg font-medium">{{ t('assistants.channels.list_title') }}</h3>
            <p class="text-sm text-muted-foreground">
                {{ t('assistants.channels.list_description') }}
            </p>
        </div>
        <Button @click="handleCreate">{{ t('assistants.channels.add') }}</Button>
    </div>

    <div v-if="loading" class="text-center py-8">{{ t('assistants.channels.loading') }}</div>

    <div v-else-if="channels.length === 0" class="text-center py-8 border border-dashed rounded-lg bg-slate-50 dark:bg-slate-900/50">
        <p class="text-muted-foreground mb-4">{{ t('assistants.channels.empty') }}</p>
        <Button variant="outline" @click="handleCreate">{{ t('assistants.channels.connect_btn') }}</Button>
    </div>

    <div v-else class="grid gap-4 md:grid-cols-2">
        <Card v-for="channel in channels" :key="channel.id">
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle class="text-sm font-medium">
                    {{ channel.name }}
                </CardTitle>
                <div class="flex items-center gap-2">
                    <Badge :variant="channel.is_active ? 'default' : 'secondary'">
                        {{ channel.is_active ? t('common.active') : t('common.disabled') }}
                    </Badge>
                     <DropdownMenu>
                        <DropdownMenuTrigger as-child>
                        <Button variant="ghost" size="icon" class="-mr-2 h-8 w-8">
                            <MoreVertical class="w-4 h-4" />
                        </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                        <DropdownMenuItem @click="handleEdit(channel)">
                            <Edit class="w-4 h-4 mr-2" /> {{ t('common.edit') }}
                        </DropdownMenuItem>
                        <DropdownMenuItem class="text-destructive" @click="handleDelete(channel.id)">
                            <Trash class="w-4 h-4 mr-2" /> {{ t('common.delete') }}
                        </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
            </CardHeader>
            <CardContent>
                <div class="text-2xl font-bold flex items-center gap-2 mb-2">
                    <span v-if="channel.provider === 'telegram'" class="i-logos-telegram w-6 h-6"></span>
                    <span v-else-if="channel.provider === 'wecom'" class="i-simple-icons-wechat w-6 h-6 text-green-600"></span>
                    {{ channel.provider.toUpperCase() }}
                </div>
                
                <div class="mt-4 space-y-2">
                    <div class="text-xs text-muted-foreground font-mono bg-slate-100 dark:bg-slate-800 p-2 rounded break-all">
                        {{ getWebhookUrl(channel.id) }}
                    </div>
                     <Button variant="ghost" size="sm" class="w-full" @click="copyWebhook(channel.id)">
                        <Copy class="w-3 h-3 mr-2" /> {{ t('assistants.channels.copy_webhook') }}
                    </Button>
                </div>
            </CardContent>
        </Card>
    </div>

    <ChannelForm 
        v-model:open="isFormOpen"
        :assistant-id="assistantId"
        :channel-to-edit="selectedChannel"
        @success="onFormSuccess"
    />
</div>
</template>
