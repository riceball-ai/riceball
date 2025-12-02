import { defineNuxtPlugin } from '#app'
import { useConfigStore } from '~/stores/config'

export default defineNuxtPlugin(async () => {
  const configStore = useConfigStore()

  if (!configStore.isLoaded) {
    await configStore.loadConfig()
  }
})