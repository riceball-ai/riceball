<script setup lang="ts">
import type { Assistant } from '~/types/api';

interface Props {
  assistant?: Assistant | null
  showWelcome?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showWelcome: true
})
</script>

<template>
  <div v-if="showWelcome" class="text-center">
    <div class="mb-4">
      <div class="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto">
        <Avatar class="w-12 h-12">
          <AvatarImage :src="assistant?.avatar_url || ''" :alt="assistant?.name" />
          <AvatarFallback>
            {{ assistant?.name?.charAt(0).toUpperCase() }}
          </AvatarFallback>
        </Avatar>
      </div>
    </div>
    <h3 class="text-lg font-semibold mb-2">{{ assistant?.name }}</h3>
    <p class="text-muted-foreground max-w-md mx-auto">
      {{ assistant?.description || '' }}
    </p>
  </div>
</template>
