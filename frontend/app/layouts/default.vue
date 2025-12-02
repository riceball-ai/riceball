<script setup lang="ts">
const defaultOpen = useCookie<boolean>('sidebar_state')
</script>

<template>
  <SidebarProvider :default-open>
    <AppSidebar />
    <SidebarInset>
      <slot />
    </SidebarInset>
  </SidebarProvider>
</template>

<style scoped></style>
