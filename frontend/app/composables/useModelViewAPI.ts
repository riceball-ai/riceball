import type { 
  PaginatedResponse, 
  ModelViewApiResponse, 
  ModelViewQueryParams, 
  ModelViewBulkOperation 
} from '~/types/api.d.ts'

export type ModelViewApiEndpointResolver = (id: string | number) => string

export interface ModelViewApiEndpointOverrides {
  list?: string
  create?: string
  getOne?: string | ModelViewApiEndpointResolver
  update?: string | ModelViewApiEndpointResolver
  updateMethod?: string
  delete?: string | ModelViewApiEndpointResolver
}

const trimTrailingSlash = (endpoint: string) => endpoint.replace(/\/+$/, '')

const resolveEndpointWithId = (
  endpoint: string | ModelViewApiEndpointResolver | undefined,
  fallbackBase: string,
  id: string | number,
) => {
  if (endpoint) {
    if (typeof endpoint === 'function') {
      return endpoint(id)
    }
    return `${trimTrailingSlash(endpoint)}/${id}`
  }
  return `${trimTrailingSlash(fallbackBase)}/${id}`
}

/**
 * ModelView API Composable
 * Provides standardized CRUD operation interfaces, supporting pagination, search, sorting, and filtering
 */
export function useModelViewAPI<T extends Record<string, any>>(
  baseEndpoint: string,
  overrides: ModelViewApiEndpointOverrides = {},
) {

  const { $api } = useNuxtApp()
  const { t } = useI18n()

  /**
   * Get list data
   */
  const getList = async (params: ModelViewQueryParams = {}): Promise<PaginatedResponse<T>> => {
    try {
      const query = new URLSearchParams()
      
      // Add pagination parameters
      if (params.page) query.append('page', params.page.toString())
      if (params.size) query.append('size', params.size.toString())
      
      // Add search parameters
      if (params.search) query.append('search', params.search)
      
      // Add sorting parameters
      if (params.sort_by) {
        query.append('sort_by', params.sort_by)
        if (params.sort_desc !== undefined) {
          query.append('sort_desc', params.sort_desc.toString())
        }
      }
      
      // Add other filter parameters
      Object.entries(params).forEach(([key, value]) => {
        if (!['page', 'size', 'search', 'sort_by', 'sort_desc'].includes(key) && 
            value !== undefined && value !== null && value !== '') {
          query.append(key, value.toString())
        }
      })
      
      const listEndpoint = overrides.list || baseEndpoint
      const url = query.toString()
        ? `${listEndpoint}?${query.toString()}`
        : listEndpoint

      // Real API call example:
      return await $api<PaginatedResponse<T>>(url)

    } catch (error) {
      throw error
    }
  }
  
  /**
   * Get single resource
   */
  const getOne = async (id: string | number): Promise<T> => {
    try {
      const endpoint = resolveEndpointWithId(overrides.getOne, baseEndpoint, id)
      return await $api<T>(endpoint)

    } catch (error) {
      throw error
    }
  }
  
  /**
   * Create resource
   */
  const create = async (data: Omit<T, 'id'>): Promise<T> => {
    try {
      const endpoint = overrides.create || baseEndpoint
      return await $api<T>(endpoint, {
        method: 'POST',
        body: data
      })

    } catch (error) {
      throw error
    }
  }
  
  /**
   * Update resource
   */
  const update = async (id: string | number, data: Partial<T>): Promise<T> => {
    try {
      const endpoint = resolveEndpointWithId(overrides.update, baseEndpoint, id)
      return await $api<T>(endpoint, {
        method: (overrides.updateMethod || 'PUT') as any,
        body: data
      })

    } catch (error) {
      throw error
    }
  }
  
  /**
   * Delete resource
   */
  const remove = async (id: string | number): Promise<void> => {
    try {      
      // Real API call:
      const endpoint = resolveEndpointWithId(overrides.delete, baseEndpoint, id)
      await $api(endpoint, {
        method: 'DELETE'
      })

    } catch (error) {
      throw error
    }
  }
  
  /**
   * Bulk operation
   */
  const bulkOperation = async (operation: ModelViewBulkOperation): Promise<ModelViewApiResponse> => {
    try {
      
      // Simulate bulk operation success
      return {
        success: true,
        message: t('common.bulkOperationSuccess', { action: operation.action, count: operation.ids.length })
      }
      
      // Real API call:
      // return await $fetch<ModelViewApiResponse>(`${baseEndpoint}/bulk`, {
      //   method: 'POST',
      //   body: operation
      // })
      
    } catch (error) {
      throw error
    }
  }
  
  /**
   * Export data
   */
  const exportData = async (params: ModelViewQueryParams = {}): Promise<Blob> => {
    try {
      const query = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          query.append(key, value.toString())
        }
      })
      
      const url = `${baseEndpoint}/export?${query.toString()}`
      
      // Simulate export file
      const csvContent = 'id,name,email\n1,John Doe,john@example.com\n2,Jane Doe,jane@example.com'
      return new Blob([csvContent], { type: 'text/csv' })
      
      // Real API call:
      // const response = await fetch(url)
      // return await response.blob()
      
    } catch (error) {
      throw error
    }
  }
  
  /**
   * Import data
   */
  const importData = async (file: File): Promise<ModelViewApiResponse> => {
    try {
      const formData = new FormData()
      formData.append('file', file)
      
      
      // Simulate import success
      return {
        success: true,
        message: t('common.importSuccess', { count: 10 })
      }
      
      // Real API call:
      // return await $fetch<ModelViewApiResponse>(`${baseEndpoint}/import`, {
      //   method: 'POST',
      //   body: formData
      // })
      
    } catch (error) {
      throw error
    }
  }
  
  return {
    getList,
    getOne,
    create,
    update,
    remove,
    bulkOperation,
    exportData,
    importData
  }
}
