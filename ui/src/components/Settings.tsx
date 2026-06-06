import { useState } from 'react'
import { Settings2, Save } from 'lucide-react'
import { useAppStore } from '../store'
import type { Settings as SettingsType } from '../types'

export default function Settings() {
  const { settings, updateSettings } = useAppStore()
  const [draft, setDraft] = useState<SettingsType>({ ...settings })
  const [saved, setSaved] = useState(false)

  const handleSave = () => {
    updateSettings(draft)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const field = (key: keyof SettingsType) => ({
    value: draft[key] as string | number,
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = e.target.type === 'number' ? parseInt(e.target.value) : e.target.value
      setDraft((prev) => ({ ...prev, [key]: val }))
    },
  })

  return (
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
