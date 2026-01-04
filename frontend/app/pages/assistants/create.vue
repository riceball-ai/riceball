<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { toast } from 'vue-sonner'
import AssistantForm from '~/components/assistants/AssistantForm.vue'
import type { Assistant } from '~/types/api'

const { t } = useI18n()

useHead({
  title: t('assistantForm.createTitle')
})

// Page metadata
definePageMeta({
    layout: 'default'
})

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const initialData = ref<Partial<Assistant>>({})

// Handle source_id for copying
onMounted(async () => {
    const sourceId = route.query.source_id as string
    if (sourceId) {
        loading.value = true
        try {
            const { $api } = useNuxtApp()
            const sourceAssistant = await $api<Assistant>(`/v1/assistants/${sourceId}`)
            
            if (sourceAssistant) {
                initialData.value = {
                    name: `${sourceAssistant.name} (Copy)`,
                    description: sourceAssistant.description,
                    system_prompt: sourceAssistant.system_prompt,
                    model_id: sourceAssistant.model_id,
                    temperature: sourceAssistant.temperature,
                    max_history_messages: sourceAssistant.max_history_messages,
                    category: sourceAssistant.category,
                    tags: sourceAssistant.tags || [],
                    avatar_file_path: sourceAssistant.avatar_file_path,
                    // Ensure it is private
                    is_public: false,
                    status: 'ACTIVE'
                }
                toast.success(t('assistantForm.loadedFromSource'))
            }
        } catch (error) {
            console.error('Failed to load source assistant:', error)
            toast.error(t('assistantForm.loadSourceFailed'))
        } finally {
            loading.value = false
        }
    }
})

// Create assistant
const createAssistant = async (data: Partial<Assistant>) => {
    loading.value = true
    try {
        const { $api } = useNuxtApp()

        await $api('/v1/assistants', {
            method: 'POST',
            body: data
        })

        toast.success(t('assistantForm.createSuccess'))
        router.push('/assistants')

    } catch (error) {
        toast.error(t('assistantForm.createFailed'))
    } finally {
        loading.value = false
    }
}

// Cancel action
const handleCancel = () => {
    router.push('/assistants')
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
                                {{ t('chat.breadcrumbAssistants') }}
                            </NuxtLink>
                        </BreadcrumbLink>
                    </BreadcrumbItem>
                    <BreadcrumbSeparator />
                    <BreadcrumbItem>
                        <BreadcrumbPage>{{ t('assistantForm.createTitle') }}</BreadcrumbPage>
                    </BreadcrumbItem>
                </BreadcrumbList>
            </Breadcrumb>
        </AppHeader>

        <div class="flex-1 overflow-y-auto">
            <div class="container mx-auto py-6 space-y-6 max-w-4xl">
                <AssistantForm
                    :initial-data="initialData"
                    :is-admin="false"
                    :loading="loading"
                    @submit="createAssistant"
                    @cancel="handleCancel"
                />
            </div>
        </div>
    </div>
</template>
