<script setup lang="ts">
import { Languages } from 'lucide-vue-next'

defineOptions({
  ssr: false
})

const { locale, locales, setLocale } = useI18n()

const availableLocales = computed(() => {
  return locales.value as Array<{ code: string; name: string }>
})

const currentLocale = computed({
  get: () => locale.value,
  set: async (value) => {
    await setLocale(value)
  }
})
</script>

<template>
  <div class="flex items-center gap-2">
    <Languages class="size-4 text-muted-foreground" />
    <Select v-model="currentLocale">
      <SelectTrigger class="w-[180px]">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem 
          v-for="loc in availableLocales" 
          :key="loc.code" 
          :value="loc.code"
        >
          {{ loc.name }}
        </SelectItem>
      </SelectContent>
    </Select>
  </div>
</template>
