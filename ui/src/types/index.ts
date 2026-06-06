// TypeScript types matching backend Pydantic models and DB schemas

export type AgentState =
  | 'IDLE'
  | 'RUNNING'
  | 'PAUSED'
  | 'STOPPED'
  | 'ERROR'
  | 'THINKING'
  | 'EXECUTING'

export type RunMode =
  | 'run_forever'
  | 'run_until_goal'
  | 'run_n_iterations'
  | 'manual_step'

export type MemoryType = 'short' | 'mid' | 'long'

export interface Agent {
  id: string
  name: string
  masterprompt: string
  state: AgentState
  model_name: string
  config_json: Record<string, unknown> | null
  project_id: string | null
  created_at: string
  updated_at: string
  live_status?: LiveStatus
}

export interface LiveStatus {
  state: AgentState
  current_iteration: number
  total_iterations: number
  current_goal: string | null
  tokens_used: number
  run_mode: RunMode | null
}

export interface Iteration {
  id: string
  number: number
  goal: string | null
  plan_json: Plan | null
  result_json: IterationResult | null
  status: 'pending' | 'success' | 'failed' | 'paused' | 'stopped'
  started_at: string
  finished_at: string | null
  tokens_used: number
  tool_calls?: ToolCall[]
}

export interface Plan {
  goal: string
  steps: PlanStep[]
  reasoning: string
}

export interface PlanStep {
  id: string
  description: string
  tool_name: string | null
  tool_args: Record<string, unknown>
  status: 'pending' | 'running' | 'done' | 'failed'
}

export interface IterationResult {
  summary: string
  success: boolean
  artifacts: string[]
  next_goal: string | null
}

export interface ToolCall {
  id: string
  tool_name: string
  input_json: Record<string, unknown> | null
  output_json: Record<string, unknown> | null
  success: boolean
  error_message: string | null
  duration_ms: number
  called_at: string
}

export interface MemoryEntry {
  id: string
  memory_type: MemoryType
  key: string
  content: string
  metadata: Record<string, unknown> | null
  access_count: number
  created_at: string
  accessed_at: string
}

export interface MemoryStats {
  agent_id: string
  counts_by_type: Record<MemoryType, number>
}

export interface WsEvent {
  id: string
  type: string
  data: Record<string, unknown>
  timestamp: string
  agent_id: string | null
}

export interface OllamaModel {
  name: string
  size: number
  digest: string
  modified_at: string
  details?: {
    parameter_size?: string
    quantization_level?: string
    family?: string
  }
}

export interface Tool {
  name: string
  description: string
  category: string
  input_schema: Record<string, unknown>
}

export interface ToolExecuteResult {
  tool: string
  success: boolean
  output: string | null
  error: string | null
  duration_ms: number
  metadata: Record<string, unknown>
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
}

export interface GitStatus {
  branch: string
  is_dirty: boolean
  staged: string[]
  unstaged: string[]
  untracked: string[]
  ahead: number
  behind: number
}

export interface Settings {
  backendUrl: string
  wsUrl: string
  defaultModel: string
  autoScroll: boolean
  maxEventHistory: number
}
