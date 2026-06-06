import { useEffect, useCallback } from 'react'
import { useAppStore } from '../store'
import { modelsApi } from '../api/models'

export function useModels() {
  const { models, setModels, ollamaHealthy, setOllamaHealthy } = useAppStore()

  const refresh = useCallback(async () => {
    try {
      const [health, list] = await Promise.all([modelsApi.health(), modelsApi.list()])
      setOllamaHealthy(health.healthy)
      setModels(list)
    } catch {
      setOllamaHealthy(false)
    }
  }, [setModels, setOllamaHealthy])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { models, ollamaHealthy, refresh }
}
