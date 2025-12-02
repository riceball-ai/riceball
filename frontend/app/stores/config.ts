import type { ConfigResponse, PublicConfig } from "~/types/api"

export const useConfigStore = defineStore('config', () => {
  const config = ref<PublicConfig>({
    registration_enabled: true,
  })

  const isLoaded = ref(false)

  const loadConfig = async () => {
    if (isLoaded.value) {
      return
    }
    try {
      const { $api } = useNuxtApp()
      const response = await $api<ConfigResponse>('/v1/config/public')
      config.value = response.configs
      isLoaded.value = true
    } catch (error) {
      console.error('Failed to load config:', error)
      isLoaded.value = true
    }
  }

  const getConfig = async (): Promise<PublicConfig> => {
    if (!isLoaded.value) {
      await loadConfig()
    }
    return config.value
  }

  const getConfigValue = async <K extends keyof PublicConfig>(key: K): Promise<PublicConfig[K]> => {
    const configData = await getConfig()
    return configData[key]
  }

  return {
    config,
    isLoaded,
    loadConfig,
    getConfig,
    getConfigValue
  }
})