export default defineNuxtRouteMiddleware(async (to) => {
  if (!to.path.startsWith('/admin')) {
    return
  }
  
  const userStore = useUserStore()
  
  if (!userStore.user && !userStore.loading) {
    const isLoggedIn = await userStore.fetchUser()
    
    if (!isLoggedIn) {
      return navigateTo('/sign-in')
    }
  }
  
  if (userStore.loading) {
    return
  }
  
  if (!userStore.user || !userStore.user.is_superuser) {
    throw createError({
      statusCode: 403,
      statusMessage: 'Access Denied: Admins Only',
    })
  }
})