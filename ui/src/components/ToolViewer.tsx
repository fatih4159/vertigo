import { useState, useEffect } from 'react'
import { Wrench, Play, ChevronDown, ChevronRight } from 'lucide-react'
import clsx from 'clsx'
import { toolsApi } from '../api/tools'
import type { Tool, ToolExecuteResult } from '../types'

function ToolCard({ tool }: { tool: Tool }) {
  const [expanded, setExpanded] = useState(false)
  const [running, setRunning] = useState(false)
  const [argsJson, setArgsJson] = useState('{}')
  const [result, setResult] = useState<ToolExecuteResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleRun = async () => {
    setRunning(true)
    setError(null)
    setResult(null)
    try {
      const args = JSON.parse(argsJson)
      const res = await toolsApi.execute(tool.name, args)
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setRunning(false)
    }
  }

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
        <Wrench className="w-4 h-4 text-accent flex-shrink-0" />
        <span className="font-mono text-sm font-medium text-slate-200">{tool.name}</span>
        {tool.category && (
          <span className="text-xs px-2 py-0.5 bg-bg-tertiary text-slate-500 rounded border border-border font-mono">
            {tool.category}
          </span>
        )}
        <span className="flex-1 text-xs text-slate-500 truncate ml-2">{tool.description}</span>
      </div>

      {expanded && (
        <div className="border-t border-border bg-bg-primary/30 px-4 py-3 space-y-3">
          <p className="text-sm text-slate-400">{tool.description}</p>

          {tool.input_schema && Object.keys(tool.input_schema).length > 0 && (
            <div>
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">
                Input Schema
              </div>
              <pre className="text-xs font-mono text-slate-400 bg-bg-secondary rounded p-2 overflow-x-auto">
                {JSON.stringify(tool.input_schema, null, 2)}
              </pre>
            </div>
          )}

          {/* Manual execution */}
          <div className="space-y-2">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Execute
            </div>
            <textarea
              value={argsJson}
              onChange={(e) => setArgsJson(e.target.value)}
              rows={3}
              className="w-full bg-bg-secondary border border-border rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-accent resize-none"
              placeholder='{"arg": "value"}'
            />
            <button
              onClick={handleRun}
              disabled={running}
              className="flex items-center gap-2 px-3 py-1.5 bg-accent hover:bg-accent-hover text-white rounded-lg text-xs font-medium transition-colors disabled:opacity-40"
            >
              <Play className="w-3 h-3" />
              {running ? 'Running...' : 'Run'}
            </button>
          </div>

          {error && (
            <div className="text-xs text-red-400 bg-red-900/20 border border-red-800/30 rounded px-3 py-2">
              {error}
            </div>
          )}

          {result && (
            <div
              className={clsx(
                'rounded-lg border p-3',
                result.success
                  ? 'bg-green-900/20 border-green-800/30'
                  : 'bg-red-900/20 border-red-800/30'
              )}
            >
              <div className="text-xs font-semibold mb-1.5">
                {result.success ? (
                  <span className="text-green-400">Success ({result.duration_ms.toFixed(1)}ms)</span>
                ) : (
                  <span className="text-red-400">Failed: {result.error}</span>
                )}
              </div>
              {result.output && (
                <pre className="text-xs font-mono text-slate-300 whitespace-pre-wrap break-words max-h-40 overflow-y-auto">
                  {result.output}
                </pre>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function ToolViewer() {
  const [tools, setTools] = useState<Tool[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')

  useEffect(() => {
    toolsApi
      .list()
      .then(setTools)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const filtered = tools.filter(
    (t) =>
      !filter ||
      t.name.toLowerCase().includes(filter.toLowerCase()) ||
      t.description?.toLowerCase().includes(filter.toLowerCase())
  )

  return (
    <div className="flex flex-col h-full bg-bg-secondary rounded-xl border border-border overflow-hidden">
      <div className="flex items-center gap-3 px-4 py-2.5 border-b border-border">
        <Wrench className="w-4 h-4 text-accent" />
        <span className="text-sm font-medium text-slate-300 flex-1">Tools ({tools.length})</span>
        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter tools..."
          className="bg-bg-tertiary border border-border rounded px-2 py-1 text-xs text-slate-300 focus:outline-none focus:border-accent w-32"
        />
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {loading && (
          <div className="text-center text-slate-500 text-sm py-8">Loading tools...</div>
        )}
        {!loading && filtered.length === 0 && (
          <div className="text-center text-slate-600 text-sm py-8">No tools found.</div>
        )}
        {filtered.map((tool) => (
          <ToolCard key={tool.name} tool={tool} />
        ))}
      </div>
    </div>
  )
}
