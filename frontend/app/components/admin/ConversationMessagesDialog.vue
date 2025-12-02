<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '~/components/ui/dialog'
import { Badge } from '~/components/ui/badge'
import { Loader2, User, Bot } from 'lucide-vue-next'

const { t } = useI18n()

interface Message {
  id: string
  content: string
  message_type: string
  created_at: string
  user_id?: string
  input_tokens?: number
  output_tokens?: number
  total_tokens?: number
  extra_data?: Record<string, any>
}

interface Props {
  open: boolean
  conversationId: string | null
  conversationTitle: string
  inputTokens?: number
  outputTokens?: number
  totalTokens?: number
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:open': [value: boolean]
}>()

const messages = ref<Message[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

const localOpen = computed({
  get: () => props.open,
  set: (value) => emit('update:open', value)
})

// Fetch message list
const fetchMessages = async () => {
  if (!props.conversationId) return
  
  loading.value = true
  error.value = null
  
  try {
    const response = await $fetch<{ items: Message[] }>(
      `/api/v1/admin/conversations/${props.conversationId}/messages`,
      {
        params: { page: 1, size: 100 }
      }
    )
    messages.value = response.items || []
  } catch (err: any) {
    error.value = err.message || t('components.conversationMessages.loadMessagesFailed')
    messages.value = []
  } finally {
    loading.value = false
  }
}

// Watch dialog open state
watch(() => props.open, (newVal) => {
  if (newVal && props.conversationId) {
    fetchMessages()
  }
})

// Format time
const formatTime = (dateString: string) => {
  return new Date(dateString).toLocaleString('zh-CN')
}

// Get message type label
const getMessageTypeLabel = (type: string) => {
  const typeKey = type.toLowerCase()
  return t(`components.conversationMessages.messageTypes.${typeKey}`, type)
}

const getMessageTypeVariant = (type: string) => {
  const variants: Record<string, 'default' | 'secondary' | 'outline'> = {
    'USER': 'default',
    'ASSISTANT': 'secondary',
    'SYSTEM': 'outline'
  }
  return variants[type] || 'default'
}

// Use statistics passed from parent component (from conversation object)
const totalStats = computed(() => {
  return {
    inputTokens: props.inputTokens || 0,
    outputTokens: props.outputTokens || 0,
    totalTokens: props.totalTokens || 0,
  }
})
</script>

<template>
  <Dialog v-model:open="localOpen">
    <DialogContent class="max-w-4xl max-h-[85vh] flex flex-col">
      <DialogHeader>
        <DialogTitle>{{ t('components.conversationMessages.title') }}</DialogTitle>
        <DialogDescription class="space-y-2">
          <div>{{ conversationTitle }} - {{ t('components.conversationMessages.totalMessages', { count: messages.length }) }}</div>
          <div v-if="totalStats.totalTokens > 0" class="flex gap-4 text-xs">
            <span class="text-muted-foreground">
              {{ t('components.conversationMessages.totalTokens') }}: <span class="font-medium text-foreground">{{ totalStats.totalTokens.toLocaleString() }}</span>
            </span>
            <span class="text-muted-foreground">
              {{ t('components.conversationMessages.inputTokens') }}: <span class="font-medium text-foreground">{{ totalStats.inputTokens.toLocaleString() }}</span>
            </span>
            <span class="text-muted-foreground">
              {{ t('components.conversationMessages.outputTokens') }}: <span class="font-medium text-foreground">{{ totalStats.outputTokens.toLocaleString() }}</span>
            </span>
          </div>
        </DialogDescription>
      </DialogHeader>

      <div class="flex-1 overflow-y-auto min-h-0">
        <div v-if="loading" class="flex items-center justify-center py-12">
          <Loader2 class="h-8 w-8 animate-spin text-muted-foreground" />
        </div>

        <div v-else-if="error" class="flex items-center justify-center py-12 text-destructive">
          {{ error }}
        </div>

        <div v-else class="pr-4">
          <div class="space-y-4">
            <div
              v-for="message in messages"
              :key="message.id"
              class="rounded-lg border p-4"
              :class="{
                'bg-muted/50': message.message_type === 'ASSISTANT',
                'bg-background': message.message_type === 'USER'
              }"
            >
              <div class="flex items-start gap-3">
                <div class="flex-shrink-0 mt-1">
                  <div 
                    class="h-8 w-8 rounded-full flex items-center justify-center"
                    :class="{
                      'bg-primary text-primary-foreground': message.message_type === 'USER',
                      'bg-secondary text-secondary-foreground': message.message_type === 'ASSISTANT'
                    }"
                  >
                    <User v-if="message.message_type === 'USER'" class="h-4 w-4" />
                    <Bot v-else class="h-4 w-4" />
                  </div>
                </div>

                <div class="flex-1 space-y-2">
                  <div class="flex items-center gap-2">
                    <Badge :variant="getMessageTypeVariant(message.message_type)">
                      {{ getMessageTypeLabel(message.message_type) }}
                    </Badge>
                    <span class="text-xs text-muted-foreground">
                      {{ formatTime(message.created_at) }}
                    </span>
                  </div>

                  <div class="text-sm whitespace-pre-wrap break-words">
                    {{ message.content }}
                  </div>

                  <!-- Display metadata -->
                  <div class="flex flex-wrap gap-3 text-xs text-muted-foreground">
                    <span v-if="message.extra_data?.model">
                      {{ t('components.conversationMessages.model') }}: {{ message.extra_data.model }}
                    </span>
                    <span v-if="message.total_tokens">
                      {{ t('components.conversationMessages.tokens') }}: {{ message.total_tokens.toLocaleString() }}
                      <span v-if="message.input_tokens && message.output_tokens">
                        ({{ message.input_tokens.toLocaleString() }} + {{ message.output_tokens.toLocaleString() }})
                      </span>
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="messages.length === 0" class="text-center py-8 text-muted-foreground">
              {{ t('components.conversationMessages.noMessages') }}
            </div>
          </div>
        </div>
      </div>
    </DialogContent>
  </Dialog>
</template>
