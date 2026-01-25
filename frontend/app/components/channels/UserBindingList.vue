<script setup lang="ts">
import { ref } from 'vue'
import { Trash2, Smartphone, MessageSquare } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import type { UserChannelBinding } from '~/types/channels'
import { Button } from '~/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '~/components/ui/table'
import { Badge } from '~/components/ui/badge'

const { t } = useI18n()
const { $api } = useNuxtApp()

const { data: bindings, refresh } = await useAPI<UserChannelBinding[]>('/api/v1/channel-bindings/')
const isLoading = ref(false)

const handleUnbind = async (id: string) => {
    if (!confirm(t('channels.confirmUnbind'))) return
    
    try {
        isLoading.value = true
        await $api(`/api/v1/channel-bindings/${id}`, { method: 'DELETE' })
        toast.success(t('common.success'), { description: t('channels.unbound') })
        refresh()
    } catch (e: any) {
        toast.error(t('common.error'), { description: e.message })
    } finally {
        isLoading.value = false
    }
}

const getProviderIcon = (provider: string) => {
    if (provider === 'telegram') return Smartphone
    if (provider === 'wecom') return MessageSquare
    return Smartphone
}
</script>

<template>
  <div class="space-y-6">
    <div>
       <h3 class="text-lg font-medium">{{ $t('channels.myBindings') }}</h3>
       <p class="text-sm text-muted-foreground">{{ $t('channels.description') }}</p>
    </div>

    <div v-if="!bindings || bindings.length === 0" class="rounded-md border border-dashed p-8 text-center">
        <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-muted">
            <Smartphone class="h-6 w-6 text-muted-foreground" />
        </div>
        <h3 class="mt-2 text-sm font-semibold">{{ $t('channels.noBindings') }}</h3>
        <p class="mt-1 text-sm text-muted-foreground">{{ $t('channels.howToBind') }}</p>
    </div>

    <div v-else class="rounded-md border">
      <Table>
        <TableHeader>
           <TableRow>
              <TableHead>{{ $t('channels.provider') }}</TableHead>
              <TableHead>{{ $t('channels.externalUser') }}</TableHead>
              <TableHead>{{ $t('channels.metadata') }}</TableHead>
              <TableHead class="text-right">{{ $t('common.actions') }}</TableHead>
           </TableRow>
        </TableHeader>
        <TableBody>
            <TableRow v-for="binding in bindings" :key="binding.id">
                <TableCell>
                    <div class="flex items-center gap-2">
                         <component :is="getProviderIcon(binding.provider)" class="h-4 w-4" />
                         <span class="capitalize">{{ binding.provider }}</span>
                    </div>
                </TableCell>
                <TableCell class="font-mono text-xs">{{ binding.external_user_id }}</TableCell>
                <TableCell>
                     <div class="flex flex-wrap gap-1">
                         <Badge v-for="(v, k) in binding.metadata" :key="k" variant="secondary" class="text-[10px]">
                             {{ k }}: {{ v }}
                         </Badge>
                     </div>
                </TableCell>
                <TableCell class="text-right">
                    <Button variant="ghost" size="icon" class="text-destructive" @click="handleUnbind(binding.id)" :disabled="isLoading">
                        <Trash2 class="h-4 w-4" />
                    </Button>
                </TableCell>
            </TableRow>
        </TableBody>
      </Table>
    </div>
  </div>
</template>
