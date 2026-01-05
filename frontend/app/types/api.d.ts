interface User {
  id: string
  email: string
  name: string
  avatar_url: string
  is_active?: boolean
  is_superuser?: boolean
  is_verified?: boolean
  created_at: string
}

interface Message {
    id: string;
    content: string;
    message_type: 'USER' | 'ASSISTANT';
  created_at: string;
  user_message_id?: string;
  status?: 'STREAMING' | 'FINAL';
  extra_data?: Record<string, any>;
}

interface ChatSession {
    id: string;
    assistant_id: string;
    messages: Message[];
    created_at: string;
    updated_at: string;
}

interface ChatResponse {
    message: string;
    conversation_updated: boolean;
    conversation_id: number;
}

interface ChatRequest {
    assistant_id: number;
    content: string;
    conversation_id?: number;
    stream?: boolean;
}

interface SendMessageRequest {
    content: string;
    assistant_id: string;
}

interface Conversation {
    id: string;
    title: string;
    assistant_id: string;
    user_id: string;
    status: string;
    last_message_at: string | null;
    message_count: number;
    created_at: string;
    updated_at: string;
    assistant_name?: string;
}

interface ConversationShareResponse {
  id: string
  conversation_id: string
  scope: 'CONVERSATION' | 'MESSAGE'
  status: 'ACTIVE' | 'REVOKED'
  start_message_id?: string | null
  end_message_id?: string | null
  created_at: string
  updated_at: string
}

interface ConversationSharePublicResponse {
  id: string
  conversation_id: string
  scope: 'CONVERSATION' | 'MESSAGE'
  assistant_id?: string | null
  assistant_name: string
  assistant_description?: string | null
  assistant?: SharedAssistant | null
  conversation_title: string
  messages: Message[]
  created_at: string
}

interface SharedAssistant {
  id: string
  name: string
  description?: string | null
  avatar_file_path?: string | null
  avatar_url?: string | null
  translations?: Record<string, Record<string, string>>
}

interface GenerateTitleResponse {
    conversation_id: string;
    title: string;
}

interface PaginatedResponse<T> {
    total: number;
    page: number;
    size: number;
    pages: number;
    items: T[];
}

type ConversationsResponse = PaginatedResponse<Conversation>;

export interface PublicConfig {
  registration_enabled: boolean
  allow_user_create_assistants?: boolean
  site_title?: string
  site_slogan?: string
  site_logo?: string
  site_favicon?: string
  pwa_enabled?: boolean
}

export interface ConfigResponse {
  configs: PublicConfig
}

export interface SystemConfigItem {
  id: string
  key: string
  value: any
  description?: string | null
  is_public: boolean
  is_enabled: boolean
  config_type: 'text' | 'boolean' | 'number' | 'select' | 'image'
  config_group: string
  label?: string
  options?: string
  created_at: string
  updated_at: string
}

export interface SystemConfigListResponse {
  configs: SystemConfigItem[]
  total: number
}

// ModelView related types
export interface ModelViewApiResponse<T = any> {
  success: boolean
  data?: T
  message?: string
  errors?: Record<string, string[]>
}

export interface ModelViewQueryParams {
  page?: number
  size?: number
  search?: string
  sort_by?: string
  sort_desc?: boolean
  [key: string]: any
}

export interface ModelViewBulkOperation {
  action: string
  ids: (string | number)[]
  data?: any
}

interface Provider {
  id: string
  display_name: string
  description: string
  website: string
  api_base_url: string
  api_key: string
  interface_type: string
  status: 'ACTIVE' | 'INACTIVE' | 'MAINTENANCE'
  created_at: string
}

interface Model {
  id: string
  name: string
  display_name: string
  description: string
  status: 'ACTIVE' | 'INACTIVE' | 'UNAVAILABLE' | 'DEPRECATED'
  provider_id: string
  max_context_tokens: number
  max_output_tokens: number
  capabilities?: string[]
  generation_config?: Record<string, any>
  created_at: string
  provider?: Provider
}

interface RagConfig {
  retrieval_count: number
  similarity_threshold: number
}

interface Assistant {
  id: string
  name: string
  description: string
  avatar_url?: string
  avatar_file_path?: string
  model_id: string
  owner_id: string
  system_prompt: string
  temperature: number
  max_tokens: number
  max_history_messages?: number | null
  status: 'ACTIVE' | 'INACTIVE' | 'DRAFT'
  is_public: boolean
  category?: string
  tags?: string[]
  created_at: string
  updated_at: string
  model?: Model
  // Knowledge base related fields
  knowledge_base_ids?: string[]
  rag_config?: RagConfig
  // Agent configuration
  enable_agent?: boolean
  agent_max_iterations?: number
  agent_enabled_tools?: string[]
  mcp_server_ids?: string[]
  is_pinned?: boolean
  translations?: Record<string, Record<string, string>>
}

interface KnowledgeBase {
  id: string
  name: string
  description: string
  embedding_model_id?: string
  chunk_size?: number
  chunk_overlap?: number
  created_at: string
  updated_at: string
}

interface Document {
  id: string
  title: string
  content?: string
  file_path?: string
  file_name?: string
  file_size?: number
  file_type: string
  knowledge_base_id: string
  status: 'PROCESSING' | 'COMPLETED' | 'FAILED'
  created_at: string
  updated_at: string
}

interface FileUploadResponse {
  file_path: string
  file_name: string
  file_size: number
  mime_type: string
}

// OAuth provider interface definition
interface OAuthProvider {
  id?: string
  name: string
  display_name: string
  description?: string
  client_id: string
  client_secret: string
  auth_url: string
  token_url: string
  user_info_url: string
  scopes: string[]
  user_mapping: Record<string, string>
  icon_url?: string
  sort_order: number
  is_active: boolean
  created_at?: string
  updated_at?: string
}

// Agent tool interface definition
interface LocalTool {
  name: string
  description: string
}

interface MCPServer {
  id: string
  name: string
  description: string
}

interface AvailableAgentTools {
  local_tools: LocalTool[]
  mcp_servers: MCPServer[]
}

