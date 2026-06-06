import { useState, useEffect } from 'react'
import { ChevronDown, ChevronRight, CheckCircle, XCircle, Clock, Zap } from 'lucide-react'
import clsx from 'clsx'
import { format } from 'date-fns'
import { agentsApi } from '../api/agents'
import type { Iteration } from '../types'

interface Props {
  agentId: string
}

const STATUS_ICON = {
  success: <CheckCircle className="w-4 h-4 text-green-400" />,
  failed: <XCircle className="w-4 h-4 text-red-400" />,
  pending: <Clock className="w-4 h-4 text-yellow-400 animate-spin-slow" />,
  paused: <Clock className="w-4 h-4 text-yellow-400" />,
  stopped: <XCircle className="w-4 h-4 text-slate-400" />,
}

const STATUS_BADGE: Record<string, string> = {
  success: 'bg-green-900/40 text-green-400 border-green-800/30',
  failed: 'bg-red-900/40 text-red-400 border-red-800/30',
  pending: 'bg-yellow-900/40 text-yellow-400 border-yellow-800/30',
  paused: 'bg-yellow-900/40 text-yellow-400 border-yellow-800/30',
  stopped: 'bg-slate-700/40 text-slate-400 border-slate-600/30',
}

function IterationRow({ iter }: { iter: Iteration }) {
  const [expanded, setExpanded] = useState(false)

  const duration =
    iter.finished_at && iter.started_at
      ? ((new Date(iter.finished_at).getTime() - new Date(iter.started_at).getTime()) / 1000).toFixed(1)
      : null

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <div
        className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-bg-tertiary transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? (
          <ChevronDown className="w-4 h-4 text-slate-500 flex-shrink-0" />
        ) : (
          <ChevronRight className="w-4 h-4 text-slate-500 flex-shrink-0" />
        )}
        {STATUS_ICON[iter.status as keyof typeof STATUS_ICON] ?? STATUS_ICON.pending}
        <span className="font-mono text-sm text-slate-400 w-10 flex-shrink-0">#{iter.number}</span>
        <span className="flex-1 text-sm text-slate-300 truncate">{iter.goal ?? 'No goal'}</span>
        <span
          className={clsx(
            'text-xs px-2 py-0.5 rounded border font-mono',
            STATUS_BADGE[iter.status] ?? STATUS_BADGE.pending
          )}
        >
          {iter.status}
        </span>
        {iter.tokens_used > 0 && (
          <span className="flex items-center gap-1 text-xs text-slate-500 font-mono">
            <Zap className="w-3 h-3" />
            {iter.tokens_used.toLocaleString()}
          </span>
        )}
        {duration && (
          <span className="text-xs text-slate-600 font-mono">{duration}s</span>
        )}
        <span className="text-xs text-slate-600 font-mono">
          {format(new Date(iter.started_at), 'HH:mm:ss')}
        </span>
      </div>

      {expanded && (
        <div className="border-t border-border bg-bg-primary/30 px-4 py-3 space-y-3">
          {iter.plan_json && (
            <div>
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Plan</div>
              <div className="space-y-1">
                {iter.plan_json.steps?.map((step, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs font-mono text-slate-400">
                    <span className="text-slate-600 w-4 flex-shrink-0">{i + 1}.</span>
                    <span>{step.description}</span>
                    {step.tool_name && (
                      <span className="ml-auto text-accent">{step.tool_name}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {iter.result_json && (
            <div>
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Result</div>
              <div className="text-xs text-slate-300 font-mono bg-bg-secondary rounded p-2">
                {iter.result_json.summary ?? JSON.stringify(iter.result_json, null, 2)}
              </div>
            </div>
          )}

          {iter.tool_calls && iter.tool_calls.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                Tool Calls ({iter.tool_calls.length})
              </div>
              <div className="space-y-1">
                {iter.tool_calls.map((tc) => (
                  <div
                    key={tc.id}
                    className={clsx(
                      'flex items-center gap-2 text-xs font-mono px-2 py-1 rounded',
                      tc.success
                        ? 'bg-green-900/20 text-green-400'
                        : 'bg-red-900/20 text-red-400'
                    )}
                  >
                    {tc.success ? (
                      <CheckCircle className="w-3 h-3 flex-shrink-0" />
                    ) : (
                      <XCircle className="w-3 h-3 flex-shrink-0" />
                    )}
                    <span className="font-semibold">{tc.tool_name}</span>
                    <span className="text-slate-600 ml-auto">{Math.round(tc.duration_ms)}ms</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function IterationViewer({ agentId }: Props) {
  const [iterations, setIterations] = useState<Iteration[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(0)
  const PAGE_SIZE = 20

  useEffect(() => {
    setLoading(true)
    agentsApi
      .listIterations(agentId, PAGE_SIZE, page * PAGE_SIZE)
      .then((data) => setIterations(data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [agentId, page])

  return (
    <div className="flex flex-col h-full bg-bg-secondary rounded-xl border border-border overflow-hidden">
      <div className="px-4 py-2.5 border-b border-border flex items-center justify-between">
        <span className="text-sm font-medium text-slate-300">Iterations</span>
        <span className="text-xs text-slate-500 font-mono">{iterations.length} shown</span>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {loading && (
          <div className="text-center text-slate-500 text-sm py-8">Loading...</div>
        )}
        {!loading && iterations.length === 0 && (
          <div className="text-center text-slate-600 text-sm py-8">
            No iterations yet. Start the agent to begin.
          </div>
        )}
        {iterations.map((it) => (
          <IterationRow key={it.id} iter={it} />
        ))}
      </div>

      {/* Pagination */}
      <div className="px-4 py-2.5 border-t border-border flex gap-2 justify-end">
        <button
          onClick={() => setPage((p) => Math.max(0, p - 1))}
          disabled={page === 0}
          className="text-xs px-3 py-1.5 rounded bg-bg-tertiary text-slate-400 hover:text-slate-200 disabled:opacity-40"
        >
          Prev
        </button>
        <span className="text-xs text-slate-500 px-2 py-1.5 font-mono">Page {page + 1}</span>
        <button
          onClick={() => setPage((p) => p + 1)}
          disabled={iterations.length < PAGE_SIZE}
          className="text-xs px-3 py-1.5 rounded bg-bg-tertiary text-slate-400 hover:text-slate-200 disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  )
}
