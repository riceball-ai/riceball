<script setup lang="ts">
import type { ScheduledTask, ScheduledTaskExecution } from '~/types/scheduler'
import { RefreshCw } from 'lucide-vue-next'
import { Badge } from '~/components/ui/badge'
import { Button } from '~/components/ui/button'
import { Spinner } from '~/components/ui/spinner'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '~/components/ui/table'

const props = defineProps<{
  task: ScheduledTask
}>()

const { $api } = useNuxtApp()
const executions = ref<ScheduledTaskExecution[]>([])
const loading = ref(false)

const fetchExecutions = async () => {
    loading.value = true
    try {
        const data = await $api<ScheduledTaskExecution[]>(`/api/v1/scheduled-tasks/${props.task.id}/executions`)
        executions.value = data
    } catch (err) {
        console.error("Failed to fetch executions", err)
    } finally {
        loading.value = false
    }
}

onMounted(() => {
    fetchExecutions()
})

defineExpose({ refresh: fetchExecutions })
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h3 class="text-lg font-medium">Execution History</h3>
      <Button variant="outline" size="sm" @click="fetchExecutions" :disabled="loading">
        <Spinner v-if="loading" class="mr-2" />
        <RefreshCw v-else class="mr-2 h-4 w-4" />
        Refresh
      </Button>
    </div>

    <div v-if="loading && executions.length === 0" class="flex justify-center py-8">
        <Spinner class="h-6 w-6 text-muted-foreground" />
    </div>

    <div v-else-if="executions.length === 0" class="text-center py-8 text-muted-foreground">
        No execution history found.
    </div>

    <div v-else class="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Status</TableHead>
            <TableHead>Started At</TableHead>
            <TableHead>Duration</TableHead>
            <TableHead>Details</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="exec in executions" :key="exec.id">
            <TableCell>
              <Badge :variant="exec.status === 'COMPLETED' ? 'default' : exec.status === 'FAILED' ? 'destructive' : 'secondary'">
                {{ exec.status }}
              </Badge>
            </TableCell>
            <TableCell>
              <NuxtTime :datetime="exec.started_at" year="numeric" month="2-digit" day="2-digit" hour="2-digit" minute="2-digit" second="2-digit" />
            </TableCell>
            <TableCell>{{ exec.duration || '-' }}</TableCell>
            <TableCell class="max-w-[300px]">
                <div v-if="exec.error_message" class="text-sm text-destructive truncate" :title="exec.error_message">
                    {{ exec.error_message }}
                </div>
                <div v-else-if="exec.result_summary" class="text-sm text-muted-foreground truncate" :title="exec.result_summary">
                    {{ exec.result_summary }}
                </div>
                <span v-else>-</span>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>
  </div>
</template>
