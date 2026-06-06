import { useState } from 'react'
import { GitBranch, RefreshCw, AlertCircle } from 'lucide-react'
import clsx from 'clsx'
import { apiClient } from '../api/client'
import type { GitStatus as GitStatusType } from '../types'

interface Props {
  agentId: string
}

export default function GitStatus({ agentId: _agentId }: Props) {
  const [status, setStatus] = useState<GitStatusType | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await apiClient.get<GitStatusType>('/git/status')
      setStatus(res.data)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-bg-secondary rounded-xl border border-border overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border">
        <GitBranch className="w-4 h-4 text-accent" />
        <span className="text-sm font-medium text-slate-300 flex-1">Git Status</span>
        <button
          onClick={refresh}
          disabled={loading}
          className="text-slate-500 hover:text-slate-200 transition-colors disabled:opacity-40"
        >
          <RefreshCw className={clsx('w-3.5 h-3.5', loading && 'animate-spin')} />
        </button>
      </div>

      <div className="p-4">
        {!status && !error && (
          <button
            onClick={refresh}
            className="text-sm text-slate-500 hover:text-slate-300 transition-colors"
          >
            Click refresh to load git status
          </button>
        )}

        {error && (
          <div className="flex items-center gap-2 text-xs text-red-400">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        )}

        {status && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <GitBranch className="w-4 h-4 text-accent" />
              <span className="font-mono text-sm text-slate-200">{status.branch}</span>
              {status.is_dirty && (
                <span className="text-xs text-yellow-400 bg-yellow-900/20 border border-yellow-800/30 px-2 py-0.5 rounded">
                  dirty
                </span>
              )}
              {status.ahead > 0 && (
                <span className="text-xs text-green-400 font-mono">+{status.ahead}</span>
              )}
              {status.behind > 0 && (
                <span className="text-xs text-red-400 font-mono">-{status.behind}</span>
              )}
            </div>

            {status.staged.length > 0 && (
              <FileList label="Staged" files={status.staged} color="text-green-400" />
            )}
            {status.unstaged.length > 0 && (
              <FileList label="Modified" files={status.unstaged} color="text-yellow-400" />
            )}
            {status.untracked.length > 0 && (
              <FileList label="Untracked" files={status.untracked} color="text-slate-500" />
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function FileList({ label, files, color }: { label: string; files: string[]; color: string }) {
  return (
    <div>
      <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
        {label} ({files.length})
      </div>
      <div className="space-y-0.5">
        {files.map((f) => (
          <div key={f} className={clsx('font-mono text-xs', color)}>
            {f}
          </div>
        ))}
      </div>
    </div>
  )
}
