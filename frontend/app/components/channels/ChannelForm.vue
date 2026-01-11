<script setup lang="ts">
import { ref, watch, onMounted } from "vue"
import { v4 as uuidv4 } from "uuid"
import { toTypedSchema } from "@vee-validate/zod"
import { useForm } from "vee-validate"
import * as z from "zod"
import { toast } from "vue-sonner"
import { useClipboard } from "@vueuse/core"
import { Copy } from "lucide-vue-next"
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogFooter, 
  DialogHeader, 
  DialogTitle 
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { ChannelProvider, useChannels, type ChannelCreate, type Channel } from "~/composables/useChannels"

const props = defineProps<{
  assistantId: string
  open: boolean
  channelToEdit?: Channel | null
}>()

const emit = defineEmits(["update:open", "success"])

const { t } = useI18n()
const { createChannel, updateChannel } = useChannels()
const { copy } = useClipboard()

const loading = ref(false)

const providers = [
  { value: ChannelProvider.TELEGRAM, label: "Telegram" },
  { value: ChannelProvider.WECOM, label: "WeCom (企业微信)" },
  // { value: ChannelProvider.DISCORD, label: "Discord" },
]

// Form Schema
const formSchema = z.object({
  name: z.string().min(1, t("common.required")),
  provider: z.nativeEnum(ChannelProvider),
  // Telegram
  bot_token: z.string().optional(),
  // WeCom
  corp_id: z.string().optional(),
  agent_id: z.string().optional(),
  secret: z.string().optional(),
  token: z.string().optional(),
  aes_key: z.string().optional(),
  // Common
  is_active: z.boolean().default(true)
})

const { handleSubmit, values, setFieldValue, resetForm, errors, defineField } = useForm({
  validationSchema: toTypedSchema(formSchema),
  initialValues: {
    name: "",
    provider: ChannelProvider.TELEGRAM,
    is_active: true
  }
})

const [name] = defineField("name")
const [bot_token] = defineField("bot_token")
const [corp_id] = defineField("corp_id")
const [agent_id] = defineField("agent_id")
const [secret] = defineField("secret")
const [token] = defineField("token")
const [aes_key] = defineField("aes_key")
// Explicit for checkbox to bind boolean
// However, shadcn checkbox often works differently, may need handleChange
// But defineField usually works with standard v-model
// Let's verify how it's used.
// For select, we used :model-value and setFieldValue manual handling, so no change needed there
// For Input, we used v-model="values.name" -> v-model="name"

// Auto-fill random tokens for WeCom
const generateWeComSecrets = () => {
    if(!values.token) setFieldValue("token", uuidv4().replace(/-/g, "").substring(0, 16))
    if(!values.aes_key) {
        // WeCom requires AES-256 (32 bytes) encoded in Base64 (44 chars) with padding removed (43 chars)
        const array = new Uint8Array(32);
        window.crypto.getRandomValues(array);
        let binaryString = "";
        for (let i = 0; i < array.length; i++) {
            binaryString += String.fromCharCode(array[i]);
        }
        const base64 = window.btoa(binaryString);
        setFieldValue("aes_key", base64.replace(/=+$/, ''))
    }
}

// Computed Webhook URL
const getWebhookUrl = () => {
    if (!props.channelToEdit) return ""
    const baseUrl = typeof window !== "undefined" ? window.location.origin : ""
    return `${baseUrl}/api/v1/channels/webhook/${props.channelToEdit.id}`
}

const copyWebhook = () => {
    const url = getWebhookUrl()
    if(url) {
        copy(url)
        toast.success(t('assistants.channels.webhook_copied'))
    }
}

watch(() => props.open, (isOpen) => {
  if (isOpen) {
    if (props.channelToEdit) {
      setFieldValue("name", props.channelToEdit.name)
      setFieldValue("provider", props.channelToEdit.provider)
      setFieldValue("is_active", props.channelToEdit.is_active)
      
      // Populate credentials
      const creds = props.channelToEdit.credentials || {}
      if (props.channelToEdit.provider === ChannelProvider.TELEGRAM) {
          setFieldValue("bot_token", creds.bot_token || "")
      } else if (props.channelToEdit.provider === ChannelProvider.WECOM) {
          setFieldValue("corp_id", creds.corp_id || "")
          setFieldValue("agent_id", creds.agent_id || "")
          setFieldValue("secret", creds.secret || "")
          setFieldValue("token", creds.token || "")
          setFieldValue("aes_key", creds.aes_key || "")
      }
    } else {
      resetForm()
      setFieldValue("name", "")
      setFieldValue("provider", ChannelProvider.TELEGRAM)
    }
  }
})

const onSubmit = handleSubmit(async (values) => {
  loading.value = true
  try {
    const commonSettings = {
        // any extra settings
    }
    
    let credentials: any = {}
    if (values.provider === ChannelProvider.TELEGRAM) {
        credentials = { bot_token: values.bot_token }
    } else if (values.provider === ChannelProvider.WECOM) {
        credentials = {
            corp_id: values.corp_id,
            agent_id: values.agent_id,
            secret: values.secret,
            token: values.token,
            aes_key: values.aes_key
        }
    }

    if (props.channelToEdit) {
        await updateChannel(props.channelToEdit.id, {
            name: values.name,
            credentials,
            is_active: values.is_active,
        })
    } else {
        await createChannel({
            assistant_id: props.assistantId,
            name: values.name,
            provider: values.provider,
            credentials,
            is_active: values.is_active,
            settings: commonSettings
        })
    }
    
    toast.success(props.channelToEdit ? t("common.updated") : t("common.created"))
    emit("success")
    emit("update:open", false)
  } catch (error) {
    console.error(error)
    toast.error(t('assistants.channels.form.error_failed'))
  } finally {
    loading.value = false
  }
})

</script>

<template>
  <Dialog :open="open" @update:open="(val) => emit('update:open', val)">
    <DialogContent class="sm:max-w-[500px]">
      <DialogHeader>
        <DialogTitle>{{ channelToEdit ? t('assistants.channels.form.edit_title') : t('assistants.channels.form.add_title') }}</DialogTitle>
        <DialogDescription>
          {{ t('assistants.channels.form.description') }}
        </DialogDescription>
      </DialogHeader>

      <form @submit="onSubmit" class="space-y-4">
        
        <!-- Provider Selection -->
        <div class="space-y-2">
            <Label>{{ t('assistants.channels.form.platform') }}</Label>
            <Select 
                :model-value="values.provider" 
                @update:model-value="(val) => setFieldValue('provider', val as any)"
                :disabled="!!channelToEdit"
            >
                <SelectTrigger>
                    <SelectValue :placeholder="t('assistants.channels.form.select_provider')" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem v-for="p in providers" :key="p.value" :value="p.value">
                        {{ p.label }}
                    </SelectItem>
                </SelectContent>
            </Select>
        </div>

        <!-- Common: Name -->
        <div class="space-y-2">
            <Label>{{ t('assistants.channels.form.name') }}</Label>
            <Input v-model="name" placeholder="e.g., Customer Support Bot" />
            <span class="text-xs text-red-500">{{ errors.name }}</span>
        </div>

        <!-- TELEGRAM Fields -->
        <div v-if="values.provider === ChannelProvider.TELEGRAM" class="space-y-4 p-4 border rounded-md bg-slate-50 dark:bg-slate-900">
            <div class="space-y-2">
                <Label>{{ t('assistants.channels.form.telegram.bot_token') }}</Label>
                <Input v-model="bot_token" type="password" placeholder="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11" />
                <p class="text-xs text-muted-foreground">{{ t('assistants.channels.form.telegram.bot_token_hint') }}</p>
            </div>
        </div>

        <!-- WECOM Fields -->
         <div v-if="values.provider === ChannelProvider.WECOM" class="space-y-4 p-4 border rounded-md bg-slate-50 dark:bg-slate-900">
            <div class="grid grid-cols-2 gap-4">
                <div class="space-y-2">
                    <Label>{{ t('assistants.channels.form.wecom.corp_id') }}</Label>
                    <Input v-model="corp_id" />
                </div>
                <div class="space-y-2">
                    <Label>{{ t('assistants.channels.form.wecom.agent_id') }}</Label>
                    <Input v-model="agent_id" />
                </div>
            </div>
            
            <div class="space-y-2">
                <Label>{{ t('assistants.channels.form.wecom.secret') }}</Label>
                <Input v-model="secret" />
            </div>

            <div class="grid grid-cols-2 gap-4">
                <div class="space-y-2">
                    <Label>{{ t('assistants.channels.form.wecom.token') }}</Label>
                    <Input v-model="token" />
                </div>
                 <div class="space-y-2">
                    <Label>{{ t('assistants.channels.form.wecom.aes_key') }}</Label>
                    <Input v-model="aes_key" />
                </div>
            </div>
             <div class="flex justify-end">
                <Button type="button" variant="outline" size="sm" @click="generateWeComSecrets">{{ t('assistants.channels.form.wecom.generate_random') }}</Button>
            </div>
        </div>

        <!-- Active Status -->
        <div class="flex items-center space-x-2">
            <Checkbox 
                id="is_active" 
                :checked="values.is_active"
                @update:checked="(val: any) => setFieldValue('is_active', val)"
             />
            <Label htmlFor="is_active">{{ t('assistants.channels.form.is_active') }}</Label>
        </div>

        <!-- Webhook URL (Only for existing channels) -->
        <div v-if="channelToEdit" class="space-y-2 p-3 bg-slate-50 dark:bg-slate-900 rounded border">
            <Label class="text-xs text-muted-foreground">{{ t('assistants.channels.form.webhook_url') }}</Label>
            <div class="flex items-center gap-2">
                <Input 
                    :model-value="getWebhookUrl()" 
                    readonly 
                    class="flex-1 min-w-0 bg-white dark:bg-black font-mono text-xs h-9"
                    @click="(e: any) => e.target?.select()" 
                />
                <Button type="button" variant="ghost" size="icon" @click="copyWebhook" class="shrink-0">
                    <Copy class="w-4 h-4" />
                </Button>
            </div>
            <p class="text-[10px] text-muted-foreground">{{ t('assistants.channels.form.webhook_hint') }}</p>
        </div>
        <div v-else class="text-sm text-yellow-600 bg-yellow-50 p-2 rounded dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-900/50">
             {{ t('assistants.channels.form.save_to_get_webhook') }}
        </div>

        <DialogFooter>
          <Button type="submit" :disabled="loading">
            {{ loading ? t('common.processing') : t('common.save') }}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>
