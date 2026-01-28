<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'
import cronstrue from 'cronstrue/i18n'
import { Label } from '~/components/ui/label'
import { Input } from '~/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '~/components/ui/select'
import { ToggleGroup, ToggleGroupItem } from '~/components/ui/toggle-group'
import { Separator } from '~/components/ui/separator'

const { t, locale } = useI18n()

const props = defineProps<{
  modelValue: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const frequencies = computed(() => [
  { value: 'once', label: t('components.cron.once') },
  { value: 'daily', label: t('components.cron.daily') },
  { value: 'weekly', label: t('components.cron.weekly') },
  { value: 'monthly', label: t('components.cron.monthly') },
  { value: 'yearly', label: t('components.cron.yearly') },
  { value: 'custom', label: t('components.cron.custom') },
])

const weekDayOptions = computed(() => [
  { value: '1', label: t('components.cron.days.mon') },
  { value: '2', label: t('components.cron.days.tue') },
  { value: '3', label: t('components.cron.days.wed') },
  { value: '4', label: t('components.cron.days.thu') },
  { value: '5', label: t('components.cron.days.fri') },
  { value: '6', label: t('components.cron.days.sat') },
  { value: '0', label: t('components.cron.days.sun') },
])

const months = computed(() => [
  { value: '1', label: t('components.cron.months.jan') },
  { value: '2', label: t('components.cron.months.feb') },
  { value: '3', label: t('components.cron.months.mar') },
  { value: '4', label: t('components.cron.months.apr') },
  { value: '5', label: t('components.cron.months.may') },
  { value: '6', label: t('components.cron.months.jun') },
  { value: '7', label: t('components.cron.months.jul') },
  { value: '8', label: t('components.cron.months.aug') },
  { value: '9', label: t('components.cron.months.sep') },
  { value: '10', label: t('components.cron.months.oct') },
  { value: '11', label: t('components.cron.months.nov') },
  { value: '12', label: t('components.cron.months.dec') },
])

// Internal State
const frequency = ref('daily')
const time = ref('09:00')
const onceDate = ref('') 
const selectedWeekDays = ref<string[]>(['1']) // Monday default
const selectedMonthDay = ref('1')
const selectedMonth = ref('1')
const customExpression = ref(props.modelValue || '* * * * *')

// Helper: Parse Cron to State
const parseCron = (cron: string) => {
  if (!cron) return

  // Handle Special ONCE Format
  if (cron.startsWith('ONCE:')) {
      frequency.value = 'once'
      const isoStr = cron.replace('ONCE:', '')
      const d = new Date(isoStr)
      if (!isNaN(d.getTime())) {
          // Input type=date needs YYYY-MM-DD
          onceDate.value = d.toISOString().split('T')[0]
          // Input type=time needs HH:MM
          padTime(d.getHours().toString(), d.getMinutes().toString())
      }
      return
  }

  const parts = cron.trim().split(/\s+/)
  if (parts.length !== 5) {
    frequency.value = 'custom'
    customExpression.value = cron
    return
  }

  const [min, hour, dom, mon, dow] = parts

  // Check Daily: m h * * *
  if (dom === '*' && mon === '*' && dow === '*') {
    frequency.value = 'daily'
    padTime(hour, min)
    return
  }

  // Check Weekly: m h * * dow
  if (dom === '*' && mon === '*' && dow !== '*') {
    frequency.value = 'weekly'
    padTime(hour, min)
    selectedWeekDays.value = dow.split(',')
    return
  }

  // Check Monthly: m h dom * *
  if (dom !== '*' && mon === '*' && dow === '*') {
    frequency.value = 'monthly'
    padTime(hour, min)
    selectedMonthDay.value = dom
    return
  }

  // Check Yearly: m h dom mon *
  if (dom !== '*' && mon !== '*' && dow === '*') {
    frequency.value = 'yearly'
    padTime(hour, min)
    selectedMonthDay.value = dom
    selectedMonth.value = mon
    return
  }

  // Fallback to custom
  frequency.value = 'custom'
  customExpression.value = cron
}

const padTime = (h: string, m: string) => {
    // Basic zero padding check, input type=time expects HH:MM
    const hh = h.padStart(2, '0')
    const mm = m.padStart(2, '0')
    time.value = `${hh}:${mm}`
}

// Helper: Generate Cron from State
const generateCron = (): string => {
  if (frequency.value === 'custom') return customExpression.value

  const [h, m] = time.value.split(':').map(Number)
  const minute = m.toString()
  const hour = h.toString()

  if (frequency.value === 'once') {
      if (!onceDate.value) return ''
      return `ONCE:${onceDate.value}T${time.value}:00`
  }

  if (frequency.value === 'daily') {
    return `${minute} ${hour} * * *`
  }

  if (frequency.value === 'weekly') {
    const dow = selectedWeekDays.value.length > 0 ? selectedWeekDays.value.join(',') : '*'
    return `${minute} ${hour} * * ${dow}`
  }

  if (frequency.value === 'monthly') {
    return `${minute} ${hour} ${selectedMonthDay.value} * *`
  }

  if (frequency.value === 'yearly') {
    return `${minute} ${hour} ${selectedMonthDay.value} ${selectedMonth.value} *`
  }

  return '* * * * *'
}

// Watchers
watch(() => props.modelValue, (newVal) => {
  // Only parse if the generated value is different (avoid loop)
  // Or just parse once on mount and rely on internal state?
  // User might type in parent? No, usually controlled by this.
  // We can parse if it's drastically different or on init.
  // For simplicity, let's parse if it doesn't match current generated.
  if (newVal !== generateCron()) {
      parseCron(newVal)
  }
}, { immediate: true })

// Update parent when state changes
watch([frequency, time, selectedWeekDays, selectedMonthDay, selectedMonth, customExpression], () => {
    const newVal = generateCron()
    emit('update:modelValue', newVal)
})

const readableCron = computed(() => {
    try {
        const c = generateCron()
        if(!c) return ''

        if (c.startsWith('ONCE:')) {
            const dateStr = c.replace('ONCE:', '')
            return new Date(dateStr).toLocaleString(locale.value)
        }

        // Map locale from nuxt i18n to cronstrue locale
        const l = locale.value === 'zh' || locale.value === 'zh-Hans' ? 'zh_CN' : 'en'
        return cronstrue.toString(c, { locale: l })
    } catch (e) {
        return t('components.cron.invalid')
    }
})

// Update parent when state changes
watch([frequency, time, onceDate, selectedWeekDays, selectedMonthDay, selectedMonth, customExpression], () => {
    const newVal = generateCron()
    emit('update:modelValue', newVal)
})
</script>

<template>
  <div class="space-y-4 rounded-md border p-4">
    <div class="flex flex-col gap-4">
        <!-- Frequency -->
        <div class="grid grid-cols-4 items-center gap-4">
            <Label class="text-right">{{ $t('components.cron.frequency') }}</Label>
            <Select v-model="frequency">
                <SelectTrigger class="col-span-3">
                    <SelectValue :placeholder="$t('components.cron.selectFrequency')" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem v-for="f in frequencies" :key="f.value" :value="f.value">
                        {{ f.label }}
                    </SelectItem>
                </SelectContent>
            </Select>
        </div>

         <Separator class="my-2" />

        <!-- Logic for Daily/Weekly/Monthly/Yearly -->
        <template v-if="frequency !== 'custom'">
             <!-- Once: Date Selection -->
             <div v-if="frequency === 'once'" class="grid grid-cols-4 items-center gap-4">
                <Label class="text-right">{{ $t('components.cron.date') }}</Label>
                <div class="col-span-3">
                    <input
                        type="date"
                        v-model="onceDate"
                        class="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                    />
                </div>
            </div>

            <!-- Time Selection -->
            <div class="grid grid-cols-4 items-center gap-4">
                <Label class="text-right">{{ $t('components.cron.time') }}</Label>
                <div class="col-span-3">
                    <input
                        type="time"
                        v-model="time"
                        class="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                    />
                </div>
            </div>

            <!-- Weekly: Week Days -->
            <div v-if="frequency === 'weekly'" class="grid grid-cols-4 items-start gap-4">
                 <Label class="text-right pt-2">{{ $t('components.cron.onDays') }}</Label>
                 <div class="col-span-3">
                     <ToggleGroup v-model="selectedWeekDays" type="multiple" variant="outline" class="justify-start flex-wrap">
                         <ToggleGroupItem v-for="day in weekDayOptions" :key="day.value" :value="day.value" class="h-8 w-8 p-0" :title="day.label">
                             {{ day.label.slice(0, 1) }}
                         </ToggleGroupItem>
                     </ToggleGroup>
                 </div>
            </div>

            <!-- Monthly: Day of Month -->
            <div v-if="frequency === 'monthly' || frequency === 'yearly'" class="grid grid-cols-4 items-center gap-4">
                 <Label class="text-right">{{ $t('components.cron.onDay') }}</Label>
                 <div class="col-span-3 flex items-center gap-2">
                     <Input type="number" min="1" max="31" v-model="selectedMonthDay" class="w-20" />
                     <span class="text-sm text-muted-foreground">{{ $t('components.cron.ofTheMonth') }}</span>
                 </div>
            </div>

             <!-- Yearly: Month -->
             <div v-if="frequency === 'yearly'" class="grid grid-cols-4 items-center gap-4">
                 <Label class="text-right">{{ $t('components.cron.inMonth') }}</Label>
                 <div class="col-span-3">
                     <Select v-model="selectedMonth">
                        <SelectTrigger>
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem v-for="m in months" :key="m.value" :value="m.value">
                                {{ m.label }}
                            </SelectItem>
                        </SelectContent>
                     </Select>
                 </div>
            </div>
        </template>

        <!-- Custom Input -->
        <div v-if="frequency === 'custom'" class="grid grid-cols-4 items-center gap-4">
            <Label class="text-right">{{ $t('components.cron.expression') }}</Label>
            <Input v-model="customExpression" class="col-span-3" placeholder="* * * * *" />
        </div>

        <!-- Preview -->
        <div class="grid grid-cols-4 gap-4">
             <div class="col-span-1"></div>
             <div class="col-span-3 text-sm text-muted-foreground bg-muted/50 p-2 rounded">
                 {{ readableCron }}
             </div>
        </div>
    </div>
  </div>
</template>
