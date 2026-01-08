<script setup lang="ts">
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Users, MessageSquare, Zap, ThumbsUp, ThumbsDown, ArrowRight } from 'lucide-vue-next'

const { t } = useI18n()

definePageMeta({
  layout: 'admin',
  breadcrumb: 'admin.pages.dashboard.breadcrumb'
})

interface ChartDataPoint {
  name: string
  value: number
}

interface DashboardStats {
  overview: {
    total_users: number
    total_token_usage: number
    total_conversations: number
    total_feedback_like: number
    total_feedback_dislike: number
  }
  recent_users: {
    name: string
    email: string
    avatar_url?: string
    created_at: string
  }[]
  top_assistants: {
    name: string
    count: number
  }[]
}

const { data: stats, status } = await useAPI<DashboardStats>('/api/v1/admin/dashboard/stats')

const userGrowthConfig = {
  value: { label: 'New Users', color: 'hsl(var(--primary))' }
}

const modelDistConfig = {
  value: { label: 'Usage', color: 'hsl(var(--chart-2))' }
}

// Formatters
const formatNumber = (num: number) => new Intl.NumberFormat('en-US').format(num)
const formatDate = (dateStr: string) => new Date(dateStr).toLocaleDateString()

</script>

<template>
  <div class="flex flex-1 flex-col gap-4 p-4">
    <div v-if="status === 'pending'" class="flex items-center justify-center h-96">
      {{ t('common.loading') }}
    </div>
    <div v-else-if="stats" class="space-y-4">
      <!-- Overview Cards -->
      <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle class="text-sm font-medium">{{ t('admin.pages.dashboard.totalUsers') }}</CardTitle>
            <Users class="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div class="text-2xl font-bold">{{ formatNumber(stats.overview.total_users) }}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle class="text-sm font-medium">{{ t('admin.pages.dashboard.tokenUsage') }}</CardTitle>
            <Zap class="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div class="text-2xl font-bold">{{ formatNumber(stats.overview.total_token_usage) }}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle class="text-sm font-medium">{{ t('admin.pages.dashboard.conversations') }}</CardTitle>
            <MessageSquare class="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div class="text-2xl font-bold">{{ formatNumber(stats.overview.total_conversations) }}</div>
          </CardContent>
        </Card>

        <!-- Feedback Card -->
        <Card class="cursor-pointer transition-colors hover:bg-accent/50" @click="navigateTo('/admin/feedbacks')">
          <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle class="text-sm font-medium">{{ t('admin.pages.dashboard.feedback') }}</CardTitle>
            <ArrowRight class="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div class="flex items-center gap-4">
              <div class="flex items-center gap-1 text-green-600 dark:text-green-500">
                <ThumbsUp class="w-4 h-4" />
                <span class="text-2xl font-bold">{{ formatNumber(stats.overview.total_feedback_like || 0) }}</span>
              </div>
              <div class="w-px h-8 bg-border"></div>
              <div class="flex items-center gap-1 text-red-600 dark:text-red-500">
                <ThumbsDown class="w-4 h-4" />
                <span class="text-2xl font-bold">{{ formatNumber(stats.overview.total_feedback_dislike || 0) }}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <!-- Lists -->
      <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <Card class="col-span-4">
          <CardHeader>
            <CardTitle>{{ t('admin.pages.dashboard.recentUsers') }}</CardTitle>
            <CardDescription>{{ t('admin.pages.dashboard.recentUsersDesc') }}</CardDescription>
          </CardHeader>
          <CardContent>
            <div class="space-y-8">
              <div v-for="user in stats.recent_users" :key="user.email" class="flex items-center">
                <Avatar class="h-9 w-9">
                  <AvatarImage :src="user.avatar_url || ''" :alt="user.name" />
                  <AvatarFallback>{{ user.name?.substring(0, 2).toUpperCase() || 'U' }}</AvatarFallback>
                </Avatar>
                <div class="ml-4 space-y-1">
                  <p class="text-sm font-medium leading-none">{{ user.name || t('admin.pages.dashboard.unnamed') }}</p>
                  <p class="text-sm text-muted-foreground">{{ user.email }}</p>
                </div>
                <div class="ml-auto font-medium text-xs text-muted-foreground">
                  {{ formatDate(user.created_at) }}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card class="col-span-3">
          <CardHeader>
            <CardTitle>{{ t('admin.pages.dashboard.topAssistants') }}</CardTitle>
            <CardDescription>{{ t('admin.pages.dashboard.topAssistantsDesc') }}</CardDescription>
          </CardHeader>
          <CardContent>
            <div class="space-y-8">
              <div v-for="(assistant, index) in stats.top_assistants" :key="assistant.name" class="flex items-center">
                <div class="flex h-9 w-9 items-center justify-center rounded-full bg-muted">
                  {{ index + 1 }}
                </div>
                <div class="ml-4 space-y-1">
                  <p class="text-sm font-medium leading-none">{{ assistant.name }}</p>
                  <p class="text-sm text-muted-foreground">{{ t('admin.pages.dashboard.conversationsCount', { count: assistant.count }) }}</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
</template>

<style scoped></style>
