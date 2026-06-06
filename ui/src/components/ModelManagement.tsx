import { useState } from 'react'
import { Download, RefreshCw, CheckCircle, Cpu, HardDrive } from 'lucide-react'
import clsx from 'clsx'
import { useModels } from '../hooks/useModels'
import { modelsApi } from '../api/models'

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

export default function ModelManagement() {
  const { models, ollamaHealthy, refresh } = useModels()
  const [pullModel, setPullModel] = useState('')
  const [pulling, setPulling] = useState(false)
  const [pullProgress, setPullProgress] = useState<string | null>(null)
  const [pullPercent, setPullPercent] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const handlePull = async () => {
    const name = pullModel.trim()
    if (!name || pulling) return

    setPulling(true)
    setError(null)
    setPullProgress('Initializing...')
    setPullPercent(0)

    try {
      await modelsApi.pull(name, (event) => {
        setPullProgress(event.status)
        if (event.completed !== undefined && event.total) {
          setPullPercent(Math.round((event.completed / event.total) * 100))
        }
      })
      setPullModel('')
      setPullProgress('Complete!')
      await refresh()
      setTimeout(() => setPullProgress(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      setPullProgress(null)
    } finally {
      setPulling(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Ollama status */}
      <div className="bg-bg-secondary rounded-xl border border-border p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-accent" />
            <span className="text-sm font-medium text-slate-300">Ollama</span>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={clsx(
                'flex items-center gap-1.5 text-xs',
                ollamaHealthy ? 'text-green-400' : 'text-red-400'
              )}
            >
              <span
                className={clsx(
                  'w-2 h-2 rounded-full',
                  ollamaHealthy ? 'bg-green-400' : 'bg-red-400'
                )}
              />
              {ollamaHealthy ? 'Connected' : 'Disconnected'}
            </span>
            <button
              onClick={refresh}
              className="text-slate-500 hover:text-slate-200 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Pull new model */}
        <div className="space-y-2">
          <div className="flex gap-2">
            <input
              type="text"
              value={pullModel}
              onChange={(e) => setPullModel(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handlePull()}
              placeholder="Model name (e.g. llama3.1:8b)"
              disabled={pulling}
              className="flex-1 bg-bg-tertiary border border-border rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-accent disabled:opacity-50"
            />
            <button
              onClick={handlePull}
              disabled={!pullModel.trim() || pulling || !ollamaHealthy}
              className="flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-40"
            >
              <Download className="w-4 h-4" />
              Pull
            </button>
          </div>

          {pullProgress && (
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-slate-400 font-mono">
                <span>{pullProgress}</span>
                {pullPercent > 0 && <span>{pullPercent}%</span>}
              </div>
              {pullPercent > 0 && (
                <div className="h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
                  <div
                    className="h-full bg-accent rounded-full transition-all duration-300"
                    style={{ width: `${pullPercent}%` }}
                  />
                </div>
              )}
            </div>
          )}

          {error && (
            <div className="text-xs text-red-400 bg-red-900/20 border border-red-800/30 rounded px-3 py-2">
              {error}
            </div>
          )}
        </div>
      </div>

      {/* Model list */}
      <div className="bg-bg-secondary rounded-xl border border-border overflow-hidden">
        <div className="px-4 py-2.5 border-b border-border">
          <span className="text-sm font-medium text-slate-300">
            Available Models ({models.length})
          </span>
        </div>
        <div className="divide-y divide-border">
          {models.length === 0 && (
            <div className="px-4 py-6 text-center text-sm text-slate-600">
              {ollamaHealthy ? 'No models installed.' : 'Cannot reach Ollama.'}
            </div>
          )}
          {models.map((model) => (
            <div key={model.name} className="flex items-center gap-3 px-4 py-3">
              <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-mono text-slate-200">{model.name}</div>
                {model.details?.parameter_size && (
                  <div className="text-xs text-slate-500">
                    {model.details.parameter_size}
                    {model.details.quantization_level && ` · ${model.details.quantization_level}`}
                    {model.details.family && ` · ${model.details.family}`}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-1.5 text-xs text-slate-500 font-mono">
                <HardDrive className="w-3 h-3" />
                {formatBytes(model.size || 0)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
