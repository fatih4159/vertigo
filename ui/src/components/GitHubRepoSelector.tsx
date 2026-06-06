import { useState, useEffect } from 'react'
import {
  Github,
  Search,
  Lock,
  Globe,
  ExternalLink,
  RefreshCw,
  ChevronRight,
  AlertCircle,
} from 'lucide-react'
import clsx from 'clsx'
import { useGitHub } from '../hooks/useGitHub'
import type { GitHubRepo } from '../types'

export default function GitHubRepoSelector() {
  const { user, repos, loading, error, fetchRepos, isConnected } = useGitHub()
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<GitHubRepo | null>(null)

  useEffect(() => {
    if (isConnected && repos.length === 0) {
      fetchRepos()
    }
  }, [isConnected])

  if (!isConnected) {
    return (
      <div className="bg-bg-secondary rounded-xl border border-border p-8 flex flex-col items-center gap-3 text-center">
        <Github className="w-10 h-10 text-slate-700" />
        <div>
          <p className="text-sm font-medium text-slate-400">GitHub not connected</p>
          <p className="text-xs text-slate-600 mt-1">
            Log in to GitHub in Settings to select a repository.
          </p>
        </div>
      </div>
    )
  }

  const filtered = repos.filter(
    (r) =>
      r.full_name.toLowerCase().includes(search.toLowerCase()) ||
      (r.description ?? '').toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="bg-bg-secondary rounded-xl border border-border overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border">
        <Github className="w-4 h-4 text-accent" />
        <span className="text-sm font-medium text-slate-300 flex-1">Repository</span>
        {user && (
          <span className="flex items-center gap-1.5 text-xs text-slate-500">
            <img src={user.avatar_url} alt={user.login} className="w-4 h-4 rounded-full" />
            {user.login}
          </span>
        )}
        <span className="text-xs text-slate-600 font-mono">{repos.length}</span>
        <button
          onClick={fetchRepos}
          disabled={loading}
          title="Refresh repos"
          className="ml-1 text-slate-500 hover:text-slate-200 transition-colors disabled:opacity-40"
        >
          <RefreshCw className={clsx('w-3.5 h-3.5', loading && 'animate-spin')} />
        </button>
      </div>

      {/* Selected repo banner */}
      {selected && (
        <div className="px-4 py-2.5 bg-accent/5 border-b border-border flex items-center gap-2">
          {selected.private ? (
            <Lock className="w-3.5 h-3.5 text-yellow-400 flex-shrink-0" />
          ) : (
            <Globe className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
          )}
          <span className="font-mono text-sm text-slate-200 flex-1 truncate">
            {selected.full_name}
          </span>
          <span className="text-xs text-slate-500 font-mono flex-shrink-0">
            {selected.default_branch}
          </span>
          <a
            href={selected.html_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-slate-500 hover:text-accent transition-colors flex-shrink-0"
            title="Open on GitHub"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      )}

      <div className="p-3 space-y-2">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-600 pointer-events-none" />
          <input
            type="text"
            placeholder="Search repositories..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-bg-tertiary border border-border rounded-lg pl-8 pr-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-accent placeholder-slate-700"
          />
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-center gap-2 text-xs text-red-400 px-1">
            <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
            {error}
          </div>
        )}

        {/* Repo list */}
        <div className="max-h-80 overflow-y-auto space-y-0.5 pr-0.5">
          {filtered.map((repo) => (
            <button
              key={repo.id}
              onClick={() => setSelected(repo)}
              className={clsx(
                'w-full text-left px-3 py-2 rounded-lg text-sm transition-colors flex items-start gap-2 group',
                selected?.id === repo.id
                  ? 'bg-accent/20 text-accent'
                  : 'text-slate-400 hover:bg-bg-tertiary hover:text-slate-200'
              )}
            >
              {repo.private ? (
                <Lock className="w-3 h-3 mt-0.5 text-yellow-400 flex-shrink-0" />
              ) : (
                <Globe className="w-3 h-3 mt-0.5 text-slate-600 flex-shrink-0" />
              )}
              <div className="min-w-0 flex-1">
                <div className="font-medium truncate">{repo.full_name}</div>
                {repo.description && (
                  <div className="text-xs text-slate-500 truncate mt-0.5">{repo.description}</div>
                )}
              </div>
              <ChevronRight
                className={clsx(
                  'w-3.5 h-3.5 flex-shrink-0 mt-0.5 transition-opacity',
                  selected?.id === repo.id ? 'opacity-100' : 'opacity-0 group-hover:opacity-50'
                )}
              />
            </button>
          ))}

          {filtered.length === 0 && !loading && (
            <div className="text-center py-6 text-xs text-slate-600">
              {repos.length === 0
                ? 'Click refresh to load your repositories'
                : 'No repositories match your search'}
            </div>
          )}

          {loading && repos.length === 0 && (
            <div className="text-center py-6 text-xs text-slate-600">Loading repositories…</div>
          )}
        </div>
      </div>
    </div>
  )
}
