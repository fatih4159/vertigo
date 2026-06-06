import { apiClient } from './client'
import type { OllamaModel } from '../types'

export const modelsApi = {
  list: async (): Promise<OllamaModel[]> => {
    const res = await apiClient.get<OllamaModel[]>('/models')
    return res.data
  },

  health: async (): Promise<{ healthy: boolean; base_url: string; default_model: string }> => {
    const res = await apiClient.get('/models/health')
    return res.data
  },

  info: async (modelName: string): Promise<OllamaModel> => {
    const res = await apiClient.get<OllamaModel>(`/models/${encodeURIComponent(modelName)}/info`)
    return res.data
  },

  pull: async (
    model: string,
    onProgress: (event: { status: string; completed?: number; total?: number }) => void
  ): Promise<void> => {
    const response = await fetch('/api/v1/models/pull', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model }),
    })

    if (!response.body) throw new Error('No response body')

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
      for (const line of lines) {
        if (line.trim()) {
          try {
            onProgress(JSON.parse(line))
          } catch {
            // ignore parse errors
          }
        }
      }
    }
  },
}
