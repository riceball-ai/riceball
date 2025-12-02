export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.vueApp.config.errorHandler = (error, instance, info) => {
    console.error('Global Error Handler:', error)
    console.error('Component:', instance)
    console.error('Info:', info)
  }

  nuxtApp.vueApp.config.warnHandler = (msg, instance, trace) => {
    // Filter out common non-critical warnings if needed
    // if (msg.includes('some-harmless-warning')) return

    console.warn('Global Warning Handler:', msg)
    if (instance) {
      console.warn('Component:', instance)
    }
    if (trace) {
      console.warn('Trace:', trace)
    }
    
    // Specifically look for hydration mismatches
    if (msg.includes('Hydration completed but contains mismatches')) {
      console.error('HYDRATION MISMATCH DETECTED!')
      console.error('Message:', msg)
      console.error('Component Trace:', trace)
      // You could send this to a logging service here
    }
  }
})
