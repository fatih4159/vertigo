import { useState, useEffect } from 'react'
import {
  FolderGit2, Github, RefreshCw, Link, GitBranch,
  CheckCircle2, Loader2, AlertCircle, Search, X, FolderOpen,
} from 'lucide-react'
import clsx from 'clsx'
import { useGitHub } from '../hooks/useGitHub'
import { agentsApi } from '../api/agents'
import type { Agent, GitHubRepo } from '../types'

interface Props {
  agent: Agent
  onUpdate: (agent: Agent) => void
}

export default function RepoPanel({ agent, onUpdate }: Props) {
  const { repos, fetchRepos, loading: ghLoading, isConnected, user } = useGitHub()

  const [repoUrl, setRepoUrl] = useState(agent.repository_url ?? '')
  const [branch, setBranch] = useState(agent.repository_branch ?? '')
  const [search, setSearch] = useState('')
  const [showPicker, setShowPicker] = useState(false)
  const [saving, setSaving] = useState(false)
  const [settingUp, setSettingUp] = useState(false)
  const [msg, setMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)

  // Load repos once when picker opens
  useEffect(() => {
    if (showPicker && repos.length === 0 && isConnected) {
      fetchRepos()
    }
  }, [showPicker, isConnected, repos.length, fetchRepos])

  const flash = (type: 'ok' | 'err', text: string) => {
    setMsg({ type, text })
    setTimeout(() => setMsg(null), 4000)
  }

  const handleSelectRepo = (r: GitHubRepo) => {
    setRepoUrl(r.html_url)
    setBranch(r.default_branch)
    setSearch('')
    setShowPicker(false)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const updated = await agentsApi.update(agent.id, {
        repository_url: repoUrl || null,
        repository_branch: branch || null,
      })
      onUpdate(updated)
      flash('ok', 'Repository settings saved.')
    } catch (e) {
      flash('err', e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const handleSetup = async () => {
    setSettingUp(true)
    try {
      const result = await agentsApi.setupRepository(agent.id)
      const updated = await agentsApi.get(agent.id)
      onUpdate(updated)
      flash('ok', `${result.status === 'cloned' ? 'Cloned' : 'Pulled'} — ${result.file_count} files indexed.`)
    } catch (e) {
      flash('err', e instanceof Error ? e.message : 'Setup failed')
    } finally {
      setSettingUp(false)
    }
  }

  const filtered = repos.filter(
    (r) =>
      !search ||
      r.full_name.toLowerCase().includes(search.toLowerCase()) ||
      (r.description ?? '').toLowerCase().includes(search.toLowerCase())
  )

  const isDirty =
    (repoUrl || '') !== (agent.repository_url ?? '') ||
    (branch || '') !== (agent.repository_branch ?? '')

  return (
    <div className="space-y-4 max-w-2xl">
      {/* Current workspace status */}
      {agent.workspace_path && (
        <div className="bg-bg-secondary rounded-xl border border-border p-4 flex items-start gap-3">
          <FolderOpen className="w-4 h-4 text-accent mt-0.5 flex-shrink-0" />
          <div className="min-w-0">
            <div className="text-sm font-medium text-slate-200">Workspace ready</div>
            <div className="text-xs text-slate-500 font-mono truncate mt-0.5">{agent.workspace_path}</div>
            {agent.workspace_file_count != null && (
              <div className="text-xs text-slate-600 mt-1">{agent.workspace_file_count} files indexed</div>
            )}
          </div>
        </div>
      )}

      {/* Repository URL */}
      <div className="bg-bg-secondary rounded-xl border border-border overflow-hidden">
        <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
          <FolderGit2 className="w-4 h-4 text-accent" />
          <span className="text-sm font-medium text-slate-300 flex-1">Repository</span>
        </div>

        <div className="p-4 space-y-3">
          {/* URL row */}
          <div className="space-y-1.5">
            <label className="text-xs text-slate-500">Repository URL</label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Link className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
                <input
                  type="text"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  placeholder="https://github.com/owner/repo"
                  className="w-full bg-bg-tertiary border border-border rounded-lg pl-8 pr-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-accent font-mono"
                />
              </div>
              {isConnected && (
                <button
                  onClick={() => setShowPicker((v) => !v)}
                  className={clsx(
                    'flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium border transition-colors flex-shrink-0',
                    showPicker
                      ? 'bg-accent/20 border-accent text-accent'
                      : 'border-border text-slate-400 hover:border-border-hover hover:text-slate-200'
                  )}
                >
                  <Github className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Browse</span>
                </button>
              )}
            </div>
          </div>

          {/* Branch */}
          <div className="space-y-1.5">
            <label className="text-xs text-slate-500">Branch (leave blank for default)</label>
            <div className="relative">
              <GitBranch className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
              <input
                type="text"
                value={branch}
                onChange={(e) => setBranch(e.target.value)}
                placeholder="main"
                className="w-full bg-bg-tertiary border border-border rounded-lg pl-8 pr-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-accent font-mono"
              />
            </div>
          </div>

          {/* GitHub repo picker */}
          {showPicker && (
            <div className="border border-border rounded-xl overflow-hidden bg-bg-tertiary">
              <div className="flex items-center gap-2 px-3 py-2 border-b border-border">
                <Search className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder={`Search ${user?.login}'s repos…`}
                  className="flex-1 bg-transparent text-sm text-slate-200 placeholder-slate-600 focus:outline-none"
                  autoFocus
                />
                <button onClick={() => { setShowPicker(false); setSearch('') }}>
                  <X className="w-3.5 h-3.5 text-slate-500 hover:text-slate-300" />
                </button>
                <button
                  onClick={fetchRepos}
                  disabled={ghLoading}
                  className="text-slate-500 hover:text-slate-300 transition-colors"
                  title="Refresh"
                >
                  <RefreshCw className={clsx('w-3.5 h-3.5', ghLoading && 'animate-spin')} />
                </button>
              </div>
              <div className="max-h-60 overflow-y-auto divide-y divide-border">
                {ghLoading && repos.length === 0 ? (
                  <div className="flex items-center justify-center py-8 text-slate-500 gap-2 text-sm">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Loading repositories…
                  </div>
                ) : filtered.length === 0 ? (
                  <div className="py-6 text-center text-slate-500 text-sm">No repositories found</div>
                ) : (
                  filtered.map((r) => (
                    <button
                      key={r.id}
                      onClick={() => handleSelectRepo(r)}
                      className="w-full text-left px-3 py-2.5 hover:bg-bg-secondary transition-colors flex items-start gap-2"
                    >
                      <Github className="w-3.5 h-3.5 text-slate-500 mt-0.5 flex-shrink-0" />
                      <div className="min-w-0 flex-1">
                        <div className="text-sm text-slate-200 truncate font-mono">{r.full_name}</div>
                        {r.description && (
                          <div className="text-xs text-slate-500 truncate mt-0.5">{r.description}</div>
                        )}
                      </div>
                      <span className="text-xs text-slate-600 flex-shrink-0 font-mono">{r.default_branch}</span>
                    </button>
                  ))
                )}
              </div>
            </div>
          )}

          {/* Not connected hint */}
          {!isConnected && (
            <p className="text-xs text-slate-500">
              Connect GitHub in{' '}
              <a href="/settings" className="text-accent underline">Settings</a>{' '}
              to browse your repositories.
            </p>
          )}

          {/* Action buttons */}
          <div className="flex gap-2 pt-1">
            <button
              onClick={handleSave}
              disabled={saving || !isDirty}
              className="flex items-center gap-1.5 px-3 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg text-xs font-medium transition-colors disabled:opacity-40"
            >
              {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
              Save
            </button>

            <button
              onClick={handleSetup}
              disabled={settingUp || !agent.repository_url || isDirty}
              className="flex items-center gap-1.5 px-3 py-2 bg-bg-tertiary hover:bg-bg-secondary border border-border hover:border-accent/50 text-slate-300 rounded-lg text-xs font-medium transition-colors disabled:opacity-40"
              title={isDirty ? 'Save first' : 'Clone or pull the repository into a local workspace'}
            >
              {settingUp ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <RefreshCw className="w-3.5 h-3.5" />
              )}
              {agent.workspace_path ? 'Pull & Re-index' : 'Clone & Index'}
            </button>
          </div>

          {/* Feedback */}
          {msg && (
            <div
              className={clsx(
                'flex items-center gap-2 text-xs rounded-lg px-3 py-2',
                msg.type === 'ok'
                  ? 'bg-green-900/20 border border-green-800/40 text-green-400'
                  : 'bg-red-900/20 border border-red-800/40 text-red-400'
              )}
            >
              {msg.type === 'ok' ? (
                <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" />
              ) : (
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
              )}
              {msg.text}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
