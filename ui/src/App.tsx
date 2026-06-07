import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import Layout from './components/layout/Layout'
import Dashboard from './pages/Dashboard'
import AgentPage from './pages/AgentPage'
import MemoryPage from './pages/MemoryPage'
import SettingsPage from './pages/SettingsPage'
import { useAppStore } from './store'
import { useWebSocket } from './hooks/useWebSocket'
import { WS_URL } from './api/client'
import { agentsApi } from './api/agents'

function AppInner() {
  const { setAgents, addWsEvent, settings } = useAppStore()
  const wsUrl = settings.wsUrl || WS_URL
  const { events, connected } = useWebSocket(wsUrl, settings.maxEventHistory)

  // Seed agent list on mount
  useEffect(() => {
    agentsApi.list().then(setAgents).catch(() => {})
  }, [setAgents])

  // Forward WS events to store
  useEffect(() => {
    if (events.length > 0) {
      const last = events[events.length - 1]
      addWsEvent(last)
    }
  }, [events, addWsEvent])

  return (
    <Layout wsConnected={connected}>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/agents/:agentId" element={<AgentPage />} />
        <Route path="/memory/:agentId" element={<MemoryPage />} />
      </Routes>
    </Layout>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppInner />
    </BrowserRouter>
  )
}
