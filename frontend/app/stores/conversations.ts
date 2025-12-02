import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Conversation, ConversationsResponse, GenerateTitleResponse } from '~/types/api'

export const useConversationsStore = defineStore('conversations', () => {
  const conversations = ref<Conversation[]>([])
  const currentConversation = ref<Conversation | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const { $api } = useNuxtApp()
  const { showError } = useNotifications()
  
  // Pagination related state
  const currentPage = ref(1)
  const pageSize = ref(20) // 20 conversations per page
  const totalCount = ref(0)
  const hasNextPage = ref(false)
  const isLoadingMore = ref(false)

  // Computed properties
  const conversationCount = computed(() => conversations.value.length)
  const hasConversations = computed(() => conversations.value.length > 0)
  const totalPages = computed(() => Math.ceil(totalCount.value / pageSize.value))

  // Actions
  const fetchConversations = async (page: number = 1, append: boolean = false) => {
    if (append) {
      isLoadingMore.value = true
    } else {
      isLoading.value = true
    }
    error.value = null
    
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        size: pageSize.value.toString()
      })
      
      const data = await $api<ConversationsResponse>(`/v1/conversations?${params}`)
      
      if (append) {
        // Append data to existing list
        conversations.value.push(...data.items)
      } else {
        // Replace existing data
        conversations.value = data.items
      }
      
      // Update pagination state
      currentPage.value = data.page
      totalCount.value = data.total
      hasNextPage.value = data.pages > data.page      
    } catch (err) {
      error.value = 'Failed to fetch conversations'
    } finally {
      isLoading.value = false
      isLoadingMore.value = false
    }
  }

  const loadMore = async () => {
    if (hasNextPage.value && !isLoadingMore.value) {
      await fetchConversations(currentPage.value + 1, true)
    }
  }

  const addConversation = (conversation: Conversation) => {
    conversations.value.unshift(conversation) // Add to the beginning of the list
    totalCount.value += 1 // Update total count
  }

  const createConversation = async (assistantId: string, title: string = 'New Conversation') => {
    isLoading.value = true
    error.value = null
    
    try {
      
      const response = await $api<Conversation>('/v1/conversations', {
        method: 'POST',
        body: {
          assistant_id: assistantId,
          title: title
        }
      })
      // addConversation
      addConversation({
        id: response.id,
        title: response.title
      })
      
      return response
    } catch (err) {
      const { showError } = useNotifications()
      const errorMessage = `Failed to create conversation: ${err instanceof Error ? err.message : 'Unknown error'}`
      error.value = errorMessage
      showError(errorMessage)
      console.error('Failed to create conversation:', err)
      return null
    } finally {
      isLoading.value = false
    }
  }

  const deleteConversation = (id: string) => {
    const initialLength = conversations.value.length
    conversations.value = conversations.value.filter(c => c.id !== id)
    
    // If the conversation was successfully deleted, update total count
    if (conversations.value.length < initialLength) {
      totalCount.value = Math.max(0, totalCount.value - 1)
    }
  }

  const removeConversation = async (id: string) => {
    try {
      await $api(`/v1/conversations/${id}`, {
        method: 'DELETE'
      })
      deleteConversation(id)
    } catch (err) {
      error.value = 'Failed to delete conversation'
      throw err
    }
  }

  const updateConversationTitle = async (id: string, title: string) => {
    try {
      const data = await $api<Conversation>(`/v1/conversations/${id}`, {
        method: 'PUT',
        body: { title }
      })
      
      // Update local state
      const conversation = conversations.value.find(c => c.id === id)
      if (conversation) {
        conversation.title = data.title
      }
      
      return data
    } catch (err) {
      error.value = 'Failed to update conversation'
      throw err
    }
  }

  const generateTitle = async (conversationId: string) => {
    try {
      const response = await $api<GenerateTitleResponse>(`/v1/conversations/${conversationId}/generate-title`, {
        method: 'POST'
      })

      if (response.title) {
        const conversation = conversations.value.find(c => c.id === conversationId)
        if (conversation) {
          conversation.title = response.title
        }
      }

      return response
    } catch (err) {
      const errorMessage = `Failed to generate title: ${err instanceof Error ? err.message : 'Unknown error'}`
      error.value = errorMessage
      showError(errorMessage)
      console.error('Failed to generate title:', err)
      throw err
    }
  }

  const refreshConversations = async () => {
    await fetchConversations(1)
  }

  const setCurrentConversation = (conversation: Conversation | null) => {
    currentConversation.value = conversation
  }

  const clearError = () => {
    error.value = null
  }

  return {
    conversations,
    currentConversation,
    isLoading,
    isLoadingMore,
    error,
    conversationCount,
    hasConversations,
    currentPage,
    pageSize,
    totalCount,
    totalPages,
    hasNextPage,
    fetchConversations,
    loadMore,
    addConversation,
    createConversation,
    deleteConversation,
    removeConversation,
    updateConversationTitle,
    generateTitle,
    refreshConversations,
    setCurrentConversation,
    clearError
  }
})
