import { useCallback, useEffect, useRef } from 'react'
import { useAppStore } from '../store'
import { agentsApi } from '../api/agents'
import type { StartAgentPayload } from '../api/agents'

export function useAgent(agentId: string | null) {
  const { agents, updateAgent } = useAppStore()
  const agent = agentId ? agents.find((a) => a.id === agentId) ?? null : null
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const refresh = useCallback(async () => {
    if (!agentId) return
    try {
      const updated = await agentsApi.get(agentId)
      updateAgent(updated)
    } catch {
      // silent
    }
  }, [agentId, updateAgent])

  // Poll for live status while agent may be running
  useEffect(() => {
    if (!agentId) return
    refresh()
    pollRef.current = setInterval(refresh, 2000)
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [agentId, refresh])

  const start = useCallback(
    async (payload: StartAgentPayload) => {
      if (!agentId) return
      await agentsApi.start(agentId, payload)
      await refresh()
    },
    [agentId, refresh]
  )

  const pause = useCallback(async () => {
    if (!agentId) return
    await agentsApi.pause(agentId)
    await refresh()
  }, [agentId, refresh])

  const resume = useCallback(async () => {
    if (!agentId) return
    await agentsApi.resume(agentId)
    await refresh()
  }, [agentId, refresh])

  const stop = useCallback(async () => {
    if (!agentId) return
    await agentsApi.stop(agentId)
    await refresh()
  }, [agentId, refresh])

  const chat = useCallback(
    async (message: string) => {
      if (!agentId) throw new Error('No agent selected')
      return agentsApi.chat(agentId, message)
    },
    [agentId]
  )

  return { agent, refresh, start, pause, resume, stop, chat }
}
