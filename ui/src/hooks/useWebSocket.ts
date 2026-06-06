import { useEffect, useRef, useState, useCallback } from 'react'
import type { WsEvent } from '../types'

export function useWebSocket(url: string, maxHistory = 300) {
  const [events, setEvents] = useState<WsEvent[]>([])
  const [connected, setConnected] = useState(false)
  const ws = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mountedRef = useRef(true)

  const connect = useCallback(() => {
    if (!mountedRef.current) return

    try {
      const socket = new WebSocket(url)
      ws.current = socket

      socket.onopen = () => {
        if (mountedRef.current) setConnected(true)
      }

      socket.onclose = () => {
        if (!mountedRef.current) return
        setConnected(false)
        // Reconnect after 3s
        reconnectTimer.current = setTimeout(connect, 3000)
      }

      socket.onerror = () => {
        socket.close()
      }

      socket.onmessage = (e: MessageEvent) => {
        if (!mountedRef.current) return
        try {
          const event: WsEvent = JSON.parse(e.data as string)
          setEvents((prev) => {
            const next = [...prev, event]
            return next.length > maxHistory ? next.slice(next.length - maxHistory) : next
          })
        } catch {
          // ignore malformed events
        }
      }
    } catch {
      if (mountedRef.current) {
        reconnectTimer.current = setTimeout(connect, 3000)
      }
    }
  }, [url, maxHistory])

  useEffect(() => {
    mountedRef.current = true
    connect()
    return () => {
      mountedRef.current = false
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      ws.current?.close()
    }
  }, [connect])

  const clearEvents = useCallback(() => setEvents([]), [])

  return { events, connected, clearEvents }
}
