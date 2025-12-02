<script setup lang="ts">
import { Brain, Search, Database, Code, FileText, Zap } from 'lucide-vue-next'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '~/components/ui/collapsible'

export interface AgentStep {
  type: 'agent_action' | 'agent_observation'
  tool?: string
  tool_display_name?: string
  observation?: string
  description?: string
  timestamp?: number
}

interface Props {
  steps: AgentStep[]
  isThinking?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isThinking: false
})

const { t } = useI18n()

// Tool icon mapping
const getToolIcon = (toolName?: string) => {
  if (!toolName) return Brain
  
  const iconMap: Record<string, any> = {
    'knowledge_base_query': Database,
    'web_search': Search,
    'code_interpreter': Code,
    'file_reader': FileText,
    'calculator': Zap,
  }
  
  return iconMap[toolName] || Brain
}

// Get the display text for the step
const getStepText = (step: AgentStep) => {
  return step.description || step.observation || t('chat.agentThinking.processing')
}

// Control collapse state - collapsed by default
const isOpen = ref(false)

// Get the last step
const lastStep = computed(() => {
  if (props.steps.length === 0) return null
  return props.steps[props.steps.length - 1]
})
</script>

<template>
  <div class="w-full">
    <Collapsible v-model:open="isOpen" class="space-y-2">
      <!-- Main container - black/gray theme -->
      <div class="rounded-lg border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 p-4">
        <!-- Header - collapsible trigger -->
        <CollapsibleTrigger class="flex items-center justify-between w-full group hover:opacity-80 transition-opacity">
          <div class="flex items-center gap-2 flex-1 min-w-0">
            <!-- Icon container -->
            <div class="relative flex-shrink-0">
              <Brain class="w-5 h-5 text-gray-700 dark:text-gray-300" :class="{ 'animate-pulse': isThinking }" />
              <!-- Pulse effect - shown when thinking -->
              <div v-if="isThinking" class="absolute -inset-1 bg-gray-500 dark:bg-gray-400 rounded-full opacity-20 animate-ping"></div>
            </div>
            
            <!-- Show last step when collapsed -->
            <div v-if="!isOpen && lastStep" class="flex items-start gap-2 flex-1 min-w-0">
              <!-- Content of the last step -->
              <div class="flex-1 min-w-0 truncate text-sm text-left text-gray-600 dark:text-gray-400">
                <span v-if="lastStep.tool_display_name">{{ lastStep.tool_display_name }}: </span>{{ getStepText(lastStep) }}
              </div>
            </div>
            
              <!-- Show title when expanded -->
            <div v-else class="flex items-center gap-2">
              <!-- Title text -->
              <span class="font-medium text-gray-900 dark:text-gray-100">
                {{ isThinking ? t('chat.agentThinking.thinking') : t('chat.agentThinking.thinkingProcess') }}
              </span>
            </div>
          </div>
          
          <!-- Collapse icon -->
          <div class="text-gray-600 dark:text-gray-400 transition-transform duration-200 flex-shrink-0 ml-2" :class="{ 'rotate-180': isOpen }">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </div>
        </CollapsibleTrigger>

        <!-- Step list - collapsible content -->
        <CollapsibleContent class="mt-3 max-h-32 overflow-y-auto">
          <div class="space-y-2">
            <!-- Single step card -->
            <div 
              v-for="(step, index) in steps" 
              :key="index"
              class="flex items-start gap-3 p-3 rounded-md bg-white dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 transition-all hover:shadow-sm hover:border-gray-300 dark:hover:border-gray-600"
            >
              <!-- Tool icon -->
              <div class="mt-0.5 flex-shrink-0">
                <component 
                  :is="getToolIcon(step.tool)" 
                  class="w-4 h-4 text-gray-600 dark:text-gray-400"
                />
              </div>
              
              <!-- Step content -->
              <div class="flex-1 min-w-0">
                <!-- Tool name -->
                <div v-if="step.tool_display_name" class="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                  {{ step.tool_display_name }}
                </div>
                <!-- Description text -->
                <div class="text-sm text-gray-700 dark:text-gray-300 break-words">
                  {{ getStepText(step) }}
                </div>
              </div>
              
              <!-- Step number -->
              <div class="flex-shrink-0 text-xs text-gray-500 dark:text-gray-400 font-mono">
                {{ t('chat.agentThinking.stepNumber', { number: index + 1 }) }}
              </div>
            </div>
            
            <!-- Loading animation when thinking -->
            <div v-if="isThinking" class="flex items-center gap-3 p-3 rounded-md bg-white dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700">
              <div class="flex space-x-1">
                <div class="w-2 h-2 bg-gray-600 dark:bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
                <div class="w-2 h-2 bg-gray-600 dark:bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
                <div class="w-2 h-2 bg-gray-600 dark:bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
              </div>
              <span class="text-sm text-gray-600 dark:text-gray-400">{{ t('chat.agentThinking.processing') }}</span>
            </div>
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  </div>
</template>

<style scoped>
@keyframes bounce {
  0%, 80%, 100% {
    transform: translateY(0);
  }
  40% {
    transform: translateY(-6px);
  }
}

.animate-bounce {
  animation: bounce 1.4s infinite;
}
</style>
