<script setup lang="ts">
import { Plus, Pin, PinOff } from "lucide-vue-next"
import type { Assistant } from '~/types/api'
import { toast } from 'vue-sonner'

interface Props {
  assistant: Assistant
  title?: string | null
  emptyState?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  emptyState: false
})
const { t } = useI18n()
const { $api } = useNuxtApp()
const userStore = useUserStore()

// Local state for pin status to ensure reactivity
const isPinned = ref(props.assistant.is_pinned)

// Sync with prop if it changes externally
watch(() => props.assistant.is_pinned, (newVal) => {
  isPinned.value = newVal
})

const handlePin = async () => {
  if (!userStore.user) {
    toast.error(t('auth.loginRequired'))
    return
  }
  
  const originalState = isPinned.value
  const newState = !originalState
  
  // Optimistic update
  isPinned.value = newState
  // Also update the prop object to keep it in sync
  props.assistant.is_pinned = newState
  
  try {
    if (originalState) { // Was pinned, so unpin
      await $api(`/v1/assistants/${props.assistant.id}/pin`, { method: 'DELETE' })
      toast.success(t('assistants.unpinned'))
    } else {
      await $api(`/v1/assistants/${props.assistant.id}/pin`, { method: 'POST' })
      toast.success(t('assistants.pinned'))
    }
  } catch (e) {
    console.error('Failed to toggle pin', e)
    toast.error(t('common.error'))
    // Revert
    isPinned.value = originalState
    props.assistant.is_pinned = originalState
  }
}
</script>

<template>
  <div class="h-screen flex flex-col">
    <AppHeader>
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem class="hidden md:block">
            <BreadcrumbLink as-child>
              <NuxtLink to="/assistants">
                {{ t('chat.breadcrumbAssistants') }}
              </NuxtLink>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator class="hidden md:block" />
          <BreadcrumbItem>
            <BreadcrumbPage class="flex items-center">
              <AssistantAvatar :assistant="assistant" class="size-4 mr-1 inline-block align-middle" />
              {{ assistant.name }}
            </BreadcrumbPage>
          </BreadcrumbItem>
          <BreadcrumbSeparator v-if="title" class="hidden md:block" />
          <BreadcrumbItem v-if="title">
            <BreadcrumbPage>{{ title }}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <template #right>
        <div class="flex items-center gap-2" v-if="assistant">
          <Button
            v-if="userStore.user"
            variant="outline"
            size="icon"
            :title="isPinned ? t('assistants.unpin') : t('assistants.pin')"
            @click="handlePin"
          >
            <PinOff v-if="isPinned" class="h-4 w-4 text-primary fill-primary" />
            <Pin v-else class="h-4 w-4" />
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <Button variant="outline" size="icon" :title="t('chat.newConversation')">
                <Plus />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem as-child>
                <NuxtLink :to="`/chatwith/${assistant.id}`">
                  {{ t('chat.actions.withCurrentAssistant') }}
                </NuxtLink>
              </DropdownMenuItem>
              <DropdownMenuItem>
                <NuxtLink to="/assistants">
                  {{ t('chat.actions.chooseAnotherAssistant') }}
                </NuxtLink>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </template>
    </AppHeader>
    
    <!-- Chat content area -->
    <div class="flex-1 overflow-y-auto">
      <div 
        class="p-4"
        :class="{ 'pb-40': !emptyState, 'h-full flex flex-col justify-center pb-[20vh]': emptyState }"
      >
        <div class="max-w-4xl mx-auto space-y-4 w-full">
          <slot />
        </div>
      </div>
    </div>

    <!-- Input area slot (only shown if not empty state OR if explicity populated in empty state via slot check, 
         but usually in empty state we want input inside the main flow) -->
    <div v-if="!emptyState || $slots.input" class="absolute bottom-0 left-0 right-0 z-50">
      <div class="p-4">
        <div class="max-w-4xl mx-auto">
          <slot name="input" />
        </div>
      </div>
    </div>
  </div>
</template>
