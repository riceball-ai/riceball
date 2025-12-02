<script setup lang="ts">
import type { Assistant, Message } from '~/types/api'

const route = useRoute()
const assistantId = route.params.id as string

// Redirect to assistants page if no assistant is selected
if (!assistantId) {
  await navigateTo('/assistants')
}

// Chat state
const messages = ref<Message[]>([])
const newMessage = ref('')
const isLoading = ref(false)
const isCreatingConversation = ref(false)

const { t } = useI18n()

const { data: rawAssistant } = await useAPI<Assistant>(`/v1/assistants/${assistantId}`)
const assistant = useLocalizedAssistant(rawAssistant as Ref<Assistant>)

if (assistant.value) {
  useHead({
    title: t('chat.chatWith', { name: assistant.value.name })
  })
}

const { $api } = useNuxtApp()
const newConversationStore = useNewConversationStore()
const conversationsStore = useConversationsStore()
const userStore = useUserStore()

const { showError, showSuccess } = useNotifications()


// Check if assistant's model supports vision (image input)
const supportsVision = computed(() => {
  if (!assistant.value?.model?.capabilities) return false
  return assistant.value.model.capabilities.includes('vision')
})

if (import.meta.server) {
  useSeoMeta({
    description: () => assistant.value?.description || t('chat.descriptionFallback')
  })
}

const resetPageState = () => {
  messages.value = []
  newMessage.value = ''
  isLoading.value = false
  isCreatingConversation.value = false
  // Clean up old conversations
  newConversationStore.cleanupOldConversations()
}

const loginPromptShown = ref(false)
const pendingAuthCheck = ref<Promise<boolean> | null>(null)
const inputDisabled = ref(false)

const ensureAuthenticated = async () => {
  if (userStore.user) {
    return true
  }

  if (!pendingAuthCheck.value) {
    pendingAuthCheck.value = (async () => {
      try {
        const loggedIn = await userStore.fetchUser()
        if (loggedIn && userStore.user) {
          return true
        }
      } catch (error) {
        console.error('Failed to fetch user state:', error)
      }

      if (!loginPromptShown.value) {
        showError(t('assistants.loginRequired'))
        loginPromptShown.value = true
      }

      await navigateTo({ path: '/sign-in', query: { redirect: route.fullPath } })
      return false
    })().finally(() => {
      pendingAuthCheck.value = null
    })
  }

  return pendingAuthCheck.value
}

const handleInputFocus = async () => {
  if (userStore.user) {
    return
  }
  inputDisabled.value = true
  await ensureAuthenticated()
}

const handleInputKeydown = async (event: KeyboardEvent) => {
  if (await ensureAuthenticated()) {
    return
  }
  event.preventDefault()
  event.stopPropagation()
}

const sendMessage = async (images?: any[]) => {
  if (!(await ensureAuthenticated())) {
    return
  }

  if (!newMessage.value.trim() || isLoading.value || !assistantId) return

  const messageContent = newMessage.value.trim()
  newMessage.value = ''
  isLoading.value = true
  isCreatingConversation.value = true

  // Add user message to UI immediately for better UX
  const userMessage: Message = {
    id: Date.now().toString(),
    content: messageContent,
    message_type: 'USER',
    created_at: new Date().toISOString(),
    extra_data: images && images.length > 0 ? { images } : undefined
  }
  messages.value.push(userMessage)

  try {
    // Create new conversation using store method
    const conversation = await conversationsStore.createConversation(assistantId)
    if (!conversation) {
      // Remove user message if conversation creation failed
      messages.value = messages.value.filter(msg => msg.id !== userMessage.id)
      isLoading.value = false
      isCreatingConversation.value = false
      return
    }

    // Store conversation state for the next page
    if (assistant?.value) {
      newConversationStore.setConversationData(
        conversation.id,
        userMessage,
        assistant.value
      )
    }

    // Reset page state before navigation to ensure clean state on back navigation
    resetPageState()
    
    // Navigate to the new conversation page
    await navigateTo(`/chat/${conversation.id}`)
  } catch (error) {
    console.error('Failed to initiate conversation:', error)
    // Remove user message if failed
    messages.value = messages.value.filter(msg => msg.id !== userMessage.id)
    isLoading.value = false
    isCreatingConversation.value = false
    showError(`${t('chat.sendFailed')}: ${error instanceof Error ? error.message : t('chat.unknownError')}`)
  }
}

// Reset state when component is mounted (e.g., when user navigates back)
onMounted(() => {
  resetPageState()
})

// Reset state when component is unmounted
onUnmounted(() => {
  resetPageState()
})

watch(() => userStore.user, (val) => {
  if (val) {
    inputDisabled.value = false
  }
})
</script>

<template>
  <ChatLayout v-if="assistant" :assistant="assistant">
    <!-- Welcome message -->
    <ChatWelcome 
      :assistant="assistant" 
      :show-welcome="messages.length === 0" 
    />

    <!-- User Messages -->
    <ChatMessage 
      v-for="message in messages" 
      :key="message.id" 
      :message="message" 
      :assistant="assistant"
    />

    <!-- Loading indicator when creating conversation -->
    <ChatLoading 
      v-if="isCreatingConversation" 
      :assistant="assistant"
      :message="t('chat.creatingConversation', 'Creating new conversation...')"
    />

    <template #input>
      <ChatInput 
        v-model="newMessage"
        :disabled="inputDisabled || isLoading"
        :send-disabled="inputDisabled || isLoading || !newMessage.trim()"
        :supports-vision="supportsVision"
        @keydown="handleInputKeydown"
        @focus="handleInputFocus"
        @click="handleInputFocus"
        @send="sendMessage"
      />
    </template>
  </ChatLayout>
</template>
