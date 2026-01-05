<script setup lang="ts">
import AssistantAvatar from '~/components/AssistantAvatar.vue'
import { Button } from '~/components/ui/button'
import { Loader2 } from 'lucide-vue-next'
import { useLocalizedAssistant } from '~/composables/useLocalized'
import type { Assistant, ConversationSharePublicResponse } from '~/types/api'

const route = useRoute()
const shareId = computed(() => route.params.id as string)
const { t } = useI18n()
const configStore = useConfigStore()
const runtimeConfig = useRuntimeConfig()

const siteName = computed(() => configStore.config.site_title || runtimeConfig.public.appName)

const { data, pending, error, refresh } = await useAPI<ConversationSharePublicResponse>(
  () => `/v1/share-links/${shareId.value}`
)

const shareData = computed(() => data.value)

const messages = computed(() => shareData.value?.messages ?? [])
const rawAssistant = computed(() => shareData.value?.assistant ?? null)
const localizedAssistant = useLocalizedAssistant(rawAssistant)
const assistantName = computed(() => localizedAssistant.value?.name ?? shareData.value?.assistant_name ?? '')
const assistantDescription = computed(() => localizedAssistant.value?.description ?? shareData.value?.assistant_description ?? '')
const assistantId = computed(() => localizedAssistant.value?.id ?? shareData.value?.assistant_id ?? null)
const assistantAvatarData = computed<Partial<Assistant> | null>(() => {
  const localized = localizedAssistant.value as Partial<Assistant> | null
  if (localized) {
    return {
      ...localized,
      avatar_url: localized.avatar_url || shareData.value?.assistant?.avatar_url || undefined
    }
  }
  if (assistantName.value) {
    return {
      name: assistantName.value,
      avatar_url: shareData.value?.assistant?.avatar_url || undefined
    }
  }
  return null
})
const conversationTitle = computed(() => shareData.value?.conversation_title ?? '')

const assistantReplyPreview = computed(() => {
  const assistantMsg = messages.value.find(msg => msg.message_type === 'ASSISTANT')
  if (!assistantMsg) return ''
  return assistantMsg.content.slice(0, 160)
})

const pageTitle = computed(() => {
  if (conversationTitle.value) {
    return t('share.metaTitle', { title: conversationTitle.value })
  }
  return t('share.defaultTitle')
})

useHead(() => ({
  title: pageTitle.value,
  meta: assistantReplyPreview.value
    ? [
        {
          name: 'description',
          content: assistantReplyPreview.value
        }
      ]
    : []
}))

const goToAssistantChat = () => {
  if (!assistantId.value) return
  navigateTo(`/chatwith/${assistantId.value}`)
}
</script>

<template>
  <div class="min-h-screen bg-background text-foreground">
    <div class="max-w-3xl mx-auto py-10 px-4 space-y-8">
      <header class="space-y-4">
        <div class="text-center space-y-2">
          <p class="text-sm text-muted-foreground uppercase tracking-wide">{{ t('share.tagline', { siteName }) }}</p>
          <h1 class="text-2xl font-semibold">
            {{ conversationTitle || t('share.defaultTitle') }}
          </h1>
        </div>

        <div
          v-if="shareData && assistantName"
          class="border border-border rounded-xl p-4 flex flex-col gap-4 md:flex-row md:items-center md:justify-between bg-card/40"
        >
          <div class="flex items-center gap-3">
            <AssistantAvatar :assistant="assistantAvatarData" class="size-12" />
            <div>
              <p class="text-lg font-medium">{{ assistantName }}</p>
              <p class="text-sm text-muted-foreground" v-if="assistantDescription">
                {{ assistantDescription }}
              </p>
            </div>
          </div>
          <div class="flex gap-2">
            <Button
              v-if="assistantId"
              size="sm"
              class="w-full md:w-auto"
              @click="goToAssistantChat"
            >
              {{ t('share.chatWithAssistant') }}
            </Button>
          </div>
        </div>
      </header>

      <section v-if="pending" class="flex flex-col items-center gap-2 py-10 text-muted-foreground">
        <Loader2 class="w-6 h-6 animate-spin" />
        <span>{{ t('share.loading') }}</span>
      </section>

      <section v-else-if="error" class="text-center space-y-3">
        <p class="text-lg font-semibold">{{ t('share.notFoundTitle') }}</p>
        <p class="text-muted-foreground text-sm">{{ t('share.notFoundDescription') }}</p>
        <Button variant="outline" @click="refresh">{{ t('common.retry') }}</Button>
      </section>

      <section v-else>
        <div class="space-y-4">
          <ChatMessage
            v-for="message in messages"
            :key="message.id"
            :message="message"
            :enable-share="false"
            :force-completed="true"
          />
        </div>
      </section>
    </div>
  </div>
</template>
