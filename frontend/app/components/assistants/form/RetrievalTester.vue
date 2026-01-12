<script setup lang="ts">
import { ref } from 'vue'
import { Search, Loader2, FileText, Database } from 'lucide-vue-next'
import { Button } from '~/components/ui/button'
import { Input } from '~/components/ui/input'
import { Card, CardHeader, CardContent } from '~/components/ui/card'
import { Badge } from '~/components/ui/badge'
import type { RetrievalResult } from '~/types/api'
import { useNuxtApp } from '#app'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  assistantId: string
}>()

const { t } = useI18n()
const query = ref('')
const loading = ref(false)
const result = ref<RetrievalResult | null>(null)
const error = ref('')

const handleTest = async () => {
    if (!query.value.trim()) return
    
    loading.value = true
    error.value = ''
    result.value = null
    
    try {
        const { $api } = useNuxtApp()
        const data = await $api<RetrievalResult>(`/v1/admin/assistants/${props.assistantId}/retrieval-test`, {
            method: 'POST',
            body: { query: query.value }
        })
        result.value = data
    } catch (e: any) {
        error.value = e.message || 'Failed to test retrieval'
    } finally {
        loading.value = false
    }
}
</script>

<template>
  <div class="space-y-6">
    <div class="bg-muted/30 p-4 rounded-lg space-y-4">
        <h3 class="text-sm font-medium">{{ t('assistants.retrievalTest.simulatorTitle') }}</h3>
        <p class="text-xs text-muted-foreground">
            {{ t('assistants.retrievalTest.description') }}
        </p>
        <div class="flex gap-2">
            <Input 
                v-model="query" 
                :placeholder="t('assistants.retrievalTest.placeholder')" 
                @keyup.enter="handleTest" 
            />
            <Button :disabled="loading || !query.trim()" @click="handleTest">
                <Loader2 v-if="loading" class="w-4 h-4 mr-2 animate-spin" />
                <Search v-else class="w-4 h-4 mr-2" />
                {{ t('assistants.retrievalTest.testButton') }}
            </Button>
        </div>
        <div v-if="error" class="text-red-500 text-xs">{{ error }}</div>
    </div>

    <div v-if="result" class="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
        <div class="flex items-center justify-between">
            <h3 class="font-medium text-sm text-muted-foreground">
                {{ t('assistants.retrievalTest.foundChunks', { count: result.chunks.length }) }}
            </h3>
        </div>
        
        <div v-if="result.chunks.length === 0" class="text-center py-8 text-muted-foreground border rounded-lg border-dashed">
            {{ t('assistants.retrievalTest.noResults') }} <br />
            <span class="text-xs">{{ t('assistants.retrievalTest.noResultsHint') }}</span>
        </div>

        <div v-else class="grid gap-4">
            <Card v-for="(chunk, idx) in result.chunks" :key="idx" class="overflow-hidden border-l-4 border-l-primary/50">
                <CardHeader class="bg-muted/30 py-3 px-4 flex flex-row items-center justify-between space-y-0">
                    <div class="flex items-center gap-2 overflow-hidden">
                         <FileText class="w-4 h-4 text-primary flex-shrink-0" />
                         <span class="font-medium text-sm truncate max-w-[300px]" :title="chunk.metadata?.title || chunk.metadata?.source">
                            {{ chunk.metadata?.title || chunk.metadata?.source || t('assistants.retrievalTest.untitled') }}
                         </span>
                    </div>
                    <Badge variant="secondary" class="ml-2 flex-shrink-0 text-xs">
                        {{ t('assistants.retrievalTest.rank', { rank: idx + 1 }) }}
                    </Badge>
                </CardHeader>
                <CardContent class="p-0">
                    <div class="p-4 text-sm whitespace-pre-wrap font-mono bg-slate-50 dark:bg-slate-950 text-foreground/80 max-h-60 overflow-y-auto custom-scrollbar">
{{ chunk.content }}
                    </div>
                    <div class="px-4 py-2 bg-muted/20 text-[10px] text-muted-foreground flex justify-between border-t items-center">
                        <div class="flex items-center gap-1.5 code">
                            <Database class="w-3 h-3" />
                            <span class="font-mono">{{ chunk.kb_id }}</span>
                        </div>
                        <div v-if="chunk.metadata?.page" class="flex items-center gap-1">
                            {{ t('assistants.retrievalTest.page', { page: chunk.metadata.page }) }}
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    </div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
    width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
    background-color: var(--border);
    border-radius: 20px;
}
</style>