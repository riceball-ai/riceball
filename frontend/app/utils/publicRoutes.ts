const PUBLIC_ROUTE_NAMES = new Set([
  'index',
  'terms',
  'privacy',
  'sign-in',
  'sign-up',
  'verify-email',
  'forgot-password',
  'reset-password',
  'assistants',
  'chatwith-id',
  'share-id',
  'test-md'
])

export const isPublicRoute = (route: { name?: string | null; path?: string | null }) => {
  if (!route) return false

  const routeName = typeof route.name === 'string' ? route.name : undefined

  // Allow all docs routes
  if (routeName && routeName.startsWith('docs')) {
    return true
  }

  if (routeName && PUBLIC_ROUTE_NAMES.has(routeName)) {
    return true
  }

  return false
}
