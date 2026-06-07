import { useState, useMemo } from 'react'
import { Copy, Trash2, CheckSquare, Square, ChevronDown, ChevronRight, Check } from 'lucide-react'
import clsx from 'clsx'
import { useAppStore } from '../store'
import type { WsEvent } from '../types'

type FilterMode = 'errors' | 'warnings' | 'all'

function getLevel(ev: WsEvent): string {
  const d = ev.data as Record<string, unknown>
  if (d.level) return d.level as string
  const t = ev.type.toLowerCase()
  if (t === 'error' || t === 'error_occurred') return 'ERROR'
  if (t === 'warning') return 'WARNING'
  return 'INFO'
}

function isError(ev: WsEvent) {
  const lvl = getLevel(ev)
  return lvl === 'ERROR' || lvl === 'CRITICAL'
}

function isWarningOrAbove(ev: WsEvent) {
  const lvl = getLevel(ev)
  return lvl === 'ERROR' || lvl === 'CRITICAL' || lvl === 'WARNING'
}

function getMessage(ev: WsEvent): string {
  const d = ev.data as Record<string, unknown>
  return (d.message as string) ?? (d.error as string) ?? ev.type
}

function formatForCopy(ev: WsEvent): string {
  const ts = new Date(ev.timestamp).toLocaleTimeString('en-US', { hour12: false })
  const level = getLevel(ev)
  const msg = getMessage(ev)
  const agentPart = ev.agent_id ? ` [agent:${ev.agent_id.slice(0, 8)}]` : ''
  const data = ev.data as Record<string, unknown>
  const dataStr = Object.keys(data).length
    ? '\n  ' + JSON.stringify(data, null, 2).replace(/\n/g, '\n  ')
    : ''
  return `[${ts}] [${level}]${agentPart} ${msg}${dataStr}`
}

const LEVEL_COLOR: Record<string, string> = {
  ERROR: 'text-red-400',
  CRITICAL: 'text-red-500',
  WARNING: 'text-yellow-400',
  INFO: 'text-sky-400',
  DEBUG: 'text-slate-500',
}

export default function DebugTab() {
  const { wsEvents, clearWsEvents } = useAppStore()
  const [filter, setFilter] = useState<FilterMode>('errors')
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [copied, setCopied] = useState(false)

  const filtered = useMemo(() => {
    if (filter === 'errors') return wsEvents.filter(isError)
    if (filter === 'warnings') return wsEvents.filter(isWarningOrAbove)
    return wsEvents
  }, [wsEvents, filter])

  const allSelected = filtered.length > 0 && filtered.every((e) => selected.has(e.id))

  function toggleAll() {
    setSelected(allSelected ? new Set() : new Set(filtered.map((e) => e.id)))
  }

  function toggleOne(id: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function toggleExpand(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  async function copy(events: WsEvent[]) {
    await navigator.clipboard.writeText(events.map(formatForCopy).join('\n\n'))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const selectedEvents = filtered.filter((e) => selected.has(e.id))

  return (
    <div className="space-y-3">
      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value as FilterMode)}
          className="bg-bg-tertiary border border-border rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-accent"
        >
          <option value="errors">Errors only</option>
          <option value="warnings">Errors + Warnings</option>
          <option value="all">All events</option>
        </select>

        <button
          onClick={toggleAll}
          disabled={filtered.length === 0}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-border text-xs text-slate-400 hover:text-slate-200 hover:border-slate-500 transition-colors disabled:opacity-40"
        >
          {allSelected ? <CheckSquare className="w-3.5 h-3.5" /> : <Square className="w-3.5 h-3.5" />}
          {allSelected ? 'Deselect all' : 'Select all'}
        </button>

        <span className="text-xs text-slate-600">{filtered.length} entries</span>

        <div className="ml-auto flex items-center gap-2">
          {selectedEvents.length > 0 && (
            <button
              onClick={() => copy(selectedEvents)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-bg-tertiary hover:bg-bg-secondary border border-border text-slate-300 rounded-lg text-xs font-medium transition-colors"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
              Copy {selectedEvents.length} selected
            </button>
          )}
          <button
            onClick={() => copy(filtered)}
            disabled={filtered.length === 0}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-accent hover:bg-accent-hover text-white rounded-lg text-xs font-medium transition-colors disabled:opacity-40"
          >
            {copied && selectedEvents.length === 0 ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
            {copied && selectedEvents.length === 0 ? 'Copied!' : 'Copy all'}
          </button>
          <button
            onClick={() => { clearWsEvents(); setSelected(new Set()); setExpanded(new Set()) }}
            disabled={wsEvents.length === 0}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-slate-500 hover:text-red-400 border border-border hover:border-red-900/50 rounded-lg text-xs transition-colors disabled:opacity-40"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Clear
          </button>
        </div>
      </div>

      {/* Log list */}
      <div className="bg-bg-secondary rounded-xl border border-border overflow-hidden">
        {filtered.length === 0 ? (
          <div className="py-12 text-center text-sm text-slate-600">
            No {filter === 'all' ? '' : filter} logged.
          </div>
        ) : (
          <div className="divide-y divide-border max-h-[28rem] overflow-y-auto">
            {filtered.map((ev) => {
              const level = getLevel(ev)
              const message = getMessage(ev)
              const ts = new Date(ev.timestamp).toLocaleTimeString('en-US', {
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
              })
              const isExpanded = expanded.has(ev.id)
              const isChecked = selected.has(ev.id)

              return (
                <div key={ev.id} className={clsx('transition-colors', isChecked && 'bg-accent/5')}>
                  <div className="flex items-start gap-3 px-3 py-2.5">
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => toggleOne(ev.id)}
                      className="mt-0.5 flex-shrink-0 rounded accent-indigo-500 cursor-pointer"
                    />
                    <button
                      onClick={() => toggleExpand(ev.id)}
                      className="flex-shrink-0 mt-0.5 text-slate-600 hover:text-slate-400 transition-colors"
                    >
                      {isExpanded
                        ? <ChevronDown className="w-3.5 h-3.5" />
                        : <ChevronRight className="w-3.5 h-3.5" />}
                    </button>
                    <div className="flex-1 min-w-0 font-mono text-xs">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-slate-600 flex-shrink-0">{ts}</span>
                        <span className={clsx('font-semibold flex-shrink-0', LEVEL_COLOR[level] ?? 'text-slate-400')}>
                          {level}
                        </span>
                        {ev.agent_id && (
                          <span className="text-slate-600">agent:{ev.agent_id.slice(0, 8)}</span>
                        )}
                        <span className="text-slate-500">{ev.type}</span>
                      </div>
                      <div className="text-slate-300 mt-0.5 break-all">{message}</div>
                      {isExpanded && (
                        <pre className="mt-2 p-2 bg-bg-tertiary rounded text-slate-500 overflow-x-auto text-[10px] leading-relaxed whitespace-pre-wrap break-all">
                          {JSON.stringify(ev, null, 2)}
                        </pre>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
