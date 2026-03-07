import { useState } from 'react'
import './index.css'
import Dashboard from './components/Dashboard'
import InventoryTable from './components/InventoryTable'

const TABS = ['Dashboard', 'Inventory']

export default function App() {
  const [tab, setTab] = useState('Dashboard')

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-50">
      {/* Header */}
      <header className="bg-white border-b border-green-100 sticky top-0 z-40 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-green-600 rounded-xl flex items-center justify-center text-white text-lg">
              &#127807;
            </div>
            <div>
              <h1 className="text-base font-bold text-gray-800 leading-tight">Green-Tech Inventory</h1>
              <p className="text-xs text-gray-400 leading-tight">Sustainable stock management</p>
            </div>
          </div>

          {/* Tabs */}
          <nav className="flex gap-1 bg-gray-100 rounded-xl p-1">
            {TABS.map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-4 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  tab === t
                    ? 'bg-white text-green-700 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {t}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <div className="mb-6">
          <h2 className="text-xl font-bold text-gray-800">{tab}</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            {tab === 'Dashboard'
              ? 'Overview of low-stock items and expiring inventory'
              : 'Manage your inventory — search, filter, and get AI-powered reorder predictions'}
          </p>
        </div>

        {tab === 'Dashboard' ? <Dashboard /> : <InventoryTable />}
      </main>

      <footer className="text-center text-xs text-gray-400 py-6">
        Green-Tech Inventory Assistant · reducing waste, one reorder at a time
      </footer>
    </div>
  )
}
