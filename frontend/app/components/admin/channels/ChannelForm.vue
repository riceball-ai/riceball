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
  provider: z.enum(['telegram', 'wecom', 'discord', 'slack']),
  is_active: z.boolean().default(true),
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
      credentials: props.initialData.credentials || {},
      settings: props.initialData.settings || {},
    }
  }
  return {
    name: '',
    provider: 'telegram' as ChannelProvider,
    is_active: true,
    credentials: {},
    settings: {},
  }
}

const onSubmit = (values: any) => {
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
                <SelectItem value="wecom">WeCom (企业微信)</SelectItem>
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
                    <Switch :checked="value" @update:checked="handleChange" />
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

      <!-- WeCom Credentials -->
      <div v-if="values.provider === 'wecom'" class="space-y-4 border-t pt-4">
         <h4 class="text-sm font-semibold">WeCom Configuration</h4>
         
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
                            <Button type="button" variant="outline" size="icon" @click="setFieldValue('credentials.token', generateRandomSecret('token', 16))">
                                <Loader2 class="h-4 w-4" /> <!-- Using loader as refresh icon placeholder -->
                            </Button>
                        </div>
                    </FormControl>
                    <FormMessage />
                </FormItem>
            </FormField>

            <FormField v-slot="{ componentField }" name="credentials.aes_key">
                <FormItem>
                    <FormLabel>{{ t('channels.form.wecom.aes_key') }}</FormLabel>
                    <FormControl>
                         <div class="flex gap-2">
                             <Input v-bind="componentField" />
                             <Button type="button" variant="outline" size="icon" @click="setFieldValue('credentials.aes_key', generateRandomSecret('aes', 43))">
                                <Loader2 class="h-4 w-4" />
                            </Button>
                         </div>
                    </FormControl>
                    <FormMessage />
                </FormItem>
            </FormField>
         </div>
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
