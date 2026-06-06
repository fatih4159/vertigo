import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bot, Plus, Activity, Cpu, Brain, Wrench, Loader2 } from 'lucide-react'
import clsx from 'clsx'
import { useAppStore } from '../store'
import { agentsApi } from '../api/agents'
import { useModels } from '../hooks/useModels'
import ModelManagement from '../components/ModelManagement'
import Settings from '../components/Settings'
import ToolViewer from '../components/ToolViewer'
import type { Agent } from '../types'

const STATE_COLORS: Record<string, string> = {
  IDLE: 'bg-state-idle',
  RUNNING: 'bg-state-running animate-pulse',
  PAUSED: 'bg-state-paused',
  STOPPED: 'bg-state-stopped',
  ERROR: 'bg-state-error animate-pulse',
}

type Tab = 'overview' | 'models' | 'tools' | 'settings'

export default function Dashboard() {
  const { agents, setAgents, setActiveAgentId, wsEvents } = useAppStore()
  const { models } = useModels()
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('overview')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    agentsApi.list().then(setAgents).catch(() => {})
  }, [setAgents])

  const handleNewAgent = async () => {
    setCreating(true)
    try {
      const agent = await agentsApi.create({
        name: `Agent-${Date.now().toString(36).toUpperCase()}`,
        masterprompt:
          'You are an autonomous AI agent. You help the user by breaking down goals into actionable steps, using available tools to accomplish tasks, and learning from each iteration.\n\nBe concise, precise, and proactive. Always explain what you are doing and why.',
        model_name: models[0]?.name || 'qwen2.5-coder:latest',
      })
      const all = await agentsApi.list()
      setAgents(all)
      setActiveAgentId(agent.id)
      navigate(`/agents/${agent.id}`)
    } catch (err) {
      console.error(err)
    } finally {
      setCreating(false)
    }
  }

  const stateCounts = agents.reduce<Record<string, number>>((acc, a) => {
    acc[a.state] = (acc[a.state] ?? 0) + 1
    return acc
  }, {})

  const recentEvents = wsEvents.slice(-5).reverse()

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Hero */}
      <div className="bg-bg-secondary rounded-xl border border-border p-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-100">AAOS Dashboard</h1>
            <p className="text-slate-500 mt-1 text-sm">AGI Agent Operating System</p>
          </div>
          <button
            onClick={handleNewAgent}
            disabled={creating}
            className="flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
          >
            {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            New Agent
          </button>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          <StatCard icon={Bot} label="Total Agents" value={agents.length} />
          <StatCard
            icon={Activity}
            label="Running"
            value={stateCounts.RUNNING ?? 0}
            accent="text-green-400"
          />
          <StatCard icon={Cpu} label="Models" value={models.length} />
          <StatCard
            icon={Brain}
            label="Events"
            value={wsEvents.length}
            accent="text-violet-400"
          />
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-bg-secondary rounded-lg border border-border p-1">
        {(
          [
            { id: 'overview', label: 'Overview', icon: Bot },
            { id: 'models', label: 'Models', icon: Cpu },
            { id: 'tools', label: 'Tools', icon: Wrench },
            { id: 'settings', label: 'Settings', icon: Activity },
          ] as const
        ).map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={clsx(
              'flex items-center gap-2 px-4 py-2 rounded text-sm font-medium transition-colors flex-1 justify-center',
              tab === id
                ? 'bg-accent/20 text-accent'
                : 'text-slate-500 hover:text-slate-300'
            )}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'overview' && (
        <div className="space-y-4">
          {/* Agent grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {agents.map((agent) => (
              <AgentCard
                key={agent.id}
                agent={agent}
                onClick={() => {
                  setActiveAgentId(agent.id)
                  navigate(`/agents/${agent.id}`)
                }}
              />
            ))}
            {agents.length === 0 && (
              <div className="col-span-3 py-16 text-center">
                <Bot className="w-12 h-12 mx-auto text-slate-700 mb-3" />
                <p className="text-slate-500">No agents yet. Create your first agent to get started.</p>
              </div>
            )}
          </div>

          {/* Recent events */}
          {recentEvents.length > 0 && (
            <div className="bg-bg-secondary rounded-xl border border-border p-4">
              <h3 className="text-sm font-semibold text-slate-300 mb-3">Recent Events</h3>
              <div className="space-y-1">
                {recentEvents.map((ev, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs font-mono text-slate-500">
                    <span className="text-slate-700">
                      {new Date(ev.timestamp).toLocaleTimeString()}
                    </span>
                    <span className="text-slate-400">{ev.type}</span>
                    {ev.agent_id && (
                      <span className="text-slate-600">{ev.agent_id.slice(0, 8)}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'models' && <ModelManagement />}

      {tab === 'tools' && (
        <div className="h-[600px]">
          <ToolViewer />
        </div>
      )}

      {tab === 'settings' && <Settings />}
    </div>
  )
}

function StatCard({
  icon: Icon,
  label,
  value,
  accent = 'text-accent',
}: {
  icon: React.ElementType
  label: string
  value: number
  accent?: string
}) {
  return (
    <div className="bg-bg-tertiary rounded-lg p-4 flex items-center gap-3">
      <div className="w-10 h-10 rounded-lg bg-bg-secondary flex items-center justify-center">
        <Icon className={clsx('w-5 h-5', accent)} />
      </div>
      <div>
        <div className="text-2xl font-bold text-slate-100">{value}</div>
        <div className="text-xs text-slate-500">{label}</div>
      </div>
    </div>
  )
}

function AgentCard({ agent, onClick }: { agent: Agent; onClick: () => void }) {
  return (
    <div
      onClick={onClick}
      className="bg-bg-tertiary rounded-xl border border-border p-4 cursor-pointer hover:border-accent/50 transition-colors"
    >
      <div className="flex items-center gap-2 mb-3">
        <span
          className={clsx(
            'w-2.5 h-2.5 rounded-full flex-shrink-0',
            STATE_COLORS[agent.state] ?? 'bg-state-idle'
          )}
        />
        <span className="font-medium text-slate-200 truncate">{agent.name}</span>
        <span className="ml-auto text-xs text-slate-500 font-mono">{agent.state}</span>
      </div>
      <p className="text-xs text-slate-500 line-clamp-2">{agent.masterprompt}</p>
      <div className="mt-3 text-xs text-slate-600 font-mono">{agent.model_name}</div>
    </div>
  )
}
