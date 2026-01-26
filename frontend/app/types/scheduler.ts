export interface ScheduledTask {
  id: string
  owner_id: string
  name: string
  description?: string
  cron_expression: string
  assistant_id: string
  prompt_template: string
  channel_config_id: string
  target_identifier: string
  is_active: boolean
  last_run_at?: string
  created_at: string
  updated_at: string
}

export interface ScheduledTaskCreate {
  name: string
  description?: string
  cron_expression: string
  assistant_id: string
  prompt_template: string
  channel_config_id: string
  target_identifier: string
  is_active: boolean
}

export interface ScheduledTaskUpdate {
  name?: string
  description?: string
  cron_expression?: string
  assistant_id?: string
  prompt_template?: string
  channel_config_id?: string
  target_identifier?: string
  is_active?: boolean
}
