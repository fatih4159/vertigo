import { Menu, Wifi, WifiOff, Activity } from 'lucide-react'
import clsx from 'clsx'
import { useAppStore } from '../../store'

interface Props {
  wsConnected: boolean
}

export default function Header({ wsConnected }: Props) {
  const { setSidebarOpen, sidebarOpen, agents, activeAgentId } = useAppStore()
  const activeAgent = agents.find((a) => a.id === activeAgentId)

  return (
    <header className="h-12 bg-bg-secondary border-b border-border flex items-center px-4 gap-3 flex-shrink-0">
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="text-slate-400 hover:text-slate-200 transition-colors"
      >
        <Menu className="w-5 h-5" />
      </button>

      <div className="flex-1 min-w-0">
        {activeAgent ? (
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-slate-200 truncate">{activeAgent.name}</span>
            <span
              className={clsx(
                'text-xs px-2 py-0.5 rounded-full font-mono',
                stateClass(activeAgent.state)
              )}
            >
              {activeAgent.state}
            </span>
            <span className="text-xs text-slate-500 font-mono">{activeAgent.model_name}</span>
          </div>
        ) : (
          <span className="text-sm text-slate-500">AAOS — AGI Agent Operating System</span>
        )}
      </div>

      <div className="flex items-center gap-3">
        {/* WS indicator */}
        <div
          className={clsx(
            'flex items-center gap-1.5 text-xs',
            wsConnected ? 'text-state-running' : 'text-state-stopped'
          )}
          title={wsConnected ? 'WebSocket connected' : 'WebSocket disconnected'}
        >
          {wsConnected ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
          <span className="hidden sm:inline">{wsConnected ? 'Live' : 'Offline'}</span>
        </div>

        <Activity className="w-4 h-4 text-slate-500" />
      </div>
    </header>
  )
}

function stateClass(state: string): string {
  const map: Record<string, string> = {
    IDLE: 'bg-slate-700 text-slate-300',
    RUNNING: 'bg-green-900/50 text-green-400',
    PAUSED: 'bg-yellow-900/50 text-yellow-400',
    STOPPED: 'bg-red-900/50 text-red-400',
    ERROR: 'bg-red-900/50 text-red-400',
    THINKING: 'bg-violet-900/50 text-violet-400',
    EXECUTING: 'bg-sky-900/50 text-sky-400',
  }
  return map[state] ?? 'bg-slate-700 text-slate-300'
}
