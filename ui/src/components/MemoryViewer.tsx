import { useState, useEffect } from 'react'
import { Brain, RefreshCw, Hash } from 'lucide-react'
import clsx from 'clsx'
import { formatDistanceToNow } from 'date-fns'
import { memoryApi } from '../api/memory'
import type { MemoryEntry, MemoryType } from '../types'

interface Props {
  agentId: string
}

const TABS: { label: string; value: MemoryType; color: string }[] = [
  { label: 'Short-term', value: 'short', color: 'text-sky-400' },
  { label: 'Mid-term', value: 'mid', color: 'text-violet-400' },
  { label: 'Long-term', value: 'long', color: 'text-amber-400' },
]

function MemoryCard({ entry }: { entry: MemoryEntry }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <div
        className="flex items-start gap-3 px-3 py-2.5 cursor-pointer hover:bg-bg-tertiary transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-semibold text-slate-300 truncate">{entry.key}</span>
            <span className="flex items-center gap-1 text-xs text-slate-600 ml-auto flex-shrink-0">
              <Hash className="w-3 h-3" />
              {entry.access_count}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{entry.content}</p>
        </div>
      </div>
      {expanded && (
        <div className="border-t border-border bg-bg-primary/30 px-3 py-2.5 space-y-2">
          <pre className="text-xs text-slate-300 font-mono whitespace-pre-wrap break-words">
            {entry.content}
          </pre>
          {entry.metadata && Object.keys(entry.metadata).length > 0 && (
            <pre className="text-xs text-slate-500 font-mono">
              {JSON.stringify(entry.metadata, null, 2)}
            </pre>
          )}
          <div className="flex gap-4 text-xs text-slate-600 font-mono">
            <span>Created: {formatDistanceToNow(new Date(entry.created_at), { addSuffix: true })}</span>
            <span>Accessed: {formatDistanceToNow(new Date(entry.accessed_at), { addSuffix: true })}</span>
          </div>
        </div>
      )}
    </div>
  )
}

export default function MemoryViewer({ agentId }: Props) {
  const [tab, setTab] = useState<MemoryType>('short')
  const [entries, setEntries] = useState<MemoryEntry[]>([])
  const [counts, setCounts] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const [data, stats] = await Promise.all([
        memoryApi.list(agentId, tab, 100),
        memoryApi.stats(agentId),
      ])
      setEntries(data)
      setCounts(stats.counts_by_type)
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [agentId, tab])

  return (
    <div className="flex flex-col h-full bg-bg-secondary rounded-xl border border-border overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border">
        <Brain className="w-4 h-4 text-accent" />
        <span className="text-sm font-medium text-slate-300 flex-1">Memory</span>
        <button
          onClick={load}
          disabled={loading}
          className="text-slate-500 hover:text-slate-200 transition-colors disabled:opacity-40"
        >
          <RefreshCw className={clsx('w-3.5 h-3.5', loading && 'animate-spin')} />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border">
        {TABS.map(({ label, value, color }) => (
          <button
            key={value}
            onClick={() => setTab(value)}
            className={clsx(
              'flex-1 py-2.5 text-xs font-medium transition-colors',
              tab === value
                ? clsx('border-b-2 border-accent', color)
                : 'text-slate-500 hover:text-slate-300'
            )}
          >
            {label}
            {counts[value] !== undefined && (
              <span className="ml-1.5 text-xs font-mono opacity-70">({counts[value]})</span>
            )}
          </button>
        ))}
      </div>

      {/* Entries */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {loading && (
          <div className="text-center text-slate-500 text-sm py-8">Loading...</div>
        )}
        {!loading && entries.length === 0 && (
          <div className="text-center text-slate-600 text-sm py-8">
            No {tab}-term memory entries.
          </div>
        )}
        {entries.map((entry) => (
          <MemoryCard key={entry.id} entry={entry} />
        ))}
      </div>
    </div>
  )
}
