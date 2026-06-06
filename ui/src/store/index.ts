import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Agent, OllamaModel, WsEvent, Settings, GitHubUser, GitHubRepo } from '../types'

interface AppState {
  // Agents
  agents: Agent[]
  activeAgentId: string | null
  setAgents: (agents: Agent[]) => void
  updateAgent: (agent: Agent) => void
  removeAgent: (id: string) => void
  setActiveAgentId: (id: string | null) => void

  // Models
  models: OllamaModel[]
  ollamaHealthy: boolean
  setModels: (models: OllamaModel[]) => void
  setOllamaHealthy: (healthy: boolean) => void

  // WebSocket events
  wsEvents: WsEvent[]
  addWsEvent: (event: WsEvent) => void
  clearWsEvents: () => void

  // UI state
  sidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void

  // Settings
  settings: Settings
  updateSettings: (partial: Partial<Settings>) => void

  // GitHub (not persisted)
  githubUser: GitHubUser | null
  githubRepos: GitHubRepo[]
  setGithubUser: (user: GitHubUser | null) => void
  setGithubRepos: (repos: GitHubRepo[]) => void
}

const DEFAULT_SETTINGS: Settings = {
  backendUrl: '/api/v1',
  wsUrl: '',
  defaultModel: 'qwen2.5-coder:latest',
  autoScroll: true,
  maxEventHistory: 300,
  githubToken: '',
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      // Agents
      agents: [],
      activeAgentId: null,
      setAgents: (agents) => set({ agents }),
      updateAgent: (agent) =>
        set((state) => ({
          agents: state.agents.some((a) => a.id === agent.id)
            ? state.agents.map((a) => (a.id === agent.id ? agent : a))
            : [...state.agents, agent],
        })),
      removeAgent: (id) =>
        set((state) => ({
          agents: state.agents.filter((a) => a.id !== id),
          activeAgentId: state.activeAgentId === id ? null : state.activeAgentId,
        })),
      setActiveAgentId: (id) => set({ activeAgentId: id }),

      // Models
      models: [],
      ollamaHealthy: false,
      setModels: (models) => set({ models }),
      setOllamaHealthy: (ollamaHealthy) => set({ ollamaHealthy }),

      // WS events
      wsEvents: [],
      addWsEvent: (event) =>
        set((state) => {
          const next = [...state.wsEvents, event]
          const max = state.settings.maxEventHistory
          return { wsEvents: next.length > max ? next.slice(next.length - max) : next }
        }),
      clearWsEvents: () => set({ wsEvents: [] }),

      // UI
      sidebarOpen: true,
      setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),

      // Settings
      settings: DEFAULT_SETTINGS,
      updateSettings: (partial) =>
        set((state) => ({ settings: { ...state.settings, ...partial } })),

      // GitHub
      githubUser: null,
      githubRepos: [],
      setGithubUser: (githubUser) => set({ githubUser }),
      setGithubRepos: (githubRepos) => set({ githubRepos }),
    }),
    {
      name: 'aaos-store',
      partialize: (state) => ({
        activeAgentId: state.activeAgentId,
        settings: state.settings,
        sidebarOpen: state.sidebarOpen,
      }),
    }
  )
)
