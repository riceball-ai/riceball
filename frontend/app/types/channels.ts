export interface ChannelConfig {
  id: string
  name: string
  provider: string
  is_active: boolean
  description?: string
  settings?: Record<string, any>
}

export interface UserChannelBinding {
    id: string
    provider: string
    external_user_id: string
    metadata: Record<string, any>
}
