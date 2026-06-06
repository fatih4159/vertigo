import { apiClient } from './client'
import type { Agent, Iteration, RunMode, WsEvent } from '../types'

export interface CreateAgentPayload {
  name: string
  masterprompt: string
  model_name: string
  project_id?: string
  config?: Record<string, unknown>
}

export interface StartAgentPayload {
  mode: RunMode
  n_iterations?: number
  goal?: string
}

export const agentsApi = {
  list: async (state?: string): Promise<Agent[]> => {
    const params = state ? { state } : {}
    const res = await apiClient.get<Agent[]>('/agents', { params })
    return res.data
  },

  get: async (id: string): Promise<Agent> => {
    const res = await apiClient.get<Agent>(`/agents/${id}`)
    return res.data
  },

  create: async (payload: CreateAgentPayload): Promise<Agent> => {
    const res = await apiClient.post<Agent>('/agents', payload)
    return res.data
  },

  update: async (id: string, payload: Partial<CreateAgentPayload>): Promise<Agent> => {
    const res = await apiClient.patch<Agent>(`/agents/${id}`, payload)
    return res.data
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/agents/${id}`)
  },

  start: async (id: string, payload: StartAgentPayload): Promise<{ status: string }> => {
    const res = await apiClient.post(`/agents/${id}/start`, payload)
    return res.data
  },

  pause: async (id: string): Promise<{ status: string }> => {
    const res = await apiClient.post(`/agents/${id}/pause`)
    return res.data
  },

  resume: async (id: string): Promise<{ status: string }> => {
    const res = await apiClient.post(`/agents/${id}/resume`)
    return res.data
  },

  stop: async (id: string): Promise<{ status: string }> => {
    const res = await apiClient.post(`/agents/${id}/stop`)
    return res.data
  },

  chat: async (id: string, message: string): Promise<{ agent_id: string; message: string; response: string }> => {
    const res = await apiClient.post(`/agents/${id}/chat`, { message })
    return res.data
  },

  listIterations: async (id: string, limit = 50, offset = 0): Promise<Iteration[]> => {
    const res = await apiClient.get<Iteration[]>(`/agents/${id}/iterations`, {
      params: { limit, offset },
    })
    return res.data
  },

  listEvents: async (id: string, eventType?: string, limit = 100): Promise<WsEvent[]> => {
    const params: Record<string, unknown> = { limit }
    if (eventType) params.event_type = eventType
    const res = await apiClient.get<WsEvent[]>(`/agents/${id}/events`, { params })
    return res.data
  },
}
