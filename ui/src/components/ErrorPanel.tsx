import { AlertTriangle, X } from 'lucide-react'
import { useState } from 'react'
import type { WsEvent } from '../types'

interface Props {
  events: WsEvent[]
}

export default function ErrorPanel({ events }: Props) {
  const [dismissed, setDismissed] = useState<Set<number>>(new Set())

  const errors = events
    .map((e, i) => ({ event: e, index: i }))
    .filter(({ event, index }) => {
      if (dismissed.has(index)) return false
      const d = event.data as Record<string, unknown>
      return (
        event.type === 'error' ||
        event.type.includes('error') ||
        d.error ||
        (d.level as string) === 'ERROR' ||
        (d.level as string) === 'CRITICAL'
      )
    })
    .slice(-20)

  if (errors.length === 0) return null

  return (
    <div className="space-y-2">
      {errors.map(({ event, index }) => {
        const d = event.data as Record<string, unknown>
        const message =
          (d.error as string) ??
          (d.message as string) ??
          JSON.stringify(event.data).slice(0, 200)
        return (
          <div
            key={index}
            className="flex items-start gap-3 bg-red-900/20 border border-red-800/40 rounded-lg px-4 py-3"
          >
            <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <div className="text-xs font-mono font-semibold text-red-400">{event.type}</div>
              <div className="text-xs text-red-300 mt-0.5 break-words">{message}</div>
              <div className="text-xs text-red-700 mt-1 font-mono">
                {new Date(event.timestamp).toLocaleString()}
              </div>
            </div>
            <button
              onClick={() => setDismissed((prev) => new Set([...prev, index]))}
              className="text-red-700 hover:text-red-400 transition-colors flex-shrink-0"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )
      })}
    </div>
  )
}
