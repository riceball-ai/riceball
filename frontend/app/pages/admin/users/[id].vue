<script setup lang="ts">
import { toast } from 'vue-sonner'

const { t } = useI18n()

definePageMeta({
  breadcrumb: 'admin.pages.users.detail.breadcrumb',
  layout: 'admin'
})

const route = useRoute()
const userId = route.params.id as string

// Tabs
const activeTab = ref('info')

// Load user info
const { data: user, refresh: refreshUser } = await useAPI(`/v1/admin/users/${userId}`)

// Load balance info
const { data: balance, refresh: refreshBalance } = await useAPI(`/v1/admin/users/${userId}/balance`)

// Recharge records
const rechargePage = ref(1)
const rechargePageSize = ref(20)
const { data: rechargeData, pending: rechargePending, refresh: refreshRecharge } = await useAPI(
  `/v1/admin/users/${userId}/recharge-records`,
  {
    query: {
      page: rechargePage,
      size: rechargePageSize
    }
  }
)

// Consumption records
const consumptionPage = ref(1)
const consumptionPageSize = ref(20)
const { data: consumptionData, pending: consumptionPending, refresh: refreshConsumption } = await useAPI(
  `/v1/admin/users/${userId}/consumption-records`,
  {
    query: {
      page: consumptionPage,
      size: consumptionPageSize
    }
  }
)

// Format date
const formatDate = (date: string | null) => {
  if (!date) return '-'
  return new Date(date).toLocaleString()
}

// Format amount
const formatAmount = (amount: number | string) => {
  return `$${Number(amount).toFixed(2)}`
}

// Recharge status mapping
const rechargeStatusMap = computed(() => ({
  COMPLETED: { label: t('admin.pages.users.detail.recharge.statusMap.completed'), variant: 'default' as const },
  PENDING: { label: t('admin.pages.users.detail.recharge.statusMap.pending'), variant: 'secondary' as const },
  PROCESSING: { label: t('admin.pages.users.detail.recharge.statusMap.processing'), variant: 'outline' as const },
  FAILED: { label: t('admin.pages.users.detail.recharge.statusMap.failed'), variant: 'destructive' as const },
  CANCELLED: { label: t('admin.pages.users.detail.recharge.statusMap.cancelled'), variant: 'secondary' as const },
  REFUNDED: { label: t('admin.pages.users.detail.recharge.statusMap.refunded'), variant: 'destructive' as const }
}))

watch([rechargePage], () => {
  refreshRecharge()
})

watch([consumptionPage], () => {
  refreshConsumption()
})
</script>

<template>
  <div class="container mx-auto py-6 space-y-6">
    <!-- Back button -->
    <div class="flex items-center gap-4">
      <Button variant="outline" @click="$router.back()">
        <Icon name="lucide:arrow-left" class="mr-2 h-4 w-4" />
        {{ t('common.back') }}
      </Button>
      <h1 class="text-3xl font-bold">{{ t('admin.pages.users.detail.title') }}</h1>
    </div>

    <!-- User basic info card -->
    <Card v-if="user">
      <CardHeader>
        <CardTitle>{{ t('admin.pages.users.detail.basicInfo') }}</CardTitle>
      </CardHeader>
      <CardContent>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <div class="text-sm text-muted-foreground">{{ t('admin.pages.users.detail.email') }}</div>
            <div class="font-medium">{{ user.email }}</div>
          </div>
          <div>
            <div class="text-sm text-muted-foreground">{{ t('admin.pages.users.detail.name') }}</div>
            <div class="font-medium">{{ user.name || '-' }}</div>
          </div>
          <div>
            <div class="text-sm text-muted-foreground">{{ t('admin.pages.users.detail.status') }}</div>
            <div class="flex gap-2 mt-1">
              <Badge v-if="user.is_active" variant="default">{{ t('admin.pages.users.detail.active') }}</Badge>
              <Badge v-else variant="secondary">{{ t('admin.pages.users.detail.inactive') }}</Badge>
              <Badge v-if="user.is_verified" variant="default">{{ t('admin.pages.users.detail.verified') }}</Badge>
            </div>
          </div>
          <div>
            <div class="text-sm text-muted-foreground">{{ t('admin.pages.users.detail.role') }}</div>
            <div class="mt-1">
              <Badge v-if="user.is_superuser" variant="destructive">{{ t('admin.pages.users.detail.admin') }}</Badge>
              <span v-else class="text-muted-foreground">{{ t('admin.pages.users.detail.user') }}</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- Balance statistics card -->
    <div v-if="balance" class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <Card>
        <CardHeader class="pb-2">
          <CardTitle class="text-sm font-medium">{{ t('admin.pages.users.detail.currentBalance') }}</CardTitle>
        </CardHeader>
        <CardContent>
          <div class="text-2xl font-bold">{{ formatAmount(balance.balance) }}</div>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader class="pb-2">
          <CardTitle class="text-sm font-medium">{{ t('admin.pages.users.detail.totalRecharged') }}</CardTitle>
        </CardHeader>
        <CardContent>
          <div class="text-2xl font-bold text-green-600">{{ formatAmount(balance.total_recharged) }}</div>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader class="pb-2">
          <CardTitle class="text-sm font-medium">{{ t('admin.pages.users.detail.totalConsumed') }}</CardTitle>
        </CardHeader>
        <CardContent>
          <div class="text-2xl font-bold text-orange-600">{{ formatAmount(balance.total_consumed) }}</div>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader class="pb-2">
          <CardTitle class="text-sm font-medium">{{ t('admin.pages.users.detail.lastUpdated') }}</CardTitle>
        </CardHeader>
        <CardContent>
          <div class="text-sm text-muted-foreground">{{ formatDate(balance.updated_at) }}</div>
        </CardContent>
      </Card>
    </div>

    <!-- Tabs -->
    <Card>
      <CardHeader>
        <Tabs v-model="activeTab">
          <TabsList>
            <TabsTrigger value="recharge">{{ t('admin.pages.users.detail.tabs.recharge') }}</TabsTrigger>
            <TabsTrigger value="consumption">{{ t('admin.pages.users.detail.tabs.consumption') }}</TabsTrigger>
          </TabsList>
        </Tabs>
      </CardHeader>
      <CardContent>
        <!-- Recharge records tab -->
        <div v-show="activeTab === 'recharge'">
          <div v-if="rechargePending" class="flex justify-center py-8">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
          
          <div v-else-if="rechargeData?.items && rechargeData.items.length > 0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{{ t('admin.pages.users.detail.recharge.transactionId') }}</TableHead>
                  <TableHead>{{ t('admin.pages.users.detail.recharge.amount') }}</TableHead>
                  <TableHead>{{ t('admin.pages.users.detail.recharge.paymentProvider') }}</TableHead>
                  <TableHead>{{ t('admin.pages.users.detail.recharge.status') }}</TableHead>
                  <TableHead>{{ t('admin.pages.users.detail.recharge.completedAt') }}</TableHead>
                  <TableHead>{{ t('admin.pages.users.detail.recharge.createdAt') }}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow v-for="record in rechargeData.items" :key="record.id">
                  <TableCell class="font-mono text-xs">{{ record.transaction_id || '-' }}</TableCell>
                  <TableCell class="font-medium">{{ formatAmount(record.amount) }} {{ record.currency.toUpperCase() }}</TableCell>
                  <TableCell>{{ record.payment_provider }}</TableCell>
                  <TableCell>
                    <Badge :variant="rechargeStatusMap[record.status]?.variant || 'secondary'">
                      {{ rechargeStatusMap[record.status]?.label || record.status }}
                    </Badge>
                  </TableCell>
                  <TableCell>{{ formatDate(record.completed_at) }}</TableCell>
                  <TableCell>{{ formatDate(record.created_at) }}</TableCell>
                </TableRow>
              </TableBody>
            </Table>
            
            <!-- Pagination -->
            <div class="flex justify-between items-center mt-4">
              <div class="text-sm text-muted-foreground">
                {{ t('admin.pages.users.detail.pagination.showing', { start: ((rechargePage - 1) * rechargePageSize) + 1, end: Math.min(rechargePage * rechargePageSize, rechargeData.total), total: rechargeData.total }) }}
              </div>
              <div class="flex gap-2">
                <Button :disabled="rechargePage <= 1" @click="rechargePage--">{{ t('admin.pages.users.detail.pagination.prev') }}</Button>
                <Button :disabled="rechargePage * rechargePageSize >= rechargeData.total" @click="rechargePage++">{{ t('admin.pages.users.detail.pagination.next') }}</Button>
              </div>
            </div>
          </div>
          
          <div v-else class="text-center py-8 text-muted-foreground">
            {{ t('admin.pages.users.detail.recharge.noData') }}
          </div>
        </div>

        <!-- Consumption records tab -->
        <div v-show="activeTab === 'consumption'">
          <div v-if="consumptionPending" class="flex justify-center py-8">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
          
          <div v-else-if="consumptionData?.items && consumptionData.items.length > 0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{{ t('admin.pages.users.detail.consumption.model') }}</TableHead>
                  <TableHead>{{ t('admin.pages.users.detail.consumption.inputTokens') }}</TableHead>
                  <TableHead>{{ t('admin.pages.users.detail.consumption.outputTokens') }}</TableHead>
                  <TableHead>{{ t('admin.pages.users.detail.consumption.totalTokens') }}</TableHead>
                  <TableHead>{{ t('admin.pages.users.detail.consumption.time') }}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow v-for="record in consumptionData.items" :key="record.id">
                  <TableCell class="font-medium">{{ record.model_name }}</TableCell>
                  <TableCell>{{ record.input_tokens.toLocaleString() }}</TableCell>
                  <TableCell>{{ record.output_tokens.toLocaleString() }}</TableCell>
                  <TableCell class="font-medium">{{ record.total_tokens.toLocaleString() }}</TableCell>
                  <TableCell>{{ formatDate(record.created_at) }}</TableCell>
                </TableRow>
              </TableBody>
            </Table>
            
            <!-- Pagination -->
            <div class="flex justify-between items-center mt-4">
              <div class="text-sm text-muted-foreground">
                {{ t('admin.pages.users.detail.pagination.showing', { start: ((consumptionPage - 1) * consumptionPageSize) + 1, end: Math.min(consumptionPage * consumptionPageSize, consumptionData.total), total: consumptionData.total }) }}
              </div>
              <div class="flex gap-2">
                <Button :disabled="consumptionPage <= 1" @click="consumptionPage--">{{ t('admin.pages.users.detail.pagination.prev') }}</Button>
                <Button :disabled="consumptionPage * consumptionPageSize >= consumptionData.total" @click="consumptionPage++">{{ t('admin.pages.users.detail.pagination.next') }}</Button>
              </div>
            </div>
          </div>
          
          <div v-else class="text-center py-8 text-muted-foreground">
            {{ t('admin.pages.users.detail.consumption.noData') }}
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
