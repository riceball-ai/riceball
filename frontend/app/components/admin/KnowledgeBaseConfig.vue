<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card'
import { Label } from '~/components/ui/label'
import { Input } from '~/components/ui/input'
import { Button } from '~/components/ui/button'
import { Badge } from '~/components/ui/badge'
import { Switch } from '~/components/ui/switch'
import { RefreshCw, Database } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import type { KnowledgeBase, RagConfig } from '~/types/api'

const { t } = useI18n()

interface Props {
  modelValue: {
    knowledge_base_ids?: string[]
    rag_config?: RagConfig
  }
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false
})

const emit = defineEmits<{
  'update:modelValue': [value: Props['modelValue']]
}>()

// State management
const knowledgeBases = ref<KnowledgeBase[]>([])
const loading = ref(false)

// Independent state to control whether to enable knowledge base
const useKnowledgeBase = ref(false)

const selectedCount = computed(() => props.modelValue.knowledge_base_ids?.length || 0)

// Methods
const loadKnowledgeBases = async () => {
  loading.value = true
  try {
    const { $api } = useNuxtApp()
    const response = await $api('/v1/admin/rag/knowledge-bases/all') as any
    knowledgeBases.value = response.items || response || []
  } catch (error) {
    console.error('Failed to load knowledge base list:', error)
    knowledgeBases.value = []
    toast.error(t('components.fileUpload.loadKnowledgeBasesFailed'))
  } finally {
    loading.value = false
  }
}

const toggleKnowledgeBase = (checked: boolean) => {
  useKnowledgeBase.value = checked
  
  if (checked) {
    // When enabling, set default config if not present
    emit('update:modelValue', {
      knowledge_base_ids: props.modelValue.knowledge_base_ids || [],
      rag_config: props.modelValue.rag_config || {
        retrieval_count: 5,
        similarity_threshold: 0.7
      }
    })
  } else {
    // When disabling, clear config
    emit('update:modelValue', {
      knowledge_base_ids: [],
      rag_config: undefined
    })
  }
}

const toggleKnowledgeBaseSelection = (kbId: string, checked: boolean) => {
  const currentIds = [...(props.modelValue.knowledge_base_ids || [])]
  
  if (checked) {
    if (!currentIds.includes(kbId)) {
      currentIds.push(kbId)
    }
  } else {
    const index = currentIds.indexOf(kbId)
    if (index > -1) {
      currentIds.splice(index, 1)
    }
  }
  
  emit('update:modelValue', {
    ...props.modelValue,
    knowledge_base_ids: currentIds
  })
}

const updateRetrievalCount = (value: number) => {
  emit('update:modelValue', {
    ...props.modelValue,
    rag_config: {
      similarity_threshold: 0.7,
      ...props.modelValue.rag_config,
      retrieval_count: value
    }
  })
}

const updateSimilarityThreshold = (value: number) => {
  emit('update:modelValue', {
    ...props.modelValue,
    rag_config: {
      retrieval_count: 5,
      ...props.modelValue.rag_config,
      similarity_threshold: value
    }
  })
}

// Watch props changes, sync enable state
watch(() => props.modelValue, (newValue) => {
  // If rag_config is present, or we have selected IDs, consider it enabled
  const hasConfig = !!newValue.rag_config || (newValue.knowledge_base_ids && newValue.knowledge_base_ids.length > 0)
  if (hasConfig !== useKnowledgeBase.value) {
    useKnowledgeBase.value = hasConfig
  }
}, { immediate: true, deep: true })

// Lifecycle
onMounted(() => {
  loadKnowledgeBases()
})
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle class="flex items-center gap-2">
        <Database class="h-5 w-5" />
        {{ t('components.knowledgeBaseConfig.title') }}
      </CardTitle>
      <CardDescription>
        {{ t('components.knowledgeBaseConfig.description') }}
      </CardDescription>
    </CardHeader>
    <CardContent class="space-y-6">
      <!-- Enable knowledge base switch -->
      <div class="flex items-center space-x-3">
        <Switch
          id="use-knowledge-base"
          :model-value="useKnowledgeBase"
          :disabled="disabled || loading"
          @update:model-value="toggleKnowledgeBase"
        />
        <Label for="use-knowledge-base" class="text-sm font-medium cursor-pointer">
          {{ t('components.knowledgeBaseConfig.enable') }}
        </Label>
      </div>

      <!-- Knowledge base config area -->
      <div v-if="useKnowledgeBase" class="space-y-6 pl-6 border-l-2 border-primary/20">
        <!-- Knowledge base selection -->
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <Label class="text-sm font-medium">
              {{ t('components.knowledgeBaseConfig.selectKnowledgeBase') }}
              <span v-if="selectedCount > 0" class="text-muted-foreground">
                {{ t('components.knowledgeBaseConfig.selectedCount', { count: selectedCount }) }}
              </span>
            </Label>
            <Button
              variant="outline"
              size="sm"
              @click="loadKnowledgeBases"
              :disabled="loading"
            >
              <RefreshCw class="h-4 w-4 mr-1" :class="{ 'animate-spin': loading }" />
              {{ t('components.knowledgeBaseConfig.refresh') }}
            </Button>
          </div>

          <!-- Knowledge base list -->
          <div class="space-y-2 max-h-40 overflow-y-auto border rounded-md p-3">
            <div v-if="loading" class="text-center py-4 text-muted-foreground">
              {{ t('components.knowledgeBaseConfig.loading') }}
            </div>
            <div v-else-if="knowledgeBases.length === 0" class="text-center py-4 text-muted-foreground">
              {{ t('components.knowledgeBaseConfig.noKnowledgeBases') }}
            </div>
            <div
              v-else
              v-for="kb in knowledgeBases"
              :key="kb.id"
              class="flex items-start space-x-3 p-2 rounded hover:bg-muted transition-colors"
            >
              <input
                :id="`kb-${kb.id}`"
                type="checkbox"
                :checked="props.modelValue.knowledge_base_ids?.includes(kb.id)"
                :disabled="disabled"
                @change="(e) => toggleKnowledgeBaseSelection(kb.id, (e.target as HTMLInputElement).checked)"
                class="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary mt-1"
              />
              <Label :for="`kb-${kb.id}`" class="flex-1 cursor-pointer space-y-1">
                <div class="font-medium text-sm">{{ kb.name }}</div>
                <div class="text-xs text-muted-foreground">{{ kb.description }}</div>
              </Label>
            </div>
          </div>
        </div>

        <!-- Retrieval parameter config -->
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-2">
            <Label for="retrieval-count" class="text-sm font-medium">
              {{ t('components.knowledgeBaseConfig.retrievalCount') }}
            </Label>
            <Input
              id="retrieval-count"
              type="number"
              :model-value="props.modelValue.rag_config?.retrieval_count || 5"
              :disabled="disabled"
              :min="1"
              :max="20"
              placeholder="5"
              @update:model-value="(val) => updateRetrievalCount(Number(val))"
            />
            <div class="text-xs text-muted-foreground">
              {{ t('components.knowledgeBaseConfig.retrievalCountHelp') }}
            </div>
          </div>

          <div class="space-y-2">
            <Label for="similarity-threshold" class="text-sm font-medium">
              {{ t('components.knowledgeBaseConfig.similarityThreshold') }}
            </Label>
            <Input
              id="similarity-threshold"
              type="number"
              :model-value="props.modelValue.rag_config?.similarity_threshold || 0.7"
              :disabled="disabled"
              :min="0"
              :max="1"
              :step="0.01"
              placeholder="0.7"
              @update:model-value="(val) => updateSimilarityThreshold(Number(val))"
            />
            <div class="text-xs text-muted-foreground">
              {{ t('components.knowledgeBaseConfig.similarityThresholdHelp') }}
            </div>
          </div>
        </div>

        <!-- Config description -->
        <div class="bg-muted/50 p-3 rounded-md text-sm space-y-2">
          <div class="font-medium">{{ t('components.knowledgeBaseConfig.configDescription') }}</div>
          <ul class="space-y-1 text-muted-foreground text-xs ml-4">
            <li>• <strong>{{ t('components.knowledgeBaseConfig.retrievalCount') }}:</strong> {{ t('components.knowledgeBaseConfig.configTips.retrievalCount') }}</li>
            <li>• <strong>{{ t('components.knowledgeBaseConfig.similarityThreshold') }}:</strong> {{ t('components.knowledgeBaseConfig.configTips.similarityThreshold') }}</li>
            <li>• {{ t('components.knowledgeBaseConfig.configTips.recommended') }}</li>
          </ul>
        </div>
      </div>
    </CardContent>
  </Card>
</template>
