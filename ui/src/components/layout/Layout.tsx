import { ReactNode } from 'react'
import Sidebar from './Sidebar'
import Header from './Header'
import { useAppStore } from '../../store'

interface Props {
  children: ReactNode
  wsConnected: boolean
}

export default function Layout({ children, wsConnected }: Props) {
  const { sidebarOpen } = useAppStore()

  return (
    <div className="flex h-screen overflow-hidden bg-bg-primary text-slate-200">
      <Sidebar />
      <div
        className={`flex flex-col flex-1 min-w-0 transition-all duration-200 ${
          sidebarOpen ? 'md:ml-64' : 'ml-0'
        }`}
      >
        <Header wsConnected={wsConnected} />
        <main className="flex-1 overflow-auto p-2 sm:p-4">{children}</main>
      </div>
    </div>
  )
}
