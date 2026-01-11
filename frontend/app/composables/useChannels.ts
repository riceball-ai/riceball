export enum ChannelProvider {
  TELEGRAM = 'telegram',
  DISCORD = 'discord',
  WECOM = 'wecom',
  SLACK = 'slack'
}

export interface Channel {
  id: string
  name: string
  provider: ChannelProvider
  assistant_id: string
  is_active: boolean
  settings: Record<string, any>
  metadata_: Record<string, any>
  credentials?: Record<string, any> // usually hidden
  created_at: string
  updated_at: string
}

export interface ChannelCreate {
  name: string
  provider: ChannelProvider
  assistant_id: string
  credentials: Record<string, any>
  settings?: Record<string, any>
  is_active?: boolean
}

export interface ChannelUpdate {
  name?: string
  credentials?: Record<string, any>
  settings?: Record<string, any>
  is_active?: boolean
}

export const useChannels = () => {
  const { $api } = useNuxtApp()

  const listChannels = async (assistantId: string) => {
    return await $api<Channel[]>(`/v1/channels/assistant/${assistantId}`)
  }

  const createChannel = async (payload: ChannelCreate) => {
    return await $api<Channel>('/v1/channels', {
      method: 'POST',
      body: payload
    })
  }

  const updateChannel = async (channelId: string, payload: ChannelUpdate) => {
    return await $api<Channel>(`/v1/channels/${channelId}`, {
      method: 'PUT',
      body: payload
    })
  }

  const deleteChannel = async (channelId: string) => {
    return await $api<void>(`/v1/channels/${channelId}`, {
      method: 'DELETE'
    })
  }

  return {
    listChannels,
    createChannel,
    updateChannel,
    deleteChannel
  }
}
