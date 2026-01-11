<script setup lang="ts">
import { ref, onMounted } from "vue"
import { useRouter, useRoute } from "vue-router"
import { toast } from "vue-sonner"
import { Share2 } from "lucide-vue-next"
import { Button } from "@/components/ui/button"
import AssistantForm from "~/components/assistants/AssistantForm.vue"
import type { Assistant } from "~/types/api"

const { t } = useI18n()

useHead({
  title: t("assistantForm.editTitle")
})

// Page metadata
definePageMeta({
  layout: "default"
})

const router = useRouter()
const route = useRoute()
const assistantId = route.params.id as string

// State management
const loading = ref(false)
const fetching = ref(true)
const assistant = ref<Assistant | null>(null)

// Fetch assistant details
const fetchAssistant = async () => {
  fetching.value = true
  try {
    const { $api } = useNuxtApp()
    const data = await $api<Assistant>(`/v1/assistants/${assistantId}`)
    assistant.value = data
  } catch (error) {
    console.error("Failed to fetch assistant details:", error)
    toast.error(t("assistantForm.fetchFailed"))
    router.push("/assistants")
  } finally {
    fetching.value = false
  }
}

onMounted(() => {
  fetchAssistant()
})

// Update assistant
const updateAssistant = async (data: Partial<Assistant>) => {
  loading.value = true
  try {
    const { $api } = useNuxtApp()
    
    await $api(`/v1/assistants/${assistantId}`, {
      method: "PUT",
      body: data
    })
    
    toast.success(t("assistantForm.updateSuccess"))
    router.push("/assistants")
    
  } catch (error) {
    console.error("Update failed:", error)
    toast.error(t("assistantForm.updateFailed"))
  } finally {
    loading.value = false
  }
}

// Cancel action
const handleCancel = () => {
  router.push("/assistants")
}
</script>

<template>
  <div class="absolute inset-0 flex flex-col overflow-hidden rounded-[inherit]">
    <AppHeader>
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink as-child>
              <NuxtLink to="/assistants">
                {{ t("chat.breadcrumbAssistants") }}
              </NuxtLink>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>{{ t("assistantForm.editTitle") }}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
    </AppHeader>

    <div class="flex-1 overflow-y-auto">
      <div class="container mx-auto py-6 space-y-6 max-w-4xl">
        <div v-if="fetching" class="flex justify-center py-12">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>

        <div v-else-if="assistant" class="space-y-6">
            <AssistantForm
            :initial-data="assistant"
            :is-admin="false"
            :loading="loading"
            @submit="updateAssistant"
            @cancel="handleCancel"
            />
        </div>
      </div>
    </div>
  </div>
</template>
