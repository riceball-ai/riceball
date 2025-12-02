<template>
  <Card>
    <CardContent class="legal-content">
      <slot />
    </CardContent>
  </Card>
</template>

<style scoped>
.legal-content :deep(p) {
  margin-bottom: 1rem;
  line-height: 1.8;
}

.legal-content :deep(ul) {
  padding-left: 1.5rem;
  margin-bottom: 1.8rem;
}
</style>