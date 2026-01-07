<script setup lang="ts">
import {
  MoreVertical,
  Trash2,
  ChevronDown,
  Pencil,
} from "lucide-vue-next"

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar"

import { useConversationsStore } from "@/stores/conversations"
import { storeToRefs } from 'pinia'

const { isMobile } = useSidebar()

const route = useRoute()

const conversationsStore = useConversationsStore()
const {
  conversations,
  isLoading,
  isLoadingMore,
  error,
  hasConversations,
  hasNextPage,
  totalCount,
  currentPage,
} = storeToRefs(conversationsStore)

const {
  removeConversation,
  fetchConversations,
  loadMore,
  updateConversationTitle
} = conversationsStore

const editingId = ref<string | null>(null)
const editingTitle = ref('')

const startRename = (conversation: any) => {
  editingId.value = conversation.id
  editingTitle.value = conversation.title
}

const cancelRename = () => {
  editingId.value = null
  editingTitle.value = ''
}

const confirmRename = async (id: string) => {
  const trimmedTitle = editingTitle.value.trim()
  
  if (!trimmedTitle) {
    cancelRename()
    return
  }
  
  const originalTitle = conversations.value.find(c => c.id === id)?.title
  if (trimmedTitle === originalTitle) {
    cancelRename()
    return
  }
  
  try {
    await updateConversationTitle(id, trimmedTitle)
    editingId.value = null
    editingTitle.value = ''
  } catch (error) {
    console.error('Failed to rename conversation:', error)
  }
}

onMounted(() => {
  fetchConversations()
})

const handleLoadMore = async () => {
  if (hasNextPage.value && !isLoadingMore.value) {
    await loadMore()
  }
}
</script>

<template>
  <SidebarGroup class="group-data-[collapsible=icon]:hidden">
    <SidebarGroupLabel>{{ $t('nav.history') }}</SidebarGroupLabel>
    <SidebarMenu>
      <SidebarMenuItem v-if="isLoading">
        <SidebarMenuButton class="text-sidebar-foreground/70">
          <span>{{ $t('nav.loadingHistory') }}</span>
        </SidebarMenuButton>
      </SidebarMenuItem>
      <SidebarMenuItem v-else-if="error">
        <SidebarMenuButton class="text-sidebar-foreground/70">
          <span>{{ $t('nav.errorLoadingHistory') }}</span>
        </SidebarMenuButton>
      </SidebarMenuItem>
      <SidebarMenuItem v-else-if="!hasConversations">
        <SidebarMenuButton class="text-sidebar-foreground/70">
          <span>{{ $t('nav.noConversations') }}</span>
        </SidebarMenuButton>
      </SidebarMenuItem>
      <SidebarMenuItem v-else v-for="item in conversations" :key="item.id">
        <SidebarMenuButton as-child :is-active="route.path === `/chat/${item.id}`">
          <NuxtLink v-if="editingId !== item.id" :to="`/chat/${item.id}`" :title="item.title">
            <span>{{ item.title }}</span>
          </NuxtLink>
          <div v-else class="flex items-center w-full">
            <input
              v-model="editingTitle"
              @keyup.enter="confirmRename(item.id)"
              @keyup.escape="cancelRename"
              @blur="confirmRename(item.id)"
              class="flex-1 bg-transparent border-none outline-none text-sm"
              :placeholder="item.title"
              autofocus
            />
          </div>
        </SidebarMenuButton>
        <DropdownMenu v-if="editingId !== item.id">
          <DropdownMenuTrigger as-child>
            <SidebarMenuAction show-on-hover>
              <MoreVertical />
              <span class="sr-only">More</span>
            </SidebarMenuAction>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            class="w-56 rounded-lg"
            :side="isMobile ? 'bottom' : 'right'"
            :align="isMobile ? 'end' : 'start'"
          >
            <DropdownMenuItem @click="startRename(item)">
              <Pencil class="text-muted-foreground" />
              <span>{{ $t('common.rename') }}</span>
            </DropdownMenuItem>
            <DropdownMenuItem @click="removeConversation(item.id)">
              <Trash2 class="text-muted-foreground" />
              <span>{{ $t('common.delete') }}</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>

      <SidebarMenuItem v-if="hasConversations && totalCount > conversations.length">
        <SidebarMenuButton 
          @click="handleLoadMore" 
          :disabled="isLoadingMore || !hasNextPage"
          class="text-sidebar-foreground/70 hover:text-sidebar-foreground"
        >
          <ChevronDown v-if="!isLoadingMore" />
          <div v-else class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
          <span v-if="isLoadingMore">{{ $t('nav.loading') }}</span>
          <span v-else-if="hasNextPage">{{ $t('nav.loadMore') }} ({{ conversations.length }}/{{ totalCount }})</span>
          <span v-else>{{ $t('nav.allLoaded') }} ({{ totalCount }})</span>
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarMenu>
  </SidebarGroup>
</template>
