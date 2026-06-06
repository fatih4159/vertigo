import { useState } from 'react'
import { Play, Pause, Square, StepForward, Zap, Target, Repeat, Hash } from 'lucide-react'
import clsx from 'clsx'
import type { Agent, RunMode, WsEvent } from '../types'
import type { StartAgentPayload } from '../api/agents'

interface Props {
  agent: Agent
  wsEvents: WsEvent[]
  onStart: (payload: StartAgentPayload) => Promise<void>
  onPause: () => Promise<void>
  onResume: () => Promise<void>
  onStop: () => Promise<void>
}

const STATE_COLORS: Record<string, string> = {
  IDLE: 'bg-state-idle',
  RUNNING: 'bg-state-running animate-pulse',
  PAUSED: 'bg-state-paused',
  STOPPED: 'bg-state-stopped',
  ERROR: 'bg-state-error animate-pulse',
  THINKING: 'bg-state-thinking animate-pulse',
  EXECUTING: 'bg-state-executing animate-pulse',
}

const STATE_TEXT: Record<string, string> = {
  IDLE: 'text-slate-400',
  RUNNING: 'text-green-400',
  PAUSED: 'text-yellow-400',
  STOPPED: 'text-red-400',
  ERROR: 'text-red-400',
  THINKING: 'text-violet-400',
  EXECUTING: 'text-sky-400',
}

export default function AgentConsole({ agent, wsEvents, onStart, onPause, onResume, onStop }: Props) {
  const [mode, setMode] = useState<RunMode>('run_forever')
  const [nIterations, setNIterations] = useState(10)
  const [goal, setGoal] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isRunning = agent.state === 'RUNNING' || agent.state === 'THINKING' || agent.state === 'EXECUTING'
  const isPaused = agent.state === 'PAUSED'
  const isIdle = agent.state === 'IDLE' || agent.state === 'STOPPED'

  const liveStatus = agent.live_status

  // Recent tool calls from WS events
  const toolEvents = wsEvents
    .filter((e) => (e.agent_id === agent.id || !e.agent_id) && e.type === 'tool_call')
    .slice(-20)

  const handleStart = async () => {
    setLoading(true)
    setError(null)
    try {
      await onStart({
        mode,
        n_iterations: mode === 'run_n_iterations' ? nIterations : undefined,
        goal: goal || undefined,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  const handle = (fn: () => Promise<void>) => async () => {
    setLoading(true)
    setError(null)
    try {
      await fn()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* State header */}
      <div className="bg-bg-secondary rounded-xl border border-border p-4">
        <div className="flex items-center gap-3 mb-4">
          <span className={clsx('w-3 h-3 rounded-full flex-shrink-0', STATE_COLORS[agent.state] ?? 'bg-state-idle')} />
          <span className={clsx('font-mono text-lg font-bold', STATE_TEXT[agent.state] ?? 'text-slate-400')}>
            {agent.state}
          </span>
          {liveStatus && (
            <span className="ml-auto font-mono text-xs text-slate-500">
              iter {liveStatus.current_iteration} / {liveStatus.total_iterations || '∞'}
            </span>
          )}
        </div>

        {/* Token usage */}
        {liveStatus && liveStatus.tokens_used > 0 && (
          <div className="flex items-center gap-2 text-xs text-slate-500 mb-3">
            <Zap className="w-3.5 h-3.5" />
            <span>{liveStatus.tokens_used.toLocaleString()} tokens used</span>
          </div>
        )}

        {/* Current goal */}
        {(liveStatus?.current_goal || goal) && (
          <div className="flex items-start gap-2 text-sm text-slate-300 bg-bg-tertiary rounded-lg p-3">
            <Target className="w-4 h-4 mt-0.5 text-accent flex-shrink-0" />
            <span className="font-mono text-xs">{liveStatus?.current_goal || goal}</span>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="bg-bg-secondary rounded-xl border border-border p-4 space-y-4">
        <h3 className="text-sm font-semibold text-slate-300">Run Controls</h3>

        {/* Mode selector */}
        {isIdle && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2">
              {(
                [
                  { value: 'run_forever', label: 'Forever', icon: Repeat },
                  { value: 'run_until_goal', label: 'Until Goal', icon: Target },
                  { value: 'run_n_iterations', label: 'N Iterations', icon: Hash },
                  { value: 'manual_step', label: 'Manual Step', icon: StepForward },
                ] as const
              ).map(({ value, label, icon: Icon }) => (
                <button
                  key={value}
                  onClick={() => setMode(value)}
                  className={clsx(
                    'flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors border',
                    mode === value
                      ? 'bg-accent/20 border-accent text-accent'
                      : 'border-border text-slate-400 hover:border-border-hover hover:text-slate-200'
                  )}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {label}
                </button>
              ))}
            </div>

            {mode === 'run_n_iterations' && (
              <input
                type="number"
                min={1}
                max={10000}
                value={nIterations}
                onChange={(e) => setNIterations(parseInt(e.target.value) || 1)}
                className="w-full bg-bg-tertiary border border-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-accent"
                placeholder="Number of iterations"
              />
            )}

            <textarea
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              rows={2}
              className="w-full bg-bg-tertiary border border-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-accent resize-none font-mono"
              placeholder="Goal (optional)..."
            />
          </div>
        )}

        {/* Action buttons */}
        <div className="flex gap-2">
          {isIdle && (
            <button
              onClick={handleStart}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
            >
              <Play className="w-4 h-4" />
              Start
            </button>
          )}

          {isRunning && (
            <>
              <button
                onClick={handle(onPause)}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 bg-yellow-600 hover:bg-yellow-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                <Pause className="w-4 h-4" />
                Pause
              </button>
              <button
                onClick={handle(onStop)}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 bg-red-700 hover:bg-red-600 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                <Square className="w-4 h-4" />
                Stop
              </button>
            </>
          )}

          {isPaused && (
            <>
              <button
                onClick={handle(onResume)}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                <Play className="w-4 h-4" />
                Resume
              </button>
              <button
                onClick={handle(onStop)}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 bg-red-700 hover:bg-red-600 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                <Square className="w-4 h-4" />
                Stop
              </button>
            </>
          )}
        </div>

        {error && (
          <div className="text-xs text-red-400 bg-red-900/20 border border-red-800/50 rounded-lg px-3 py-2">
            {error}
          </div>
        )}
      </div>

      {/* Live tool call feed */}
      {toolEvents.length > 0 && (
        <div className="bg-bg-secondary rounded-xl border border-border p-4">
          <h3 className="text-sm font-semibold text-slate-300 mb-3">Live Tool Calls</h3>
          <div className="space-y-1.5 max-h-48 overflow-y-auto">
            {toolEvents.map((ev, i) => {
              const d = ev.data as Record<string, unknown>
              return (
                <div
                  key={i}
                  className={clsx(
                    'flex items-center gap-2 text-xs font-mono px-2 py-1 rounded',
                    d.success ? 'bg-green-900/20 text-green-400' : 'bg-red-900/20 text-red-400'
                  )}
                >
                  <span className="text-slate-500">{new Date(ev.timestamp).toLocaleTimeString()}</span>
                  <span className="font-semibold">{String(d.tool_name ?? '?')}</span>
                  {d.duration_ms !== undefined && (
                    <span className="ml-auto text-slate-500">{Math.round(d.duration_ms as number)}ms</span>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
