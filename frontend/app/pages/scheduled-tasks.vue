<script setup lang="ts">
import { ref } from 'vue'
import { Plus, Pencil, Trash2, CalendarClock, Play, History } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import type { ScheduledTask, ScheduledTaskCreate } from '~/types/scheduler'
import type { ChannelConfig } from '~/types/channels'
import type { Assistant } from '~/types/api'

import { Button } from '~/components/ui/button'
import { Input } from '~/components/ui/input'
import { Textarea } from '~/components/ui/textarea'
import { Label } from '~/components/ui/label'
import { Switch } from '~/components/ui/switch'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '~/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '~/components/ui/dialog'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '~/components/ui/sheet'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '~/components/ui/select'
import { Badge } from '~/components/ui/badge'
import TaskHistoryList from '~/components/scheduler/TaskHistoryList.vue'
import CronEditor from '~/components/scheduler/CronEditor.vue'

const { t } = useI18n()
const { $api } = useNuxtApp()

// Fetch Data
const { data: tasks, refresh: refreshTasks } = await useAPI<ScheduledTask[]>('/v1/scheduled-tasks/')
const { data: assistants } = await useAPI<Assistant[]>('/v1/assistants')
const { data: channels } = await useAPI<ChannelConfig[]>('/v1/channels')

// State
const isDialogOpen = ref(false)
const isEditing = ref(false)
const currentId = ref<string | null>(null)
const isLoading = ref(false)
const isHistoryOpen = ref(false)
const selectedTaskForHistory = ref<ScheduledTask | null>(null)

const form = ref<ScheduledTaskCreate>({
  name: '',
  description: '',
  cron_expression: '',
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  assistant_id: '',
  prompt_template: '',
  channel_config_id: '',
  target_identifier: '',
  is_active: true
})

// Methods
const openCreateDialog = () => {
  isEditing.value = false
  currentId.value = null
  form.value = {
    name: '',
    description: '',
    cron_expression: '0 9 * * *',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    assistant_id: assistants.value?.[0]?.id || '',
    prompt_template: '',
    channel_config_id: channels.value?.[0]?.id || '',
    target_identifier: '',
    is_active: true
  }
  isDialogOpen.value = true
}

const openEditDialog = (task: ScheduledTask) => {
  isEditing.value = true
  currentId.value = task.id
  form.value = {
    name: task.name,
    description: task.description || '',
    cron_expression: task.cron_expression,
    timezone: task.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
    assistant_id: task.assistant_id,
    prompt_template: task.prompt_template,
    channel_config_id: task.channel_config_id,
    target_identifier: task.target_identifier,
    is_active: task.is_active
  }
  isDialogOpen.value = true
}

const openHistory = (task: ScheduledTask) => {
  selectedTaskForHistory.value = task
  isHistoryOpen.value = true
}

const onSubmit = async () => {
  if (!form.value.name || !form.value.cron_expression || !form.value.assistant_id || !form.value.channel_config_id || !form.value.prompt_template) {
    toast.error(t('common.error'), { description: t('common.fixValidationErrors') })
    return
  }

  try {
    isLoading.value = true
    if (isEditing.value && currentId.value) {
      await $api(`/api/v1/scheduled-tasks/${currentId.value}`, {
        method: 'PATCH',
        body: form.value
      })
      toast.success(t('common.success'), { description: t('tasks.updated') })
    } else {
      await $api('/api/v1/scheduled-tasks/', {
        method: 'POST',
        body: form.value
      })
      toast.success(t('common.success'), { description: t('tasks.created') })
    }
    isDialogOpen.value = false
    refreshTasks()
  } catch (e: any) {
    toast.error(t('common.error'), { description: e.message || 'Unknown Error' })
  } finally {
    isLoading.value = false
  }
}

const deleteTask = async (id: string) => {
  if (!confirm(t('common.confirmDelete'))) return
  try {
    await $api(`/api/v1/scheduled-tasks/${id}`, { method: 'DELETE' })
    toast.success(t('common.success'), { description: t('tasks.deleted') })
    refreshTasks()
  } catch (e: any) {
    toast.error(t('common.error'), { description: e.message })
  }
}

const getAssistantName = (id: string) => {
  return assistants.value?.find(a => a.id === id)?.name || id
}

const getChannelName = (id: string) => {
  return channels.value?.find(c => c.id === id)?.name || id
}

const formatDate = (dateStr?: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString()
}
</script>

<template>
  <div class="absolute inset-0 flex flex-col overflow-hidden rounded-[inherit]">
    <AppHeader></AppHeader>
    <div class="h-full flex-1 flex-col space-y-8 p-8 md:flex">
      <div class="flex items-center justify-between space-y-2">
        <div>
          <h2 class="text-2xl font-bold tracking-tight">{{ $t('tasks.title') }}</h2>
          <p class="text-muted-foreground">{{ $t('tasks.description') }}</p>
        </div>
        <div class="flex items-center space-x-2">
          <Button @click="openCreateDialog">
            <Plus class="mr-2 h-4 w-4" /> {{ $t('tasks.create') }}
          </Button>
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="!tasks || tasks.length === 0"
        class="flex h-[400px] shrink-0 items-center justify-center rounded-md border border-dashed">
        <div class="mx-auto flex max-w-[420px] flex-col items-center justify-center text-center">
          <div class="flex h-20 w-20 items-center justify-center rounded-full bg-muted">
            <CalendarClock class="h-10 w-10 text-muted-foreground" />
          </div>
          <h3 class="mt-4 text-lg font-semibold">{{ $t('common.noData') }}</h3>
          <p class="mb-4 mt-2 text-sm text-muted-foreground">
            {{ $t('tasks.description') }}
          </p>
          <Button size="sm" @click="openCreateDialog">
            <Plus class="mr-2 h-4 w-4" /> {{ $t('tasks.create') }}
          </Button>
        </div>
      </div>

      <!-- Table -->
      <div v-else class="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{{ $t('tasks.name') }}</TableHead>
              <TableHead>{{ $t('tasks.cron') }}</TableHead>
              <TableHead>{{ $t('tasks.assistant') }}</TableHead>
              <TableHead>{{ $t('tasks.target') }}</TableHead>
              <TableHead>{{ $t('tasks.lastRun') }}</TableHead>
              <TableHead>{{ $t('tasks.status') }}</TableHead>
              <TableHead class="text-right">{{ $t('common.actions') }}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="task in tasks" :key="task.id">
              <TableCell class="font-medium">
                <div class="flex flex-col">
                  <span>{{ task.name }}</span>
                  <span class="text-xs text-muted-foreground truncate max-w-[200px]">{{ task.description }}</span>
                </div>
              </TableCell>
              <TableCell>
                <code class="relative rounded bg-muted px-[0.3rem] py-[0.2rem] font-mono text-sm">
                    {{ task.cron_expression }}
                </code>
              </TableCell>
              <TableCell>{{ getAssistantName(task.assistant_id) }}</TableCell>
              <TableCell>
                <div class="flex flex-col">
                  <span class="font-medium">{{ getChannelName(task.channel_config_id) }}</span>
                  <span class="text-xs text-muted-foreground">{{ task.target_identifier }}</span>
                </div>
              </TableCell>
              <TableCell>{{ formatDate(task.last_run_at) }}</TableCell>
              <TableCell>
                <Badge :variant="task.is_active ? 'default' : 'secondary'">
                  {{ task.is_active ? $t('tasks.active') : $t('tasks.inactive') }}
                </Badge>
              </TableCell>
              <TableCell class="text-right">
                <Button variant="ghost" size="icon" @click="openHistory(task)" :title="$t('tasks.history')">
                  <History class="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="icon" @click="openEditDialog(task)">
                  <Pencil class="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="icon" class="text-destructive" @click="deleteTask(task.id)">
                  <Trash2 class="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>

      <!-- Create/Edit Dialog -->
      <Dialog v-model:open="isDialogOpen">
        <DialogContent class="sm:max-w-[550px]">
          <DialogHeader>
            <DialogTitle>{{ isEditing ? $t('common.edit') : $t('tasks.create') }}</DialogTitle>
            <DialogDescription>
              {{ $t('tasks.description') }}
            </DialogDescription>
          </DialogHeader>

          <div class="grid gap-4 py-4 max-h-[60vh] overflow-y-auto px-1">
            <!-- Name -->
            <div class="grid grid-cols-4 items-center gap-4">
              <Label for="name" class="text-right">{{ $t('tasks.name') }}</Label>
              <Input id="name" v-model="form.name" class="col-span-3" />
            </div>
            <!-- Description -->
            <div class="grid grid-cols-4 items-center gap-4">
              <Label for="description" class="text-right">{{ $t('common.description') }}</Label>
              <Input id="description" v-model="form.description" class="col-span-3" />
            </div>

            <!-- Cron -->
            <div class="w-full">
                 <CronEditor v-model="form.cron_expression" />
            </div>

            <!-- Timezone -->
            <div class="grid grid-cols-4 items-center gap-4">
              <Label for="timezone" class="text-right">{{ $t('common.timezone') }}</Label>
              <Input id="timezone" v-model="form.timezone" class="col-span-3" placeholder="UTC" />
            </div>

            <!-- Assistant -->
            <div class="grid grid-cols-4 items-center gap-4">
              <Label for="assistant" class="text-right">{{ $t('tasks.assistant') }}</Label>
              <Select v-model="form.assistant_id">
                <SelectTrigger class="col-span-3">
                  <SelectValue :placeholder="$t('tasks.selectAssistant')" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="a in assistants" :key="a.id" :value="a.id">
                    {{ a.name }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <!-- Channel -->
            <div class="grid grid-cols-4 items-center gap-4">
              <Label for="channel" class="text-right">{{ $t('tasks.channel') }}</Label>
              <div class="col-span-3">
                <Select v-model="form.channel_config_id">
                  <SelectTrigger>
                    <SelectValue :placeholder="$t('tasks.selectChannel')" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem v-for="c in channels" :key="c.id" :value="c.id">
                      {{ c.name }} ({{ c.provider }})
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <!-- Target ID -->
            <div class="grid grid-cols-4 items-center gap-4">
              <Label for="target" class="text-right">{{ $t('tasks.target') }}</Label>
              <Input id="target" v-model="form.target_identifier" class="col-span-3" />
            </div>

            <!-- Prompt -->
            <div class="grid grid-cols-4 items-center gap-4">
              <Label for="prompt" class="text-right">{{ $t('tasks.prompt') }}</Label>
              <Textarea id="prompt" v-model="form.prompt_template" class="col-span-3" />
            </div>

            <!-- Active -->
            <div class="grid grid-cols-4 items-center gap-4">
              <Label class="text-right">{{ $t('tasks.active') }}</Label>
              <Switch :model-value="form.is_active" @update:model-value="(v) => form.is_active = v" />
            </div>
          </div>

          <DialogFooter>
            <Button @click="onSubmit" :disabled="isLoading">
              {{ isLoading ? $t('common.saving') : $t('common.save') }}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <!-- History Sheet -->
      <Sheet v-model:open="isHistoryOpen">
        <SheetContent class="w-[800px] sm:max-w-[800px] overflow-y-auto">
          <SheetHeader>
            <SheetTitle>{{ $t('tasks.historyTitle') }}</SheetTitle>
            <SheetDescription>
              {{ selectedTaskForHistory?.name }}
            </SheetDescription>
          </SheetHeader>
          <div class="py-4" v-if="selectedTaskForHistory">
            <TaskHistoryList :task="selectedTaskForHistory" />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  </div>

</template>
