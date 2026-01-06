import type { ConfigResponse, PublicConfig } from "~/types/api"

export const useConfigStore = defineStore('config', () => {
  const config = ref<PublicConfig>({
    registration_enabled: true,
    allow_user_create_assistants: true,
  })

  const isLoaded = ref(false)

  const loadConfig = async () => {
    if (isLoaded.value) {
      return
    }
    try {
      const { $api } = useNuxtApp()
      const response = await $api<ConfigResponse>('/v1/config/public')
      
      // Process config values to ensure booleans are correct
      const processedConfig = { ...response.configs }
      
      // Helper to convert string boolean to actual boolean
      const toBool = (val: any) => {
        if (typeof val === 'string') {
          return val.toLowerCase() !== 'false'
        }
        return Boolean(val)
      }

      // Explicitly convert known boolean keys
      if (processedConfig.registration_enabled !== undefined) {
        processedConfig.registration_enabled = toBool(processedConfig.registration_enabled)
      }
      
      if (processedConfig.allow_user_create_assistants !== undefined) {
        processedConfig.allow_user_create_assistants = toBool(processedConfig.allow_user_create_assistants)
      }
      
      if (processedConfig.enable_assistant_categories !== undefined) {
        processedConfig.enable_assistant_categories = toBool(processedConfig.enable_assistant_categories)
      }

      config.value = processedConfig
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