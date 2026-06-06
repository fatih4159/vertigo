import { useParams } from 'react-router-dom'
import { useState } from 'react'
import {
  Terminal,
  MessageSquare,
  History,
  Activity,
  FileCode,
  GitBranch,
  Bot,
} from 'lucide-react'
import clsx from 'clsx'
import { useAgent } from '../hooks/useAgent'
import { useAppStore } from '../store'
import AgentConsole from '../components/AgentConsole'
import Chat from '../components/Chat'
import MasterpromptEditor from '../components/MasterpromptEditor'
import IterationViewer from '../components/IterationViewer'
import EventTimeline from '../components/EventTimeline'
import LogsPanel from '../components/LogsPanel'
import ErrorPanel from '../components/ErrorPanel'
import GitStatus from '../components/GitStatus'
import { agentsApi } from '../api/agents'

type Tab = 'console' | 'chat' | 'masterprompt' | 'iterations' | 'events' | 'logs' | 'git'

const TABS: { id: Tab; label: string; icon: React.ElementType }[] = [
  { id: 'console', label: 'Console', icon: Terminal },
  { id: 'chat', label: 'Chat', icon: MessageSquare },
  { id: 'masterprompt', label: 'Masterprompt', icon: FileCode },
  { id: 'iterations', label: 'Iterations', icon: History },
  { id: 'events', label: 'Events', icon: Activity },
  { id: 'logs', label: 'Logs', icon: Terminal },
  { id: 'git', label: 'Git', icon: GitBranch },
]

export default function AgentPage() {
  const { agentId } = useParams<{ agentId: string }>()
  const { agent, start, pause, resume, stop, chat } = useAgent(agentId ?? null)
  const { wsEvents, clearWsEvents, updateAgent } = useAppStore()
  const [tab, setTab] = useState<Tab>('console')

  if (!agentId) return <div className="text-slate-500 p-8">No agent ID</div>

  if (!agent) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <Bot className="w-12 h-12 mx-auto text-slate-700 mb-3" />
          <p className="text-slate-500">Loading agent...</p>
        </div>
      </div>
    )
  }

  // Filter events for this agent
  const agentEvents = wsEvents.filter(
    (e) => e.agent_id === agentId || e.agent_id === null
  )

  const errorEvents = agentEvents.filter(
    (e) =>
      e.type === 'error' ||
      e.type.includes('error') ||
      (e.data as Record<string, unknown>)?.level === 'ERROR'
  )

  const handleSaveMasterprompt = async (value: string) => {
    await agentsApi.update(agentId, { masterprompt: value })
    const updated = await agentsApi.get(agentId)
    updateAgent(updated)
  }

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Error panel at top if any */}
      {errorEvents.length > 0 && (
        <ErrorPanel events={errorEvents} />
      )}

      {/* Tab bar */}
      <div className="flex gap-1 bg-bg-secondary rounded-lg border border-border p-1 overflow-x-auto flex-shrink-0">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={clsx(
              'flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium whitespace-nowrap transition-colors',
              tab === id
                ? 'bg-accent/20 text-accent'
                : 'text-slate-500 hover:text-slate-300'
            )}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* Main content */}
      <div className="flex-1 min-h-0">
        {tab === 'console' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 h-full">
            <AgentConsole
              agent={agent}
              wsEvents={agentEvents}
              onStart={start}
              onPause={pause}
              onResume={resume}
              onStop={stop}
            />
            <div className="h-full">
              <EventTimeline
                events={agentEvents}
                onClear={clearWsEvents}
                filterAgentId={agentId}
              />
            </div>
          </div>
        )}

        {tab === 'chat' && (
          <div className="h-full">
            <Chat
              agentId={agentId}
              agentName={agent.name}
              onSend={chat}
            />
          </div>
        )}

        {tab === 'masterprompt' && (
          <div className="h-full">
            <MasterpromptEditor
              value={agent.masterprompt}
              onSave={handleSaveMasterprompt}
            />
          </div>
        )}

        {tab === 'iterations' && (
          <div className="h-full">
            <IterationViewer agentId={agentId} />
          </div>
        )}

        {tab === 'events' && (
          <div className="h-full">
            <EventTimeline
              events={agentEvents}
              onClear={clearWsEvents}
              filterAgentId={agentId}
            />
          </div>
        )}

        {tab === 'logs' && (
          <div className="h-full">
            <LogsPanel events={agentEvents} onClear={clearWsEvents} />
          </div>
        )}

        {tab === 'git' && (
          <div>
            <GitStatus agentId={agentId} />
          </div>
        )}
      </div>
    </div>
  )
}
