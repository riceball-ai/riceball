<script setup lang="ts">
import { Sun, Moon, Monitor } from 'lucide-vue-next'

const colorMode = useColorMode()

const modes = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Monitor },
]

const currentMode = computed({
  get: () => colorMode.preference,
  set: (value) => {
    colorMode.preference = value
  }
})
</script>

<template>
  <div class="flex items-center gap-2">
    <component :is="modes.find(m => m.value === currentMode)?.icon || Monitor" class="size-4 text-muted-foreground" />
    <Select v-model="currentMode">
      <SelectTrigger class="w-[180px]">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem 
          v-for="mode in modes" 
          :key="mode.value" 
          :value="mode.value"
        >
          <div class="flex items-center gap-2">
            <component :is="mode.icon" class="size-4" />
            {{ $t(`settings.colorMode.${mode.value}`) }}
          </div>
        </SelectItem>
      </SelectContent>
    </Select>
  </div>
</template>
