<script setup lang="ts">
import {
    Bot,
    ArrowLeft,
    Building,
    Brain,
    Database,
    MessageSquare,
    DollarSign,
    Users,
    Key,
    Settings,
    LayoutDashboard,
    Files,
    Shield
} from 'lucide-vue-next'

const route = useRoute()

const runtimeConfig = useRuntimeConfig()
const configStore = useConfigStore()
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
                <div class="grid flex-1 text-left text-sm leading-tight">
                    <span class="truncate font-bold">
                        {{ configStore.config.site_title || runtimeConfig.public.appName }}
                    </span>
                    <span class="truncate text-xs">{{ $t('admin.dashboard') }}</span>
                </div>
            </SidebarMenuButton>
        </SidebarHeader>
        <SidebarContent>
            <SidebarGroup>
                <SidebarGroupContent>
                    <SidebarMenu>
                        <SidebarMenuItem>
                            <SidebarMenuButton as-child :is-active="route.path === '/admin'">
                                <NuxtLink to="/admin">
                                    <LayoutDashboard />
                                    <span>Dashboard</span>
                                </NuxtLink>
                            </SidebarMenuButton>
                        </SidebarMenuItem>
                        <SidebarMenuItem>
                            <SidebarMenuButton as-child :is-active="route.path === '/admin/users'">
                                <NuxtLink to="/admin/users">
                                    <Users />
                                    <span>{{ $t('admin.sidebar.users') }}</span>
                                </NuxtLink>
                            </SidebarMenuButton>
                        </SidebarMenuItem>
                        <SidebarMenuItem>
                            <SidebarMenuButton as-child :is-active="route.path === '/admin/conversations'">
                                <NuxtLink to="/admin/conversations">
                                    <MessageSquare />
                                    <span>{{ $t('admin.sidebar.conversations') }}</span>
                                </NuxtLink>
                            </SidebarMenuButton>
                        </SidebarMenuItem>
                        <SidebarMenuItem>
                            <SidebarMenuButton as-child :is-active="route.path === '/admin/assistants'">
                                <NuxtLink to="/admin/assistants">
                                    <Bot />
                                    <span>{{ $t('admin.sidebar.assistants') }}</span>
                                </NuxtLink>
                            </SidebarMenuButton>
                        </SidebarMenuItem>
                        <SidebarMenuItem>
                            <SidebarMenuButton as-child :is-active="route.path === '/admin/models'">
                                <NuxtLink to="/admin/models">
                                    <Brain />
                                    <span>{{ $t('admin.sidebar.models') }}</span>
                                </NuxtLink>
                            </SidebarMenuButton>
                        </SidebarMenuItem>
                        <SidebarMenuItem>
                            <SidebarMenuButton as-child :is-active="route.path === '/admin/model-providers'">
                                <NuxtLink to="/admin/model-providers">
                                    <Building />
                                    <span>{{ $t('admin.sidebar.modelProviders') }}</span>
                                </NuxtLink>
                            </SidebarMenuButton>
                        </SidebarMenuItem>
                        <SidebarMenuItem>
                            <SidebarMenuButton as-child :is-active="route.path.startsWith('/admin/kbs')">
                                <NuxtLink to="/admin/kbs">
                                    <Database />
                                    <span>{{ $t('admin.sidebar.knowledgeBases') }}</span>
                                </NuxtLink>
                            </SidebarMenuButton>
                        </SidebarMenuItem>
                        <SidebarMenuItem>
                            <SidebarMenuButton as-child :is-active="route.path.startsWith('/admin/files')">
                                <NuxtLink to="/admin/files">
                                    <Files />
                                    <span>{{ $t('admin.sidebar.files') }}</span>
                                </NuxtLink>
                            </SidebarMenuButton>
                        </SidebarMenuItem>
                        <SidebarMenuItem>
                            <SidebarMenuButton as-child :is-active="route.path.startsWith('/admin/oauth-providers')">
                                <NuxtLink to="/admin/oauth-providers">
                                    <Shield />
                                    <span>{{ $t('admin.sidebar.oauthProviders') }}</span>
                                </NuxtLink>
                            </SidebarMenuButton>
                        </SidebarMenuItem>
                        <SidebarMenuItem>
                            <SidebarMenuButton as-child :is-active="route.path.startsWith('/admin/api-keys')">
                                <NuxtLink to="/admin/api-keys">
                                    <Key />
                                    <span>{{ $t('admin.sidebar.apiKeys') }}</span>
                                </NuxtLink>
                            </SidebarMenuButton>
                        </SidebarMenuItem>
                        <SidebarMenuItem>
                            <SidebarMenuButton as-child :is-active="route.path.startsWith('/admin/system-config')">
                                <NuxtLink to="/admin/system-config">
                                    <Settings />
                                    <span>{{ $t('admin.sidebar.systemConfig') }}</span>
                                </NuxtLink>
                            </SidebarMenuButton>
                        </SidebarMenuItem>
                    </SidebarMenu>
                </SidebarGroupContent>
            </SidebarGroup>
        </SidebarContent>
        <SidebarFooter>
            <SidebarMenuItem>
                <SidebarMenuButton as-child>
                    <NuxtLink to="/assistants">
                        <ArrowLeft />
                        <span>{{ $t('admin.sidebar.backToUser') }}</span>
                    </NuxtLink>
                </SidebarMenuButton>
            </SidebarMenuItem>
            <NavUser />
        </SidebarFooter>
        <SidebarRail />
    </Sidebar>
</template>