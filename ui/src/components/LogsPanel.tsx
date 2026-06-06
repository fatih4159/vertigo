import { useState, useEffect, useRef } from 'react'
import { Terminal, Trash2 } from 'lucide-react'
import clsx from 'clsx'
import type { WsEvent } from '../types'

interface Props {
  events: WsEvent[]
  onClear: () => void
}

const LOG_LEVEL_COLORS: Record<string, string> = {
  DEBUG: 'text-slate-500',
  INFO: 'text-sky-400',
  WARNING: 'text-yellow-400',
  ERROR: 'text-red-400',
  CRITICAL: 'text-red-500',
}

function formatEvent(event: WsEvent): { level: string; message: string; ts: string } {
  const d = event.data as Record<string, unknown>
  const level = (d.level as string) ?? (event.type === 'error' ? 'ERROR' : 'INFO')
  const message =
    (d.message as string) ??
    (d.error as string) ??
    `${event.type}: ${JSON.stringify(event.data).slice(0, 120)}`
  const ts = new Date(event.timestamp).toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
  return { level, message, ts }
}

export default function LogsPanel({ events, onClear }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)
  const [levelFilter, setLevelFilter] = useState<string>('ALL')

  useEffect(() => {
    if (autoScroll) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [events, autoScroll])

  const logEvents = events.filter(
    (e) =>
      levelFilter === 'ALL' ||
      (e.data as Record<string, unknown>)?.level === levelFilter ||
      (levelFilter === 'ERROR' && e.type === 'error')
  )

  return (
    <div className="flex flex-col h-full bg-bg-secondary rounded-xl border border-border overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border">
        <Terminal className="w-4 h-4 text-accent" />
        <span className="text-sm font-medium text-slate-300 flex-1">Logs</span>

        <select
          value={levelFilter}
          onChange={(e) => setLevelFilter(e.target.value)}
          className="bg-bg-tertiary border border-border rounded px-2 py-1 text-xs text-slate-300 focus:outline-none focus:border-accent"
        >
          {['ALL', 'DEBUG', 'INFO', 'WARNING', 'ERROR'].map((l) => (
            <option key={l} value={l}>{l}</option>
          ))}
        </select>

        <label className="flex items-center gap-1.5 text-xs text-slate-500 cursor-pointer">
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => setAutoScroll(e.target.checked)}
            className="rounded"
          />
          Auto
        </label>

        <button
          onClick={onClear}
          className="text-slate-500 hover:text-red-400 transition-colors"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 font-mono text-xs space-y-0.5">
        {logEvents.length === 0 && (
          <div className="text-slate-600 text-center py-8">No logs yet.</div>
        )}
        {logEvents.map((ev, i) => {
          const { level, message, ts } = formatEvent(ev)
          return (
            <div key={i} className="flex gap-3 leading-5">
              <span className="text-slate-600 flex-shrink-0">{ts}</span>
              <span
                className={clsx(
                  'flex-shrink-0 w-8',
                  LOG_LEVEL_COLORS[level] ?? 'text-slate-400'
                )}
              >
                {level.slice(0, 4)}
              </span>
              <span className="text-slate-300 break-all">{message}</span>
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
