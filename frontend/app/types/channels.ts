export interface UserChannelBinding {
    id: string
    provider: string
    external_user_id: string
    metadata: Record<string, any>
}
