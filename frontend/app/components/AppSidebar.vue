<script setup lang="ts">
import { computed } from 'vue'
import {
    SquarePen,
    MonitorCog,
    ReceiptText,
    ChevronsRight,
    Gift,
    CalendarClock
} from 'lucide-vue-next'
import { Button } from '~/components/ui/button'
import { useSidebar } from '~/components/ui/sidebar'
// when the route is /chatwith/:id, active the menu item
const route = useRoute()
const isActive = computed(() => {
    return route.path.startsWith('/assistants')
})

const userStore = useUserStore()
const configStore = useConfigStore()
const { state, toggleSidebar } = useSidebar()
const isCollapsed = computed(() => state.value === 'collapsed')

const handleSignIn = () => navigateTo('/sign-in')
const handleSignUp = () => navigateTo('/sign-up')
</script>

<template>
    <Sidebar collapsible="icon">
        <SidebarHeader>
            <SidebarMenuButton size="lg"
                class="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground">
                <div
                    class="flex aspect-square size-8 items-center justify-center rounded-lg text-sidebar-primary-foreground">
                    <img :src="configStore.config.site_logo || '/logo.png'" alt="Logo" />
                </div>
            </SidebarMenuButton>
            <SidebarMenu>
                <SidebarMenuItem>
                    <SidebarMenuButton as-child :is-active="isActive">
                        <NuxtLink to="/assistants">
                            <SquarePen />
                            <span>{{ $t('nav.newChat') }}</span>
                        </NuxtLink>
                    </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                    <SidebarMenuButton as-child>
                        <NuxtLink to="/scheduled-tasks">
                            <CalendarClock />
                            <span>{{ $t('nav.tasks') }}</span>
                        </NuxtLink>
                    </SidebarMenuButton>
                </SidebarMenuItem>
            </SidebarMenu>
        </SidebarHeader>
        <SidebarContent>
            <ClientOnly>
                <NavHistoryList v-if="userStore.user" />
            </ClientOnly>
        </SidebarContent>
        <SidebarFooter>
            <ClientOnly>
                <template v-if="userStore.user">
                    <SidebarMenuItem v-if="userStore.user?.is_superuser">
                        <SidebarMenuButton as-child>
                            <NuxtLink to="/admin">
                                <MonitorCog />
                                <span>{{ $t('nav.adminPanel') }}</span>
                            </NuxtLink>
                        </SidebarMenuButton>
                    </SidebarMenuItem>
                    <NavUser />
                </template>
                <template v-else>
                    <div class="space-y-2 p-2">
                        <Button class="w-full" @click="handleSignIn">
                            {{ $t('auth.signIn') }}
                        </Button>
                        <Button variant="outline" class="w-full" @click="handleSignUp">
                            {{ $t('auth.signUp') }}
                        </Button>
                    </div>
                </template>
            </ClientOnly>
            <div v-if="isCollapsed" class="mt-2 flex justify-center">
                <Button
                    variant="ghost"
                    size="icon"
                    :title="$t('nav.expandSidebar')"
                    @click="toggleSidebar"
                >
                    <ChevronsRight class="size-4" />
                    <span class="sr-only">{{ $t('nav.expandSidebar') }}</span>
                </Button>
            </div>
        </SidebarFooter>
        <SidebarRail />
    </Sidebar>
</template>