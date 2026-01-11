<script setup lang="ts">
import { ref, onMounted } from "vue"
import { useRouter, useRoute } from "vue-router"
import { toast } from "vue-sonner"
import type { Assistant } from "~/types/api"
import ChannelList from "~/components/channels/ChannelList.vue"
import { Button } from "@/components/ui/button"
import { ChevronLeft } from "lucide-vue-next"

const { t } = useI18n()
useHead({ title: t('assistants.integrations.title_page') })

const route = useRoute()
const router = useRouter()
const assistantId = route.params.id as string
const loading = ref(true)
const assistant = ref<Assistant | null>(null)

// Page metadata
definePageMeta({
  layout: "admin",
  breadcrumb: 'assistants.integrations.title_page'
})

onMounted(async () => {
  try {
    const { $api } = useNuxtApp()
    assistant.value = await $api<Assistant>(`/v1/admin/assistants/${assistantId}`)
  } catch (error) {
    toast.error(t('assistants.integrations.failed_load'))
    router.push("/admin/assistants")
  } finally {
    loading.value = false
  }
})

</script>

<template>
  <div class="container py-6 max-w-4xl mx-auto">
    <div class="mb-6 flex items-center gap-4">
       <Button variant="ghost" size="icon" @click="router.push(`/admin/assistants/${assistantId}/edit`)">
        <ChevronLeft class="w-5 h-5" />
      </Button>
      <div>
        <h1 class="text-2xl font-bold tracking-tight">{{ t('assistants.integrations.title') }}</h1>
        <p class="text-muted-foreground" v-if="assistant">
            {{ t('assistants.integrations.manage_channels_for', { name: assistant.name }) }}
        </p>
      </div>
    </div>

    <div v-if="loading" class="space-y-4">
       <div class="h-8 w-1/3 bg-slate-100 animate-pulse rounded"></div>
       <div class="h-64 bg-slate-100 animate-pulse rounded"></div>
    </div>

    <div v-else>
       <ChannelList :assistant-id="assistantId" />
    </div>
  </div>
</template>
