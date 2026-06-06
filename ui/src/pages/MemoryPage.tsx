import { useParams } from 'react-router-dom'
import { useAppStore } from '../store'
import MemoryViewer from '../components/MemoryViewer'
import { Brain } from 'lucide-react'

export default function MemoryPage() {
  const { agentId } = useParams<{ agentId: string }>()
  const { agents } = useAppStore()

  if (!agentId) return <div className="text-slate-500 p-8">No agent ID</div>

  const agent = agents.find((a) => a.id === agentId)

  return (
    <div className="flex flex-col h-full gap-4">
      <div className="flex items-center gap-3">
        <Brain className="w-5 h-5 text-accent" />
        <h2 className="text-lg font-semibold text-slate-200">
          Memory — {agent?.name ?? agentId}
        </h2>
      </div>

      <div className="flex-1 min-h-0">
        <MemoryViewer agentId={agentId} />
      </div>
    </div>
  )
}
