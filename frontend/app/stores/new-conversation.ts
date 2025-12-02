import { defineStore } from 'pinia'
import type { Assistant, Message } from '~/types/api'

interface NewConversationData {
  userMessage: Message
  assistant: Assistant
  isTransitioning: boolean
  timestamp: number
}

interface NewConversationState {
  conversations: Record<string, NewConversationData>
}

export const useNewConversationStore = defineStore('new-conversation', () => {
  const state = ref<NewConversationState>({
    conversations: {}
  })

  const setConversationData = (
    conversationId: string,
    userMessage: Message,
    assistant: Assistant
  ) => {
    state.value.conversations[conversationId] = {
      userMessage,
      assistant,
      isTransitioning: true,
      timestamp: Date.now()
    }
  }

  const getConversationData = (conversationId: string) => {
    return state.value.conversations[conversationId] || null
  }

  const clearConversationData = (conversationId: string) => {
    delete state.value.conversations[conversationId]
  }

  const completeTransition = (conversationId: string) => {
    const conversation = state.value.conversations[conversationId]
    if (conversation) {
      conversation.isTransitioning = false
    }
  }

  const isNewConversation = (conversationId: string) => {
    const conversation = state.value.conversations[conversationId]
    return conversation?.isTransitioning || false
  }

  // Clean up old conversations (older than 5 minutes)
  const cleanupOldConversations = () => {
    const fiveMinutesAgo = Date.now() - 5 * 60 * 1000
    for (const [id, data] of Object.entries(state.value.conversations)) {
      if (data.timestamp < fiveMinutesAgo) {
        delete state.value.conversations[id]
      }
    }
  }

  return {
    state,
    setConversationData,
    getConversationData,
    clearConversationData,
    completeTransition,
    isNewConversation,
    cleanupOldConversations
  }
})
