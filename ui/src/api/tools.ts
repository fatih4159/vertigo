import { apiClient } from './client'
import type { Tool, ToolExecuteResult } from '../types'

export const toolsApi = {
  list: async (): Promise<Tool[]> => {
    const res = await apiClient.get<Tool[]>('/tools')
    return res.data
  },

  getSchema: async (toolName: string): Promise<Tool> => {
    const res = await apiClient.get<Tool>(`/tools/${toolName}`)
    return res.data
  },

  execute: async (toolName: string, args: Record<string, unknown>): Promise<ToolExecuteResult> => {
    const res = await apiClient.post<ToolExecuteResult>('/tools/execute', {
      tool_name: toolName,
      args,
    })
    return res.data
  },
}
