import { NavLink, useNavigate } from 'react-router-dom'
import {
  Brain,
  LayoutDashboard,
  Settings,
  Cpu,
  Plus,
  Trash2,
} from 'lucide-react'
import clsx from 'clsx'
import { useAppStore } from '../../store'
import { agentsApi } from '../../api/agents'
import { useState } from 'react'

export default function Sidebar() {
  const { agents, activeAgentId, setActiveAgentId, sidebarOpen, setSidebarOpen, setAgents } = useAppStore()
  const navigate = useNavigate()
  const [creating, setCreating] = useState(false)

  if (!sidebarOpen) return null

  const closeMobile = () => {
    if (window.innerWidth < 768) setSidebarOpen(false)
  }

  const handleNewAgent = async () => {
    setCreating(true)
    try {
      const agent = await agentsApi.create({
        name: `Agent-${Date.now().toString(36)}`,
        masterprompt: 'You are an autonomous agent. Help the user accomplish their goals.',
        model_name: 'qwen2.5-coder:latest',
      })
      const all = await agentsApi.list()
      setAgents(all)
      setActiveAgentId(agent.id)
      navigate(`/agents/${agent.id}`)
      closeMobile()
    } catch (err) {
      console.error(err)
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    try {
      await agentsApi.delete(id)
      const all = await agentsApi.list()
      setAgents(all)
      if (activeAgentId === id) {
        setActiveAgentId(null)
        navigate('/dashboard')
      }
    } catch (err) {
      console.error(err)
    }
  }

  return (
    <>
    {/* Tap-to-close backdrop on mobile */}
    <div
      className="md:hidden fixed inset-0 bg-black/50 z-10"
      onClick={() => setSidebarOpen(false)}
    />
    <aside className="fixed left-0 top-0 h-screen w-64 bg-bg-secondary border-r border-border flex flex-col z-20">
      {/* Logo */}
      <div className="flex items-center gap-2 px-4 py-4 border-b border-border">
        <Cpu className="text-accent w-6 h-6 flex-shrink-0" />
        <div>
          <div className="font-bold text-sm text-slate-100">AAOS</div>
          <div className="text-xs text-slate-500">AGI Agent OS</div>
        </div>
      </div>

      {/* Nav */}
      <nav className="p-2 space-y-1">
        <NavLink
          to="/dashboard"
          onClick={closeMobile}
          className={({ isActive }) =>
            clsx(
              'flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors',
              isActive
                ? 'bg-accent/20 text-accent'
                : 'text-slate-400 hover:bg-bg-tertiary hover:text-slate-200'
            )
          }
        >
          <LayoutDashboard className="w-4 h-4" />
          Dashboard
        </NavLink>
      </nav>

      {/* Agents section */}
      <div className="px-3 pt-4 pb-2 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Agents
        </span>
        <button
          onClick={handleNewAgent}
          disabled={creating}
          className="w-5 h-5 rounded flex items-center justify-center text-slate-400 hover:text-accent hover:bg-accent/10 transition-colors disabled:opacity-50"
          title="New agent"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 space-y-0.5">
        {agents.map((agent) => (
          <div key={agent.id} className="group relative">
            <NavLink
              to={`/agents/${agent.id}`}
              onClick={() => { setActiveAgentId(agent.id); closeMobile() }}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors w-full',
                  isActive
                    ? 'bg-accent/20 text-accent'
                    : 'text-slate-400 hover:bg-bg-tertiary hover:text-slate-200'
                )
              }
            >
              <StateIndicator state={agent.state} />
              <span className="flex-1 truncate">{agent.name}</span>
              <button
                onClick={(e) => handleDelete(agent.id, e)}
                className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 transition-all"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </NavLink>

            {/* Memory sub-link */}
            <NavLink
              to={`/memory/${agent.id}`}
              onClick={closeMobile}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-2 pl-8 pr-3 py-1 rounded text-xs transition-colors',
                  isActive
                    ? 'text-accent'
                    : 'text-slate-500 hover:text-slate-300'
                )
              }
            >
              <Brain className="w-3 h-3" />
              Memory
            </NavLink>
          </div>
        ))}

        {agents.length === 0 && (
          <div className="px-3 py-4 text-xs text-slate-500 text-center">
            No agents yet. Click + to create one.
          </div>
        )}
      </div>

      {/* Bottom */}
      <div className="p-2 border-t border-border">
        <NavLink
          to="/settings"
          onClick={closeMobile}
          className={({ isActive }) =>
            clsx(
              'flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors',
              isActive
                ? 'bg-accent/20 text-accent'
                : 'text-slate-400 hover:bg-bg-tertiary hover:text-slate-200'
            )
          }
        >
          <Settings className="w-4 h-4" />
          Settings
        </NavLink>
      </div>
    </aside>
    </>
  )
}

function StateIndicator({ state }: { state: string }) {
  const colorMap: Record<string, string> = {
    IDLE: 'bg-state-idle',
    RUNNING: 'bg-state-running animate-pulse',
    PAUSED: 'bg-state-paused',
    STOPPED: 'bg-state-stopped',
    ERROR: 'bg-state-error',
    THINKING: 'bg-state-thinking animate-pulse',
    EXECUTING: 'bg-state-executing animate-pulse',
  }
  return (
    <span
      className={clsx('w-2 h-2 rounded-full flex-shrink-0', colorMap[state] ?? 'bg-state-idle')}
    />
  )
}
