<script setup lang="ts">
import { useAPI } from '~/composables/useAPI'
import { ref } from 'vue'
import { ThumbsUp, ThumbsDown, Search, ArrowRight, MessageSquare, AlertCircle } from 'lucide-vue-next'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet'
import { useMarkdown } from '~/composables/useMarkdown'

const { t } = useI18n()
const { renderMarkdown } = useMarkdown()

definePageMeta({
  layout: 'admin',
  breadcrumb: 'admin.pages.feedbacks.breadcrumb'
})

const page = ref(1)
const size = ref(20)
const feedbackFilter = ref<string>('dislike')
const search = ref('')
const selectedMessage = ref<any>(null)
const detailsOpen = ref(false)

const { data, refresh, pending } = await useAPI<any>('/api/v1/admin/messages', {
  query: computed(() => ({
    page: page.value,
    size: size.value,
    feedback: feedbackFilter.value === 'all' ? undefined : feedbackFilter.value,
    search: search.value || undefined
  }))
})

// Debounce search
let searchTimer: NodeJS.Timeout
const handleSearch = (e: Event) => {
  const target = e.target as HTMLInputElement
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    search.value = target.value
    page.value = 1
  }, 500)
}

const openDetails = (message: any) => {
  selectedMessage.value = message
  detailsOpen.value = true
}

const formatDate = (date: string) => {
  return new Date(date).toLocaleString()
}

const truncate = (text: string, length = 100) => {
  if (!text) return ''
  return text.length > length ? text.substring(0, length) + '...' : text
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold tracking-tight">Feedback Review</h2>
        <p class="text-muted-foreground">Review user feedback on assistant responses to improve quality.</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex items-center gap-4">
      <div class="flex items-center rounded-md border bg-background p-1">
        <button
          v-for="opt in [
            { value: 'dislike', label: 'Needs Improvement', icon: ThumbsDown },
            { value: 'like', label: 'Positive', icon: ThumbsUp },
            { value: 'all', label: 'All', icon: null }
          ]"
          :key="opt.value"
          @click="feedbackFilter = opt.value; page = 1"
          class="flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-sm transition-colors"
          :class="feedbackFilter === opt.value ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:bg-muted hover:text-foreground'"
        >
          <component :is="opt.icon" v-if="opt.icon" class="w-4 h-4" />
          {{ opt.label }}
        </button>
      </div>

      <div class="relative max-w-sm flex-1">
        <Search class="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          type="search"
          placeholder="Search content..."
          class="pl-9"
          :value="search"
          @input="handleSearch"
        />
      </div>
    </div>

    <!-- Table -->
    <div class="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead class="w-[50px]">Status</TableHead>
            <TableHead class="w-[200px]">Assistant</TableHead>
            <TableHead class="max-w-[300px]">User Query (Context)</TableHead>
            <TableHead>Response Preview</TableHead>
            <TableHead class="w-[180px]">Time</TableHead>
            <TableHead class="w-[80px]">Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-if="pending && !data?.items?.length">
            <TableCell colspan="6" class="h-24 text-center">Loading...</TableCell>
          </TableRow>
          
          <TableRow v-else-if="!data?.items?.length">
            <TableCell colspan="6" class="h-24 text-center text-muted-foreground">
              No feedback found.
            </TableCell>
          </TableRow>

          <TableRow v-for="item in data?.items" :key="item.id">
            <TableCell>
              <ThumbsDown v-if="item.feedback === 'dislike'" class="w-5 h-5 text-red-500" />
              <ThumbsUp v-else-if="item.feedback === 'like'" class="w-5 h-5 text-green-500" />
              <div v-else class="w-5 h-5 rounded-full border-2 border-gray-300"></div>
            </TableCell>
            <TableCell>
              <div class="font-medium">{{ item.assistant_name }}</div>
              <div class="text-xs text-muted-foreground truncate" :title="item.assistant_id">{{ item.assistant_id }}</div>
            </TableCell>
            <TableCell>
              <div v-if="item.context_message" class="flex flex-col gap-1">
                <div class="text-sm font-medium text-foreground/80 line-clamp-2" :title="item.context_message.content">
                  {{ truncate(item.context_message.content, 80) }}
                </div>
              </div>
              <div v-else class="text-sm text-muted-foreground italic">
                (No context found)
              </div>
            </TableCell>
            <TableCell>
              <div class="line-clamp-2 text-sm text-muted-foreground" :title="item.content">
                {{ truncate(item.content, 120) }}
              </div>
            </TableCell>
            <TableCell class="text-sm text-muted-foreground">
              {{ formatDate(item.created_at) }}
            </TableCell>
            <TableCell>
              <Button variant="ghost" size="sm" @click="openDetails(item)">
                View
              </Button>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>

    <!-- Pagination -->
    <div class="flex items-center justify-end gap-2" v-if="data?.total > size">
      <Button
        variant="outline"
        size="sm"
        :disabled="page <= 1"
        @click="page--"
      >
        Previous
      </Button>
      <div class="text-sm font-medium">Page {{ page }} of {{ Math.ceil((data?.total || 0) / size) }}</div>
      <Button
        variant="outline"
        size="sm"
        :disabled="page >= Math.ceil((data?.total || 0) / size)"
        @click="page++"
      >
        Next
      </Button>
    </div>

    <!-- Details Sheet -->
    <Sheet v-model:open="detailsOpen">
      <SheetContent class="sm:max-w-2xl overflow-y-auto">
        <SheetHeader class="mb-6">
          <SheetTitle>Feedback Details</SheetTitle>
          <SheetDescription>
            <div class="flex items-center gap-2 mt-2">
              <span class="font-medium text-foreground">Assistant:</span> {{ selectedMessage?.assistant_name }}
              <span class="mx-2">•</span>
              <span class="font-medium text-foreground">User:</span> {{ selectedMessage?.user_email || 'Anonymous' }}
            </div>
            <div class="flex items-center gap-2 mt-1">
              <span class="font-medium text-foreground">Time:</span> {{ selectedMessage ? formatDate(selectedMessage.created_at) : '' }}
              <span class="mx-2">•</span>
              <span 
                class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
                :class="selectedMessage?.feedback === 'dislike' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'"
              >
                <component :is="selectedMessage?.feedback === 'dislike' ? ThumbsDown : ThumbsUp" class="w-3 h-3" />
                {{ selectedMessage?.feedback === 'dislike' ? 'Needs Improvement' : 'Positive' }}
              </span>
            </div>
          </SheetDescription>
        </SheetHeader>

        <div v-if="selectedMessage" class="space-y-6">
          <!-- Context Message (User) -->
          <div v-if="selectedMessage.context_message" class="space-y-2">
            <h3 class="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <MessageSquare class="w-4 h-4" />
              User Query
            </h3>
            <div class="bg-muted/50 p-4 rounded-lg text-sm whitespace-pre-wrap">
              {{ selectedMessage.context_message.content }}
            </div>
          </div>
          <div v-else class="flex items-center gap-2 text-amber-600 dark:text-amber-500 text-sm bg-amber-50 dark:bg-amber-950/20 p-3 rounded-md">
            <AlertCircle class="w-4 h-4" />
            No context message could be found for this conversation turn.
          </div>

          <!-- Divider with Arrow -->
          <div class="flex justify-center">
            <ArrowRight class="w-5 h-5 text-muted-foreground/30 rotate-90" />
          </div>

          <!-- Assistant Response -->
          <div class="space-y-2">
            <h3 class="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <div class="w-4 h-4 rounded-full bg-primary/20 flex items-center justify-center text-[10px] font-bold text-primary">AI</div>
              Assistant Response
            </h3>
            <div 
              class="prose prose-sm dark:prose-invert max-w-none border rounded-lg p-4 bg-background"
              v-html="renderMarkdown(selectedMessage.content)"
            ></div>
          </div>
          
          <!-- Metadata -->
          <div v-if="selectedMessage.extra_data && Object.keys(selectedMessage.extra_data).length" class="space-y-2 pt-4 border-t">
            <h3 class="text-xs font-medium text-muted-foreground uppercase tracking-wider">Debug Metadata</h3>
            <pre class="bg-gray-950 text-gray-50 p-3 rounded-md text-xs overflow-x-auto">{{ JSON.stringify(selectedMessage.extra_data, null, 2) }}</pre>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  </div>
</template>
