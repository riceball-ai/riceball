<script setup lang="ts">
const defaultOpen = useCookie<boolean>('sidebar_state')

const route = useRoute()
const { t } = useI18n()

const breadcrumbs = computed(() => {
  const segments = route.path.split('/').filter(Boolean)
  const paths = segments.map((_, idx) => '/' + segments.slice(0, idx + 1).join('/'))

  return paths
    .map(path => {
      const routeRecord = findMatchingRoute(path)
      if (!routeRecord) return null

      const name = routeRecord.meta?.breadcrumb || routeRecord.meta?.name || routeRecord.name || path

      return {
        name: typeof name === 'string' ? t(name) : name,
        path
      }
    })
    .filter(Boolean)
})

</script>

<template>
  <SidebarProvider :default-open>
    <AdminSidebar />
    <SidebarInset class="min-h-screen min-w-0">
      <header class="flex h-16 shrink-0 items-center gap-2 border-b">
        <div class="flex items-center gap-2 px-3">
          <SidebarTrigger />
          <Separator orientation="vertical" class="mr-2 h-4" />
          <Breadcrumb>
            <BreadcrumbList>
              <template v-for="(breadcrumb, index) in breadcrumbs" :key="breadcrumb.path">
                <BreadcrumbItem>
                  <NuxtLink v-if="index < breadcrumbs.length - 1" :to="breadcrumb.path">
                    {{ breadcrumb.name }}
                  </NuxtLink>
                  <BreadcrumbPage v-else>
                    {{ breadcrumb.name }}
                  </BreadcrumbPage>
                </BreadcrumbItem>
                <BreadcrumbSeparator v-if="index < breadcrumbs.length - 1" />
              </template>
            </BreadcrumbList>
          </Breadcrumb>
        </div>
      </header>
      <div class="flex flex-1 flex-col gap-4 p-4 w-full overflow-x-hidden">
        <slot />
      </div>
    </SidebarInset>
  </SidebarProvider>
</template>

<style scoped></style>
