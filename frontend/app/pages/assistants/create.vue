<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { toast } from 'vue-sonner'
import { ChevronRight } from 'lucide-vue-next'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '~/components/ui/tabs'
import { Button } from '~/components/ui/button'
import BasicInfo from '~/components/assistants/form/BasicInfo.vue'
import ModelSettings from '~/components/assistants/form/ModelSettings.vue'
import ReviewDeployForm from '~/components/assistants/form/ReviewDeployForm.vue'
import type { Assistant, Model } from '~/types/api'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()

useHead({
  title: t('assistantForm.createTitle')
})

definePageMeta({
  layout: 'default'
})

// State
const loading = ref(false)
const activeTab = ref('basic')
const formData = ref<Partial<Assistant>>({
  name: '',
  description: '',
  instructions: '',
  system_prompt: '',
  model_id: '',
  temperature: 0.7,
  max_history_messages: 10,
  is_public: false,
  status: 'ACTIVE',
  tags: [],
  avatar_file_path: ''
})

// Fetch models
const { data: models } = useAPI<Model[]>('/v1/models', { server: false })
const modelOptions = computed(() => {
  return (models.value ?? []).map(m => ({ label: m.display_name, value: m.id }))
})

// Load from source if needed
onMounted(async () => {
    const sourceId = route.query.source_id as string
    if (sourceId) {
        loading.value = true
        try {
            const { $api } = useNuxtApp()
            const source = await $api<Assistant>(`/v1/assistants/${sourceId}`)
            
            if (source) {
                formData.value = {
                    ...formData.value,
                    name: `${source.name} (Copy)`,
                    description: source.description,
                    system_prompt: source.system_prompt,
                    model_id: source.model_id,
                    temperature: source.temperature,
                    max_history_messages: source.max_history_messages,
                    category: source.category,
                    tags: source.tags || [],
                    avatar_file_path: source.avatar_file_path,
                    // Private copy
                    is_public: false
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

// Validation
const errors = ref<Record<string, string>>({})
const validate = () => {
  const newErrors: Record<string, string> = {}
  if (!formData.value.name?.trim()) newErrors.name = t('common.required')
  if (!formData.value.model_id) newErrors.model_id = t('common.required')
  if (!formData.value.system_prompt?.trim()) newErrors.system_prompt = t('common.required')
  
  errors.value = newErrors
  return Object.keys(newErrors).length === 0
}

const handleCreate = async () => {
  if (!validate()) {
    toast.error(t('common.fixValidationErrors'))
    return
  }

  loading.value = true
  try {
    const { $api } = useNuxtApp()
    await $api('/v1/assistants', {
        method: 'POST',
        body: formData.value
    })
    toast.success(t('assistantForm.createSuccess'))
    router.push('/assistants')
  } catch (error) {
    console.error(error)
    toast.error(t('assistantForm.createFailed'))
  } finally {
    loading.value = false
  }
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

    <div class="flex-1 overflow-y-auto bg-muted/20 p-6">
      <div class="mx-auto max-w-4xl space-y-6">
        
        <Tabs v-model="activeTab" class="w-full">
          <TabsList class="grid w-full grid-cols-3">
            <TabsTrigger value="basic">
              {{ t('assistantForm.tabs.basic') }}
            </TabsTrigger>
            <TabsTrigger value="model">
              {{ t('assistantForm.tabs.model') }}
            </TabsTrigger>
            <TabsTrigger value="review">
              {{ t('assistantForm.tabs.review') }}
            </TabsTrigger>
          </TabsList>

          <div class="mt-6 space-y-6">
            <!-- Basic Info -->
            <TabsContent value="basic">
               <BasicInfo 
                 v-model="formData" 
                 :errors="errors"
                 :enable-categories="false" 
               />
               <div class="mt-4 flex justify-end">
                 <Button @click="activeTab = 'model'">
                   {{ t('common.next') }} <ChevronRight class="ml-2 h-4 w-4" />
                 </Button>
               </div>
            </TabsContent>

            <!-- Model Settings -->
            <TabsContent value="model">
               <ModelSettings 
                 v-model="formData" 
                 :model-options="modelOptions"
                 :errors="errors"
               />
               <div class="mt-4 flex justify-between">
                 <Button variant="outline" @click="activeTab = 'basic'">
                   {{ t('common.prev') }}
                 </Button>
                 <Button @click="activeTab = 'review'">
                   {{ t('common.next') }} <ChevronRight class="ml-2 h-4 w-4" />
                 </Button>
               </div>
            </TabsContent>

            <!-- Review & Deploy -->
            <TabsContent value="review">
               <ReviewDeployForm 
                 v-model="formData"
                 :is-admin="false"
                 :errors="errors"
               />
               
               <div class="mt-6 flex justify-between">
                 <Button variant="outline" @click="activeTab = 'model'">
                   {{ t('common.prev') }}
                 </Button>
                 <div class="flex gap-2">
                   <Button variant="ghost" @click="router.push('/assistants')">
                     {{ t('common.cancel') }}
                   </Button>
                   <Button @click="handleCreate" :disabled="loading">
                     {{ loading ? t('common.creating') : t('common.create') }}
                   </Button>
                 </div>
               </div>
            </TabsContent>
          </div>
        </Tabs>

      </div>
    </div>
  </div>
</template>
