<script setup lang="ts">
import type { HTMLAttributes } from "vue"
import type { Assistant } from "~/types/api";
interface Props {
  assistant: Partial<Assistant> | null,
  class?: HTMLAttributes["class"]
}

const props = withDefaults(defineProps<Props>(), {})
</script>


<template>
  <Avatar :class="class">
    <AvatarImage :src="assistant?.avatar_url || ''" :alt="assistant?.name || ''" />
    <AvatarFallback>
      {{ assistant?.name?.charAt(0)?.toUpperCase() || '?' }}
    </AvatarFallback>
  </Avatar>
</template>