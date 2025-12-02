<script setup lang="ts">
</script>

<template>
  <header class="bg-background inset-x-0 top-0 isolate z-10 flex shrink-0 items-center gap-2">
    <div class="flex h-14 w-full items-center gap-2 px-4">
      <SidebarTrigger class="-ml-1.5" />
      <Separator v-if="$slots.default" orientation="vertical" class="mr-2 data-[orientation=vertical]:h-4" />

      <slot></slot>

      <div class="ml-auto flex items-center gap-2">
        <slot name="right"></slot>
      </div>
    </div>
  </header>
</template>

<style scoped></style>
