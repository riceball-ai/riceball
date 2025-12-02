import { isPublicRoute } from '~/utils/publicRoutes'

export default defineNuxtRouteMiddleware(async (to) => {
  const routeInfo = { name: to.name?.toString() }
  const isPublic = isPublicRoute(routeInfo)

  const userStore = useUserStore()
  const signInRoute = { path: '/sign-in', query: { redirect: to.fullPath } }

  if (to.path === '/') {
    return navigateTo('/assistants')
  }

  if (!userStore.user && !userStore.loading) {
    const isLoggedIn = await userStore.fetchUser()

    if (userStore.verificationRequired) {
      return navigateTo('/verify-email')
    }

    if (!isLoggedIn && !isPublic) {
      return navigateTo(signInRoute)
    }
  }

  if (isPublic) {
    return
  }

  if (userStore.loading || userStore.user) {
    return
  }

  return navigateTo(signInRoute)
})
