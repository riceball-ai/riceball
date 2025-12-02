<script setup lang="ts">
import {
  ChevronsUpDown,
  LogOut,
  CircleUser,
  Settings,
} from "lucide-vue-next"
import {
    useSidebar
} from "@/components/ui/sidebar"

const { isMobile } = useSidebar()

const userStore = useUserStore()

const settingsDialogOpen = ref(false)

// Handle user logout
const handleLogout = async () => {
  await userStore.logout()
  await navigateTo('/sign-in')
}

// Open settings dialog
const openSettings = () => {
  settingsDialogOpen.value = true
}
</script>

<template>
  <SidebarMenu>
    <SidebarMenuItem>
      <DropdownMenu>
        <DropdownMenuTrigger as-child>
          <SidebarMenuButton
            size="lg"
            class="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
          >
            <Avatar class="h-8 w-8 rounded-lg">
              <AvatarImage :src="userStore.user?.avatar_url || ''" :alt="$t('nav.avatar')" />
              <AvatarFallback class="rounded-lg">
                <CircleUser />
              </AvatarFallback>
            </Avatar>
            <div class="grid flex-1 text-left text-sm leading-tight">
              <span class="truncate font-medium">{{ userStore.user?.name || $t('nav.mysteriousUser') }}</span>
              <span class="truncate text-xs">{{ userStore.user?.email }}</span>
            </div>
            <ChevronsUpDown class="ml-auto size-4" />
          </SidebarMenuButton>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          class="w-[--reka-dropdown-menu-trigger-width] min-w-56 rounded-lg"
          :side="isMobile ? 'bottom' : 'right'"
          align="end"
          :side-offset="4"
        >
          <DropdownMenuLabel class="p-0 font-normal">
            <div class="flex items-center gap-2 px-1 py-1.5 text-left text-sm">
              <Avatar class="h-8 w-8 rounded-lg">
                <AvatarImage :src="userStore.user?.avatar_url || ''" :alt="$t('nav.avatar')" />
                <AvatarFallback class="rounded-lg">
                  <CircleUser />
                </AvatarFallback>
              </Avatar>
              <div class="grid flex-1 text-left text-sm leading-tight">
                <span class="truncate font-semibold">{{ userStore.user?.name || $t('nav.mysteriousUser')  }}</span>
                <span class="truncate text-xs">{{ userStore.user?.email }}</span>
              </div>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem @click="openSettings">
            <Settings />
            {{ $t('nav.settings') }}
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem @click="handleLogout">
            <LogOut />
            {{ $t('common.logout') }}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </SidebarMenuItem>
  </SidebarMenu>

  <!-- Settings Dialog -->
  <SettingsDialog v-model:open="settingsDialogOpen" />
</template>