<script setup lang="ts">
import { ref } from 'vue'
import { toTypedSchema } from '@vee-validate/zod'
import * as z from 'zod'
import { v4 as uuidv4 } from 'uuid'
import { Eye, EyeOff, Loader2 } from 'lucide-vue-next'
import { Button } from '~/components/ui/button'
import { Input } from '~/components/ui/input'
import { Label } from '~/components/ui/label'
import { Switch } from '~/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '~/components/ui/select'
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from '~/components/ui/form'
import { Textarea } from '~/components/ui/textarea'

import type { Channel, ChannelProvider } from '~/composables/useChannels'

const { data: assistantsData } = useAPI<any>('/v1/admin/assistants?limit=100') // Fetch assistants for selection
const assistantOptions = computed(() => {
    const list = Array.isArray(assistantsData.value) 
        ? assistantsData.value 
        : (assistantsData.value?.items || [])
    return list.map((a: any) => ({ label: a.name, value: a.id }))
})

const props = defineProps<{
  initialData?: Channel | null
  loading?: boolean
}>()

const emit = defineEmits<{
  submit: [data: Partial<Channel>]
}>()

const { t } = useI18n()

// Show/Hide Secrets
const showSecrets = ref<Record<string, boolean>>({})
const toggleSecret = (key: string) => {
  showSecrets.value[key] = !showSecrets.value[key]
}

const formSchema = toTypedSchema(z.object({
  name: z.string().min(2),
  provider: z.enum(['telegram', 'wecom', 'wecom_smart_bot', 'wecom_webhook', 'discord', 'slack']),
  is_active: z.boolean().default(true),
  assistant_id: z.string().optional().nullable(),
  // Dynamic credentials validation would be better, but z.record(z.any()) is good enough for now
  credentials: z.record(z.any()),
  settings: z.record(z.any()).optional(),
}))

// Helper to init form from props
const getInitialValues = () => {
  if (props.initialData) {
    return {
      name: props.initialData.name,
      provider: props.initialData.provider,
      is_active: props.initialData.is_active,
      assistant_id: props.initialData.assistant_id || 'none', // Use 'none' for select when null
      credentials: props.initialData.credentials || {},
      settings: props.initialData.settings || {},
    }
  }
  return {
    name: '',
    provider: 'telegram' as ChannelProvider,
    is_active: true,
    assistant_id: 'none',
    credentials: {},
    settings: {},
  }
}

const onSubmit = (values: any) => {
    // Handle special "none" value for clearing assistant
    if (values.assistant_id === 'none') {
        values.assistant_id = null
    }

    // If WeCom, perform custom transformation if needed (e.g. ensure empty strings are handled)
    if (values.provider === 'wecom') {
        if (!values.credentials.token) values.credentials.token = uuidv4().replace(/-/g, '')
        if (!values.credentials.aes_key) values.credentials.aes_key = uuidv4().replace(/-/g, '') + 'AESKey' // Mock generator, user should regenerate
    }
    emit('submit', values)
}

const generateRandomSecret = (field: string, length = 32) => {
    // This is just a UI helper, actual generation might vary
    return uuidv4().replace(/-/g, '')
}

</script>

<template>
  <Form v-slot="{ handleSubmit, values, setFieldValue }" :validation-schema="formSchema" :initial-values="getInitialValues()">
    <form @submit="handleSubmit($event, onSubmit)" class="space-y-6">
      
      <!-- Basic Info -->
      <div class="space-y-4">
        <FormField v-slot="{ componentField }" name="name">
          <FormItem>
            <FormLabel>{{ t('channels.form.name') }}</FormLabel>
            <FormControl>
              <Input v-bind="componentField" />
            </FormControl>
            <FormMessage />
          </FormItem>
        </FormField>
        
        <!-- Assistant Selection -->
        <FormField v-slot="{ componentField }" name="assistant_id">
          <FormItem>
            <FormLabel>{{ t('channels.form.assistant') }}</FormLabel>
             <Select v-bind="componentField">
                <FormControl>
                  <SelectTrigger>
                    <SelectValue :placeholder="t('channels.form.select_assistant')" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                   <SelectItem value="none">
                      <span class="text-muted-foreground">{{ t('common.none') }}</span>
                   </SelectItem>
                   <SelectItem v-for="assistant in assistantOptions" :key="assistant.value" :value="assistant.value">
                      {{ assistant.label }}
                   </SelectItem>
                </SelectContent>
              </Select>
            <FormDescription>{{ t('channels.form.assistant_desc') }}</FormDescription>
            <FormMessage />
          </FormItem>
        </FormField>

        <FormField v-slot="{ componentField }" name="provider">
          <FormItem>
            <FormLabel>{{ t('channels.form.platform') }}</FormLabel>
            <Select v-bind="componentField" :disabled="!!initialData">
              <FormControl>
                <SelectTrigger>
                  <SelectValue :placeholder="t('channels.form.select_provider')" />
                </SelectTrigger>
              </FormControl>
              <SelectContent>
                <SelectItem value="telegram">Telegram</SelectItem>
                <SelectItem value="wecom">WeCom App</SelectItem>
                <SelectItem value="wecom_smart_bot">WeCom Smart Bot</SelectItem>
                <SelectItem value="wecom_webhook">WeCom Group Robot</SelectItem>
              </SelectContent>
            </Select>
            <FormMessage />
          </FormItem>
        </FormField>

        <FormField v-slot="{ value, handleChange }" name="is_active">
            <FormItem class="flex flex-row items-center justify-between rounded-lg border p-3 shadow-sm">
                <div class="space-y-0.5">
                    <FormLabel>{{ t('tasks.status') }}</FormLabel>
                    <FormDescription>
                        {{ value ? t('tasks.active') : t('tasks.inactive') }}
                    </FormDescription>
                </div>
                <FormControl>
                    <Switch :model-value="value" @update:model-value="handleChange" />
                </FormControl>
            </FormItem>
        </FormField>
      </div>

      <!-- Telegram Credentials -->
      <div v-if="values.provider === 'telegram'" class="space-y-4 border-t pt-4">
         <h4 class="text-sm font-semibold">Telegram Configuration</h4>
         
         <FormField v-slot="{ componentField }" name="credentials.bot_token">
            <FormItem>
                <FormLabel>{{ t('channels.form.telegram.bot_token') }}</FormLabel>
                <FormControl>
                    <div class="relative">
                        <Input 
                            v-bind="componentField" 
                            :type="showSecrets.bot_token ? 'text' : 'password'" 
                        />
                         <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            class="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                            @click="toggleSecret('bot_token')"
                        >
                            <component :is="showSecrets.bot_token ? EyeOff : Eye" class="h-4 w-4" />
                        </Button>
                    </div>
                </FormControl>
                <FormDescription>{{ t('channels.form.telegram.bot_token_hint') }}</FormDescription>
                <FormMessage />
            </FormItem>
         </FormField>
      </div>

      <!-- WeCom Configuration (Standard App) -->
      <div v-if="values.provider === 'wecom'" class="space-y-4 border-t pt-4">
         <h4 class="text-sm font-semibold">WeCom App Configuration</h4>
         
         <FormField v-slot="{ componentField }" name="credentials.corp_id">
            <FormItem>
                <FormLabel>{{ t('channels.form.wecom.corp_id') }}</FormLabel>
                <FormControl>
                    <Input v-bind="componentField" />
                </FormControl>
                <FormMessage />
            </FormItem>
         </FormField>

         <FormField v-slot="{ componentField }" name="credentials.agent_id">
            <FormItem>
                <FormLabel>{{ t('channels.form.wecom.agent_id') }}</FormLabel>
                <FormControl>
                    <Input v-bind="componentField" />
                </FormControl>
                <FormMessage />
            </FormItem>
         </FormField>

         <FormField v-slot="{ componentField }" name="credentials.secret">
            <FormItem>
                <FormLabel>{{ t('channels.form.wecom.secret') }}</FormLabel>
                <FormControl>
                    <div class="relative">
                        <Input 
                            v-bind="componentField" 
                            :type="showSecrets.wecom_secret ? 'text' : 'password'" 
                        />
                         <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            class="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                            @click="toggleSecret('wecom_secret')"
                        >
                            <component :is="showSecrets.wecom_secret ? EyeOff : Eye" class="h-4 w-4" />
                        </Button>
                    </div>
                </FormControl>
                <FormMessage />
            </FormItem>
         </FormField>
         
         <div class="grid grid-cols-2 gap-4">
            <FormField v-slot="{ componentField }" name="credentials.token">
                <FormItem>
                    <FormLabel>{{ t('channels.form.wecom.token') }}</FormLabel>
                    <FormControl>
                        <div class="flex gap-2">
                             <Input v-bind="componentField" />
                             <!-- Refresh button logic if needed -->
                        </div>
                    </FormControl>
                    <FormDescription>For Webhook Encoding</FormDescription>
                    <FormMessage />
                </FormItem>
            </FormField>

             <FormField v-slot="{ componentField }" name="credentials.encoding_aes_key">
                <FormItem>
                    <FormLabel>{{ t('channels.form.wecom.encoding_aes_key') }}</FormLabel>
                    <FormControl>
                        <div class="flex gap-2">
                            <Input v-bind="componentField" />
                             <Button type="button" variant="outline" size="icon" @click="setFieldValue('credentials.encoding_aes_key', generateRandomSecret('aes', 43))">
                                <Loader2 class="h-4 w-4" />
                            </Button>
                        </div>
                    </FormControl>
                    <FormMessage />
                </FormItem>
            </FormField>
         </div>
      </div>

      <!-- WeCom Smart Bot Configuration -->
      <div v-if="values.provider === 'wecom_smart_bot'" class="space-y-4 border-t pt-4">
         <h4 class="text-sm font-semibold">WeCom Smart Bot Configuration</h4>
         
         <!-- CorpID is optional or required depending on env, let's keep it optional or hidden if auto-detected -->
         <!-- Usually specific Bots don't need CorpID for basic reply, but adapter might use it for construction -->
         
         <div class="grid grid-cols-2 gap-4">
            <FormField v-slot="{ componentField }" name="credentials.token">
                <FormItem>
                    <FormLabel>{{ t('channels.form.wecom.token') }}</FormLabel>
                    <FormControl>
                        <Input v-bind="componentField" />
                    </FormControl>
                    <FormDescription>Webhook Token</FormDescription>
                    <FormMessage />
                </FormItem>
            </FormField>

             <FormField v-slot="{ componentField }" name="credentials.encoding_aes_key">
                <FormItem>
                    <FormLabel>{{ t('channels.form.wecom.encoding_aes_key') }}</FormLabel>
                    <FormControl>
                        <Input v-bind="componentField" />
                    </FormControl>
                    <FormDescription>EncodingAESKey</FormDescription>
                    <FormMessage />
                </FormItem>
            </FormField>
         </div>
      </div>

      <!-- WeCom Webhook Configuration -->
      <div v-if="values.provider === 'wecom_webhook'" class="space-y-4 border-t pt-4">
         <h4 class="text-sm font-semibold">WeCom Group Robot Configuration</h4>
         
         <FormField v-slot="{ componentField }" name="credentials.webhook_url">
            <FormItem>
                <FormLabel>Webhook URL / Key</FormLabel>
                <FormControl>
                    <div class="relative">
                        <Input 
                            v-bind="componentField" 
                            :type="showSecrets.webhook_url ? 'text' : 'password'" 
                            placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send..."
                        />
                         <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            class="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                            @click="toggleSecret('webhook_url')"
                        >
                            <component :is="showSecrets.webhook_url ? EyeOff : Eye" class="h-4 w-4" />
                        </Button>
                    </div>
                </FormControl>
                <FormDescription>
                    Enter the full Webhook URL or just the "key" parameter.
                </FormDescription>
                <FormMessage />
            </FormItem>
         </FormField>
      </div>

      <div class="flex justify-end pt-4">
        <Button type="submit" :disabled="loading">
          <Loader2 v-if="loading" class="mr-2 h-4 w-4 animate-spin" />
          {{ initialData ? t('common.saveChanges') : t('common.create') }}
        </Button>
      </div>
    </form>
  </Form>
</template>
