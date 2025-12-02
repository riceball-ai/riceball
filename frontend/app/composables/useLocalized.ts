import type { ComputedRef, Ref } from 'vue'

/**
 * Interface for objects with translations
 */
interface Translatable {
  translations?: Record<string, Record<string, string>>
  [key: string]: any
}

/**
 * Get localized field value with automatic fallback
 * 
 * @param obj - Object containing translations
 * @param field - Field name to localize
 * @param locale - Target locale (optional, uses current i18n locale if not provided)
 * @returns Localized field value or default field value
 * 
 * @example
 * const name = useLocalizedField(assistant, 'name')
 * const description = useLocalizedField(assistant, 'description', 'zh-Hans')
 */
export function useLocalizedField<T extends Translatable>(
  obj: ComputedRef<T> | Ref<T> | T,
  field: string,
  locale?: string
): ComputedRef<string> {
  const { locale: currentLocale } = useI18n()
  const targetLocale = locale || currentLocale.value

  return computed(() => {
    const data = unref(obj)
    
    // 1. Try to get translation for target locale
    if (data.translations?.[targetLocale]?.[field]) {
      return data.translations[targetLocale][field]
    }
    
    // 2. Fallback to default field
    return data[field] || ''
  })
}

/**
 * Get localized object with multiple fields
 * 
 * @param obj - Object containing translations
 * @param fields - Array of field names to localize
 * @param locale - Target locale (optional)
 * @returns Object with localized field values
 * 
 * @example
 * const localized = useLocalizedObject(assistant, ['name', 'description'])
 * // Returns: { name: 'Assistant', description: '...' }
 */
export function useLocalizedObject<T extends Translatable>(
  obj: ComputedRef<T> | Ref<T> | T,
  fields: string[],
  locale?: string
): ComputedRef<Record<string, string>> {
  const { locale: currentLocale } = useI18n()
  const targetLocale = locale || currentLocale.value

  return computed(() => {
    const data = unref(obj)
    const result: Record<string, string> = {}
    
    for (const field of fields) {
      // Try translation first
      if (data.translations?.[targetLocale]?.[field]) {
        result[field] = data.translations[targetLocale][field]
      } else {
        // Fallback to default
        result[field] = data[field] || ''
      }
    }
    
    return result
  })
}

/**
 * Get fully localized assistant with all translatable fields
 * This is the recommended way to use assistant localization
 * 
 * @param assistant - Assistant object
 * @param locale - Target locale (optional)
 * @returns Localized assistant object
 * 
 * @example
 * const { data: assistant } = await useAPI('/v1/assistants/123')
 * const localized = useLocalizedAssistant(assistant)
 * 
 * // Use in template
 * <h1>{{ localized.name }}</h1>
 * <p>{{ localized.description }}</p>
 */
export function useLocalizedAssistant<T extends Translatable>(
  assistant: ComputedRef<T> | Ref<T> | T,
  locale?: string
): ComputedRef<T> {
  const { locale: currentLocale } = useI18n()
  const targetLocale = locale || currentLocale.value

  return computed(() => {
    const data = unref(assistant)
    if (!data) {
      return data as T
    }
    const trans = data.translations?.[targetLocale] || {}
    
    return {
      ...data,
      name: trans.name || data.name,
      description: trans.description || data.description,
      system_prompt: trans.system_prompt || data.system_prompt
    } as T
  })
}

/**
 * Localize a list of assistants
 * 
 * @param assistants - Array of assistants
 * @param locale - Target locale (optional)
 * @returns Array of localized assistants
 * 
 * @example
 * const { data: assistants } = await useAPI('/v1/assistants')
 * const localized = useLocalizedAssistants(assistants)
 */
export function useLocalizedAssistants<T extends Translatable>(
  assistants: ComputedRef<T[]> | Ref<T[]> | T[],
  locale?: string
): ComputedRef<T[]> {
  const { locale: currentLocale } = useI18n()
  const targetLocale = locale || currentLocale.value

  return computed(() => {
    const data = unref(assistants)
    
    return data.map(assistant => {
      const trans = assistant.translations?.[targetLocale] || {}
      
      return {
        ...assistant,
        name: trans.name || assistant.name,
        description: trans.description || assistant.description,
        system_prompt: trans.system_prompt || assistant.system_prompt
      } as T
    })
  })
}
