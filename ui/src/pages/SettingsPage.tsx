import { Settings2 } from 'lucide-react'
import Settings from '../components/Settings'

export default function SettingsPage() {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-2">
        <Settings2 className="w-5 h-5 text-accent" />
        <h1 className="text-xl font-bold text-slate-100">Settings</h1>
      </div>
      <Settings />
    </div>
  )
}
