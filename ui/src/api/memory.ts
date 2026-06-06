import { apiClient } from './client'
import type { MemoryEntry, MemoryStats, MemoryType } from '../types'

export const memoryApi = {
  list: async (agentId: string, memoryType?: MemoryType, limit = 100): Promise<MemoryEntry[]> => {
    const params: Record<string, unknown> = { limit }
    if (memoryType) params.memory_type = memoryType
    const res = await apiClient.get<MemoryEntry[]>(`/agents/${agentId}/memory`, { params })
    return res.data
  },

  stats: async (agentId: string): Promise<MemoryStats> => {
    const res = await apiClient.get<MemoryStats>(`/agents/${agentId}/memory/stats`)
    return res.data
  },
}
