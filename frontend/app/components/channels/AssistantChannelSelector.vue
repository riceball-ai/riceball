<script setup lang="ts">
import { ref, onMounted, computed } from "vue"
import { toast } from "vue-sonner"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Plus, Trash, Link as LinkIcon, ExternalLink } from "lucide-vue-next"
import { useChannels, type Channel } from "~/composables/useChannels"

const props = defineProps<{
  assistantId: string
}>()

const { t } = useI18n()
const { listChannels, updateChannel } = useChannels()
const { $api } = useNuxtApp()

const linkedChannels = ref<Channel[]>([])
const availableChannels = ref<Channel[]>([])
const loading = ref(true)
const isLinkDialogOpen = ref(false)
const selectedChannelId = ref<string>("")

const fetchLinkedChannels = async () => {
    loading.value = true
    try {
        linkedChannels.value = await listChannels(props.assistantId)
    } catch (e) {
        console.error(e)
    } finally {
        loading.value = false
    }
}

const fetchAvailableChannels = async () => {
    try {
        // Fetch all user channels
        const all = await $api<Channel[]>('/v1/channels')
        // Filter out those already linked to THIS assistant
        availableChannels.value = all.filter(c => c.assistant_id !== props.assistantId)
    } catch (e) {
        console.error(e)
        availableChannels.value = []
    }
}

const openLinkDialog = async () => {
    selectedChannelId.value = ""
    await fetchAvailableChannels()
    isLinkDialogOpen.value = true
}

const handleLink = async () => {
    if (!selectedChannelId.value) return
    
    try {
        await updateChannel(selectedChannelId.value, {
            assistant_id: props.assistantId
        })
        toast.success(t('common.success'))
        isLinkDialogOpen.value = false
        await fetchLinkedChannels()
    } catch (e) {
        toast.error(t('common.error'))
    }
}

const handleUnlink = async (channel: Channel) => {
    if (!confirm(t('common.confirmUnlink'))) return
    try {
        await updateChannel(channel.id, {
            assistant_id: null // Set to null to unlink
        })
        toast.success(t('common.success'))
        await fetchLinkedChannels()
    } catch (e) {
        toast.error(t('common.error'))
    }
}

onMounted(() => {
    fetchLinkedChannels()
})

// Helper for display
const getChannelLabel = (c: Channel) => {
    return `${c.name} (${c.provider})` + (c.assistant_id ? ` - [Bound]` : '')
}
</script>

<template>
<div class="space-y-4">
    <div class="flex justify-between items-center">
        <h3 class="text-lg font-medium">{{ t('assistants.channels.linked_title') }}</h3>
        <Button size="sm" variant="outline" @click="openLinkDialog">
            <LinkIcon class="w-4 h-4 mr-2" />
            {{ t('assistants.channels.link_existing') }}
        </Button>
    </div>

    <!-- Empty State -->
    <div v-if="!loading && linkedChannels.length === 0" class="text-center py-8 text-muted-foreground border rounded-lg border-dashed">
        {{ t('assistants.channels.no_linked') }}
    </div>

    <!-- Linked List -->
    <div v-else class="grid gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
        <Card v-for="channel in linkedChannels" :key="channel.id">
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle class="text-sm font-medium">
                    {{ channel.name }}
                </CardTitle>
                <Badge variant="outline">{{ channel.provider }}</Badge>
            </CardHeader>
            <CardContent>
                <div class="text-xs text-muted-foreground mb-4">
                   Created: {{ new Date(channel.created_at).toLocaleDateString() }}
                </div>
                <div class="flex justify-end gap-2">
                     <Button variant="ghost" size="icon" @click="handleUnlink(channel)" class="text-destructive hover:text-destructive">
                        <Trash class="w-4 h-4" />
                    </Button>
                </div>
            </CardContent>
        </Card>
    </div>

    <!-- Link Dialog -->
    <Dialog v-model:open="isLinkDialogOpen">
        <DialogContent>
            <DialogHeader>
                <DialogTitle>{{ t('assistants.channels.link_title') }}</DialogTitle>
                <DialogDescription>{{ t('assistants.channels.link_description') }}</DialogDescription>
            </DialogHeader>
            
            <div class="space-y-4 py-4">
                <div class="space-y-2">
                    <label class="text-sm font-medium">{{ t('assistants.channels.select_channel') }}</label>
                    <Select v-model="selectedChannelId">
                        <SelectTrigger>
                            <SelectValue :placeholder="t('assistants.channels.select_placeholder')" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem v-for="c in availableChannels" :key="c.id" :value="c.id">
                                {{ getChannelLabel(c) }}
                            </SelectItem>
                        </SelectContent>
                    </Select>
                </div>
            </div>

            <DialogFooter>
                <Button variant="outline" @click="isLinkDialogOpen = false">{{ t('common.cancel') }}</Button>
                <Button @click="handleLink" :disabled="!selectedChannelId">{{ t('common.save') }}</Button>
            </DialogFooter>
        </DialogContent>
    </Dialog>
</div>
</template>
