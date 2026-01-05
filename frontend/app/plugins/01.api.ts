import { isPublicRoute } from '~/utils/publicRoutes'

export default defineNuxtPlugin(nuxtApp => {
    let isRefreshing = false
    let refreshPromise: Promise<void> | null = null

    const redirectToSignIn = async () => {
        const router = useRouter()
        const currentRoute = router.currentRoute.value
        if (!isPublicRoute({ name: currentRoute.name?.toString() })) {
            await navigateTo('/sign-in')
        }
    }

    // Get cookies
    const getAuthHeaders = () => {
        if (import.meta.server) {
            const accessToken = useCookie('access-token')
            const refreshToken = useCookie('refresh-token')
            const headers: Record<string, string> = {}
            
            if (accessToken.value) {
                headers['Cookie'] = `access-token=${accessToken.value}`
                if (refreshToken.value) {
                    headers['Cookie'] += `; refresh-token=${refreshToken.value}`
                }
            }
            return headers
        }
        return {}
    }

    const refreshToken = async () => {
        if (!isRefreshing) {
            const performRefresh = async () => {
                try {
                    await $fetch('/api/v1/auth/refresh', {
                        method: 'POST',
                        credentials: 'include',
                        headers: getAuthHeaders()
                    })
                } catch (error) {
                    // Clear user state to prevent middleware from re-triggering API calls
                    const userStore = useUserStore()
                    userStore.clearUser()

                    // Use navigateTo instead of window.location.replace to avoid infinite loop
                    await redirectToSignIn()
                    throw error
                } finally {
                    isRefreshing = false
                    refreshPromise = null
                }
            }

            isRefreshing = true
            refreshPromise = performRefresh()
        }
        return refreshPromise
    }

    const api = async <T = any>(url: string, options?: any): Promise<T> => {
        try {
            const headers = {
                ...getAuthHeaders(),
                ...options?.headers
            }
            
            return await $fetch<T>(url, {
                ...options,
                baseURL: '/api',
                credentials: 'include',
                headers
            })
        } catch (error: any) {
            // If it's 401 and not the refresh endpoint
            if (error.response?.status === 401 && !url.includes('/auth/refresh')) {
                try {
                    // Refresh token
                    await refreshToken()
                    // Retry original request
                    const headers = {
                        ...getAuthHeaders(),
                        ...options?.headers
                    }
                    return await $fetch<T>(url, {
                        ...options,
                        baseURL: '/api',
                        credentials: 'include',
                        headers
                    })
                } catch (refreshError) {
                    // If refresh fails, throw original error
                    throw error
                }
            }
            // Throw other errors directly
            throw error
        }
    }

    return {
        provide: {
            api
        }
    }
})