import { useState } from 'react'
import { ChevronDown, ChevronRight, Trash2 } from 'lucide-react'
import clsx from 'clsx'
import { format } from 'date-fns'
import type { WsEvent } from '../types'

interface Props {
  events: WsEvent[]
  onClear: () => void
  filterAgentId?: string
}

const EVENT_COLORS: Record<string, string> = {
  iteration_start: 'text-sky-400 bg-sky-900/20 border-sky-800/30',
  iteration_end: 'text-green-400 bg-green-900/20 border-green-800/30',
  tool_call: 'text-violet-400 bg-violet-900/20 border-violet-800/30',
  tool_result: 'text-indigo-400 bg-indigo-900/20 border-indigo-800/30',
  state_change: 'text-yellow-400 bg-yellow-900/20 border-yellow-800/30',
  error: 'text-red-400 bg-red-900/20 border-red-800/30',
  chat: 'text-teal-400 bg-teal-900/20 border-teal-800/30',
  memory: 'text-orange-400 bg-orange-900/20 border-orange-800/30',
  default: 'text-slate-400 bg-slate-800/30 border-slate-700/30',
}

function getEventColor(type: string): string {
  for (const key of Object.keys(EVENT_COLORS)) {
    if (type.includes(key)) return EVENT_COLORS[key]
  }
  return EVENT_COLORS.default
}

function EventRow({ event }: { event: WsEvent }) {
  const [expanded, setExpanded] = useState(false)
  const colorClass = getEventColor(event.type)
  const hasData = event.data && Object.keys(event.data).length > 0

  return (
    <div className={clsx('rounded-lg border text-xs font-mono', colorClass)}>
      <div
        className="flex items-center gap-2 px-3 py-1.5 cursor-pointer select-none"
        onClick={() => hasData && setExpanded(!expanded)}
      >
        {hasData ? (
          expanded ? (
            <ChevronDown className="w-3 h-3 flex-shrink-0" />
          ) : (
            <ChevronRight className="w-3 h-3 flex-shrink-0" />
          )
        ) : (
          <span className="w-3" />
        )}
        <span className="text-slate-500">
          {format(new Date(event.timestamp), 'HH:mm:ss.SSS')}
        </span>
        <span className="font-semibold">{event.type}</span>
        {event.agent_id && (
          <span className="text-slate-600 truncate max-w-[80px]">{event.agent_id.slice(0, 8)}</span>
        )}
        {/* Quick summary */}
        {!expanded && event.data && (
          <span className="text-slate-500 truncate flex-1">
            {getSummary(event)}
          </span>
        )}
      </div>

      {expanded && hasData && (
        <pre className="px-4 pb-2 text-slate-300 overflow-x-auto text-xs leading-5 border-t border-white/5 pt-2">
          {JSON.stringify(event.data, null, 2)}
        </pre>
      )}
    </div>
  )
}

function getSummary(event: WsEvent): string {
  const d = event.data
  if (!d) return ''
  if (d.tool_name) return `tool=${String(d.tool_name)} success=${String(d.success)}`
  if (d.state) return `→ ${String(d.state)}`
  if (d.goal) return String(d.goal).slice(0, 80)
  if (d.message) return String(d.message).slice(0, 80)
  const keys = Object.keys(d)
  return keys.slice(0, 3).map((k) => `${k}=${JSON.stringify(d[k])?.slice(0, 20)}`).join(' ')
}

export default function EventTimeline({ events, onClear, filterAgentId }: Props) {
  const [filter, setFilter] = useState('')

  const filtered = events
    .filter((e) => !filterAgentId || e.agent_id === filterAgentId || !e.agent_id)
    .filter((e) => !filter || e.type.toLowerCase().includes(filter.toLowerCase()))
    .slice()
    .reverse()

  return (
    <div className="flex flex-col h-full bg-bg-secondary rounded-xl border border-border overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border">
        <span className="text-sm font-medium text-slate-300 flex-1">Event Timeline</span>
        <span className="text-xs text-slate-500 font-mono">{events.length} events</span>
        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter..."
          className="bg-bg-tertiary border border-border rounded px-2 py-1 text-xs text-slate-300 focus:outline-none focus:border-accent w-24"
        />
        <button
          onClick={onClear}
          className="text-slate-500 hover:text-red-400 transition-colors"
          title="Clear events"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Events */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1">
        {filtered.length === 0 && (
          <div className="text-center text-slate-600 text-sm py-8">
            No events yet. Start an agent to see live events.
          </div>
        )}
        {filtered.map((ev, i) => (
          <EventRow key={`${ev.id}-${i}`} event={ev} />
        ))}
      </div>
    </div>
  )
}
