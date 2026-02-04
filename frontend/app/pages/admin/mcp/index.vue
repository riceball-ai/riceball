<script setup lang="ts">
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table'
import { 
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger, 
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import { 
    DownloadCloud, 
    Plug, 
    Trash2, 
    RefreshCcw, 
    Terminal, 
    Globe, 
    CheckCircle2, 
    AlertCircle,
    Server,
    Hammer,
    Plus,
    Pencil
} from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import type { MCPServerConfigResponse, MCPPresetResponse, MCPServerToolsResponse } from '~/types/mcp'
import { MCPServerTypeEnum } from '~/types/mcp'

definePageMeta({
  layout: 'admin',
  breadcrumb: 'admin.mcp.breadcrumb'
})

const { t } = useI18n()
const { listServers, listPresets, installPreset, deleteServer, listTools, updateServer } = useMCP()

// State
const servers = ref<MCPServerConfigResponse[]>([])
const presets = ref<MCPPresetResponse[]>([])
const isLoading = ref(true)
const isInstalling = ref(false)

// Selected Preset for install modal
const selectedPreset = ref<MCPPresetResponse | null>(null)
const installModalOpen = ref(false)
const connectionOverrides = ref('') // JSON string
const addServerModalOpen = ref(false)

// Tools Modal
const toolsModalOpen = ref(false)
const currentServerTools = ref<MCPServerToolsResponse | null>(null)
const isLoadingTools = ref(false)

// Edit Modal
const editModalOpen = ref(false)
const serverToEdit = ref<MCPServerConfigResponse | null>(null)
const editConfig = ref('')
const isUpdating = ref(false)

// Load Data
const loadData = async () => {
  isLoading.value = true
  try {
    const [serversData, presetsData] = await Promise.all([
      listServers(),
      listPresets()
    ])
    servers.value = serversData || []
    presets.value = presetsData || []
  } catch (error) {
    toast.error(t('common.error'))
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  loadData()
})

// Actions
const openInstallModal = (preset: MCPPresetResponse) => {
    selectedPreset.value = preset
    connectionOverrides.value = JSON.stringify(preset.connection_config, null, 2)
    installModalOpen.value = true
}

const handleServerAdded = async () => {
    await loadData()
}

const handleInstall = async () => {
    if (!selectedPreset.value) return
    
    isInstalling.value = true
    try {
        let overrides = {}
        try {
            overrides = JSON.parse(connectionOverrides.value)
        } catch (e) {
            toast.error(t('admin.mcp.error.invalidJson'))
            return
        }
        
        await installPreset(selectedPreset.value.id, overrides)
        toast.success(t('admin.mcp.installSuccess'))
        installModalOpen.value = false
        await loadData()
    } catch (e) {
        toast.error(t('common.error'))
    } finally {
        isInstalling.value = false
    }
}

const handleEdit = (server: MCPServerConfigResponse) => {
    serverToEdit.value = server
    editConfig.value = JSON.stringify(server.connection_config, null, 2)
    editModalOpen.value = true
}

const handleUpdateServer = async () => {
    if (!serverToEdit.value) return
    isUpdating.value = true
    try {
        let config = {}
        try {
            config = JSON.parse(editConfig.value)
        } catch (e) {
            toast.error(t('admin.mcp.error.invalidJson'))
            return
        }

        await updateServer(serverToEdit.value.id, {
            connection_config: config
        })
        toast.success(t('common.success'))
        editModalOpen.value = false
        await loadData()
    } catch (e) {
        toast.error(t('common.error'))
    } finally {
        isUpdating.value = false
    }
}

const handleDelete = async (server: MCPServerConfigResponse) => {
    if (!confirm(t('admin.mcp.deleteConfirm', { name: server.name }))) return
    
    try {
        await deleteServer(server.id)
        toast.success(t('common.success'))
        await loadData()
    } catch (e) {
        toast.error(t('common.error'))
    }
}

const handleViewTools = async (serverName: string) => {
    isLoadingTools.value = true
    currentServerTools.value = null
    toolsModalOpen.value = true
    
    try {
        const tools = await listTools(serverName)
        currentServerTools.value = tools
    } catch (e: any) {
        const msg = e.data?.detail || e.message || t('common.error')
        toast.error(msg)
        // Close modal if failed? Or keep it open to retry?
        // toolsModalOpen.value = false 
    } finally {
        isLoadingTools.value = false
    }
}

const getTypeIcon = (type: MCPServerTypeEnum) => {
    switch (type) {
        case MCPServerTypeEnum.STDIO: return Terminal
        case MCPServerTypeEnum.SSE: return Globe
        default: return Server
    }
}
</script>

<template>
  <div class="space-y-8">
      <!-- Header -->
    <div class="flex justify-between items-center">
      <div>
        <h2 class="text-3xl font-bold tracking-tight">{{ t('admin.mcp.title') }}</h2>
        <p class="text-muted-foreground">
          {{ t('admin.mcp.description') }}
        </p>
      </div>
      <div class="flex gap-2">
        <Button @click="addServerModalOpen = true">
            <Plus class="w-4 h-4 mr-2" />
            {{ t('admin.mcp.custom.add') }}
        </Button>
        <Button variant="outline" @click="loadData" :disabled="isLoading">
            <RefreshCcw class="w-4 h-4 mr-2" :class="{ 'animate-spin': isLoading }" />
            {{ t('common.refresh') }}
        </Button>
      </div>
    </div>

    <!-- Installed Servers -->
    <div>
        <h3 class="text-xl font-semibold mb-4 flex items-center gap-2">
            <CheckCircle2 class="w-5 h-5 text-green-500" />
            {{ t('admin.mcp.installed') }}
        </h3>
        
        <div class="rounded-md border bg-card text-card-foreground shadow-sm">
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead class="w-[250px]">{{ t('admin.mcp.columns.name') }}</TableHead>
                        <TableHead>{{ t('admin.mcp.columns.type') }}</TableHead>
                        <TableHead>{{ t('admin.mcp.connectionType') }}</TableHead>
                        <TableHead class="text-right">{{ t('common.actions') }}</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    <TableRow v-if="isLoading">
                        <TableCell colspan="4" class="h-24 text-center">
                            {{ t('common.loading') }}
                        </TableCell>
                    </TableRow>
                    <TableRow v-else-if="servers.length === 0">
                        <TableCell colspan="4" class="h-24 text-center text-muted-foreground">
                            {{ t('common.noData') }}
                        </TableCell>
                    </TableRow>
                    <TableRow v-for="server in servers" :key="server.id">
                        <TableCell class="font-medium">
                            <div class="flex items-center gap-2">
                                <component :is="getTypeIcon(server.server_type)" class="w-4 h-4 text-muted-foreground" />
                                {{ server.name }}
                            </div>
                            <div class="text-xs text-muted-foreground pl-6 truncate max-w-[300px]" v-if="server.description">
                                {{ server.description }}
                            </div>
                        </TableCell>
                        <TableCell>
                            <Badge variant="outline">{{ server.server_type }}</Badge>
                        </TableCell>
                        <TableCell class="text-xs font-mono">
                            <div v-if="server.server_type === MCPServerTypeEnum.SSE">
                                {{ server.connection_config.url }}
                            </div>
                            <div v-else>
                                {{ server.connection_config.command }} 
                                <span class="text-muted-foreground">{{ (server.connection_config.args || []).join(' ') }}</span>
                            </div>
                        </TableCell>
                        <TableCell class="text-right space-x-2">
                            <Button variant="ghost" size="sm" @click="handleEdit(server)">
                                <Pencil class="w-4 h-4" />
                            </Button>
                            <Button variant="ghost" size="sm" @click="handleViewTools(server.name)">
                                <Hammer class="w-4 h-4 mr-1" />
                                {{ t('admin.mcp.viewTools') }}
                            </Button>
                            <Button variant="destructive" size="sm" @click="handleDelete(server)">
                                <Trash2 class="w-4 h-4" />
                            </Button>
                        </TableCell>
                    </TableRow>
                </TableBody>
            </Table>
        </div>
    </div>

    <!-- Presets -->
    <div>
        <h3 class="text-xl font-semibold mb-4 flex items-center gap-2">
            <DownloadCloud class="w-5 h-5 text-blue-500" />
            {{ t('admin.mcp.presets') }}
        </h3>
        
        <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Card v-for="preset in presets" :key="preset.id" class="flex flex-col">
                <CardHeader>
                    <div class="flex items-center gap-4">
                        <div class="w-10 h-10 rounded bg-secondary flex items-center justify-center overflow-hidden">
                            <img v-if="preset.logo_url" :src="preset.logo_url" class="w-full h-full object-cover" />
                            <Plug v-else class="w-6 h-6 text-muted-foreground" />
                        </div>
                        <div>
                            <CardTitle class="text-base">{{ preset.name }}</CardTitle>
                            <Badge variant="secondary" class="mt-1 text-xs">{{ preset.server_type }}</Badge>
                        </div>
                    </div>
                </CardHeader>
                <CardContent class="flex-1">
                    <CardDescription>
                        {{ preset.description }}
                    </CardDescription>
                </CardContent>
                <CardFooter>
                    <Button class="w-full" @click="openInstallModal(preset)">
                        <DownloadCloud class="w-4 h-4 mr-2" />
                        {{ t('admin.mcp.install') }}
                    </Button>
                </CardFooter>
            </Card>
        </div>
    </div>

    <!-- Install Modal -->
    <Dialog v-model:open="installModalOpen">
        <DialogContent class="sm:max-w-[500px]">
            <DialogHeader>
                <DialogTitle>{{ t('admin.mcp.preset.installTitle', { name: selectedPreset?.name }) }}</DialogTitle>
                <DialogDescription>
                    {{ selectedPreset?.description }}
                </DialogDescription>
            </DialogHeader>
            
            <div class="py-4">
                <Alert v-if="selectedPreset?.server_type === MCPServerTypeEnum.SSE">
                    <AlertCircle class="h-4 w-4" />
                    <AlertTitle>Warning</AlertTitle>
                    <AlertDescription>
                        {{ t('admin.mcp.preset.warning', { url: selectedPreset?.connection_config?.url }) }}
                    </AlertDescription>
                </Alert>

                <div class="mt-4">
                    <Label>{{ t('admin.mcp.preset.overrides') }}</Label>
                    <textarea 
                        v-model="connectionOverrides"
                        class="w-full h-[150px] p-2 mt-2 font-mono text-xs border rounded bg-slate-950 text-slate-50"
                    ></textarea>
                </div>
            </div>

            <DialogFooter>
                <Button variant="outline" @click="installModalOpen = false">{{ t('common.cancel') }}</Button>
                <Button @click="handleInstall" :disabled="isInstalling">
                    <RefreshCcw v-if="isInstalling" class="w-4 h-4 mr-2 animate-spin" />
                    {{ t('common.confirm') }}
                </Button>
            </DialogFooter>
        </DialogContent>
    </Dialog>

    <!-- Edit Modal -->
    <Dialog v-model:open="editModalOpen">
        <DialogContent class="sm:max-w-[500px]">
            <DialogHeader>
                <DialogTitle>{{ t('admin.mcp.editServer', { name: serverToEdit?.name }) }}</DialogTitle>
                <DialogDescription>
                    {{ t('admin.mcp.editServerDescription') }}
                </DialogDescription>
            </DialogHeader>
            
            <div class="py-4">
                <Label>{{ t('admin.mcp.connectionConfig') }}</Label>
                <textarea 
                    v-model="editConfig"
                    class="w-full h-[200px] p-2 mt-2 font-mono text-xs border rounded bg-slate-950 text-slate-50"
                ></textarea>
            </div>

            <DialogFooter>
                <Button variant="outline" @click="editModalOpen = false">{{ t('common.cancel') }}</Button>
                <Button @click="handleUpdateServer" :disabled="isUpdating">
                    <RefreshCcw v-if="isUpdating" class="w-4 h-4 mr-2 animate-spin" />
                    {{ t('common.save') }}
                </Button>
            </DialogFooter>
        </DialogContent>
    </Dialog>

    <!-- Tools Modal -->
    <Dialog v-model:open="toolsModalOpen">
        <DialogContent class="sm:max-w-[700px] max-h-[80vh] overflow-y-auto">
             <DialogHeader>
                <DialogTitle>{{ t('admin.mcp.tools') }} - {{ currentServerTools?.server_name }}</DialogTitle>
            </DialogHeader>

            <div v-if="isLoadingTools" class="py-8 flex justify-center">
                 <RefreshCcw class="w-8 h-8 animate-spin text-muted-foreground" />
            </div>
            
            <div v-else-if="currentServerTools?.tools?.length === 0" class="py-8 text-center text-muted-foreground">
                {{ t('common.noData') }}
            </div>

            <div v-else class="space-y-4">
                <div v-for="tool in currentServerTools?.tools" :key="tool.name" class="p-4 border rounded-lg bg-card">
                    <div class="flex items-center justify-between mb-2">
                        <span class="font-mono font-bold text-sm bg-secondary px-2 py-1 rounded">{{ tool.name }}</span>
                    </div>
                    <p class="text-sm text-muted-foreground mb-3">{{ tool.description }}</p>
                    
                    <div class="bg-muted p-2 rounded text-xs font-mono overflow-x-auto">
                        <pre>{{ JSON.stringify(tool.inputSchema, null, 2) }}</pre>
                    </div>
                </div>
            </div>
        </DialogContent>
    </Dialog>

    <McpAddCustomServerDialog 
        v-model:open="addServerModalOpen" 
        @success="handleServerAdded" 
    />
  </div>
</template>
