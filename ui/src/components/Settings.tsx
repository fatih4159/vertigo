import { useState, useEffect } from 'react'
import { Settings2, Save, Github, CheckCircle2, LogOut, Loader2, AlertCircle } from 'lucide-react'
import { useAppStore } from '../store'
import { useGitHub } from '../hooks/useGitHub'
import type { Settings as SettingsType } from '../types'

export default function Settings() {
  const { settings, updateSettings } = useAppStore()
  const [draft, setDraft] = useState<SettingsType>({ ...settings })
  const [saved, setSaved] = useState(false)

  const { user, loading: ghLoading, error: ghError, connect, disconnect, isConnected } = useGitHub()
  const [tokenInput, setTokenInput] = useState('')

  const handleSave = () => {
    updateSettings(draft)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const field = (key: keyof Omit<SettingsType, 'githubToken'>) => ({
    value: draft[key] as string | number,
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = e.target.type === 'number' ? parseInt(e.target.value) : e.target.value
      setDraft((prev) => ({ ...prev, [key]: val }))
    },
  })

  const handleConnect = async () => {
    const token = tokenInput.trim()
    if (!token) return
    const u = await connect(token)
    if (u) setTokenInput('')
  }

  // Sync draft when settings change externally
  useEffect(() => {
    setDraft((prev) => ({ ...prev, ...settings }))
  }, [settings.githubToken])

  return (
    <div className="space-y-4">
      {/* Main settings card */}
      <div className="bg-bg-secondary rounded-xl border border-border overflow-hidden">
        <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
          <Settings2 className="w-4 h-4 text-accent" />
          <span className="text-sm font-medium text-slate-300 flex-1">Settings</span>
          {saved && <span className="text-xs text-green-400 font-mono">Saved!</span>}
          <button
            onClick={handleSave}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-accent hover:bg-accent-hover text-white rounded-lg text-xs font-medium transition-colors"
          >
            <Save className="w-3 h-3" />
            Save
          </button>
        </div>

        <div className="p-4 space-y-4">
          <FieldGroup label="Backend URL" description="Base URL for the API">
            <input
              type="text"
              className="w-full bg-bg-tertiary border border-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-accent font-mono"
              {...field('backendUrl')}
            />
          </FieldGroup>

          <FieldGroup label="WebSocket URL" description="WS URL (empty = auto-detect)">
            <input
              type="text"
              className="w-full bg-bg-tertiary border border-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-accent font-mono"
              placeholder="ws://localhost:8000/ws (auto)"
              {...field('wsUrl')}
            />
          </FieldGroup>

          <FieldGroup label="Default Model" description="Ollama model for new agents">
            <input
              type="text"
              className="w-full bg-bg-tertiary border border-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-accent font-mono"
              {...field('defaultModel')}
            />
          </FieldGroup>

          <FieldGroup label="Max Event History" description="Maximum WS events kept in memory">
            <input
              type="number"
              min={50}
              max={5000}
              className="w-full bg-bg-tertiary border border-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-accent font-mono"
              {...field('maxEventHistory')}
            />
          </FieldGroup>

          <FieldGroup label="Auto-scroll" description="Automatically scroll to latest events">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={draft.autoScroll}
                onChange={(e) => setDraft((prev) => ({ ...prev, autoScroll: e.target.checked }))}
                className="w-4 h-4 rounded accent-indigo-500"
              />
              <span className="text-sm text-slate-400">Enabled</span>
            </label>
          </FieldGroup>
        </div>
      </div>

      {/* GitHub integration card */}
      <div className="bg-bg-secondary rounded-xl border border-border overflow-hidden">
        <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
          <Github className="w-4 h-4 text-accent" />
          <span className="text-sm font-medium text-slate-300 flex-1">GitHub</span>
          {isConnected && (
            <span className="flex items-center gap-1 text-xs text-green-400">
              <CheckCircle2 className="w-3 h-3" />
              Connected
            </span>
          )}
        </div>

        <div className="p-4">
          {isConnected && user ? (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <img
                  src={user.avatar_url}
                  alt={user.login}
                  className="w-10 h-10 rounded-full border border-border"
                />
                <div>
                  <div className="text-sm font-medium text-slate-200">
                    {user.name ?? user.login}
                  </div>
                  <div className="text-xs text-slate-500 font-mono">@{user.login}</div>
                </div>
                <button
                  onClick={disconnect}
                  className="ml-auto flex items-center gap-1.5 px-3 py-1.5 bg-red-900/30 hover:bg-red-900/50 border border-red-800/40 text-red-400 rounded-lg text-xs font-medium transition-colors"
                >
                  <LogOut className="w-3 h-3" />
                  Disconnect
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-xs text-slate-500">
                Enter a GitHub Personal Access Token to enable repository access. Requires{' '}
                <code className="text-slate-400 bg-bg-tertiary px-1 py-0.5 rounded text-xs">repo</code>{' '}
                scope.
              </p>
              <div className="flex gap-2">
                <input
                  type="password"
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                  value={tokenInput}
                  onChange={(e) => setTokenInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleConnect()}
                  className="flex-1 bg-bg-tertiary border border-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-accent font-mono placeholder-slate-700"
                />
                <button
                  onClick={handleConnect}
                  disabled={ghLoading || !tokenInput.trim()}
                  className="flex items-center gap-1.5 px-3 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg text-xs font-medium transition-colors disabled:opacity-50"
                >
                  {ghLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Github className="w-3.5 h-3.5" />}
                  Connect
                </button>
              </div>
              {ghError && (
                <div className="flex items-center gap-2 text-xs text-red-400">
                  <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                  {ghError}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function FieldGroup({
  label,
  description,
  children,
}: {
  label: string
  description: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1.5">
      <div>
        <div className="text-sm font-medium text-slate-300">{label}</div>
        <div className="text-xs text-slate-500">{description}</div>
      </div>
      {children}
    </div>
  )
}
