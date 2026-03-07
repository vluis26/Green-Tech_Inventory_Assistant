import { useState, useEffect, useCallback } from 'react'
import { api } from '../api'
import ScoreBadge from './ScoreBadge'
import ItemModal from './ItemModal'
import PredictPanel from './PredictPanel'

const CATEGORIES = ['office supplies', 'food/beverage', 'cleaning', 'lab equipment']

export default function InventoryTable() {
  const [items, setItems] = useState([])
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [loading, setLoading] = useState(true)
  const [modalItem, setModalItem] = useState(null)   // null=closed, {}=new, item=edit
  const [predictItem, setPredictItem] = useState(null)
  const [deleting, setDeleting] = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    api.getItems(search || undefined, category || undefined)
      .then(setItems)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [search, category])

  useEffect(() => { load() }, [load])

  async function handleSave(payload) {
    if (modalItem?.id) {
      await api.updateItem(modalItem.id, payload)
    } else {
      await api.createItem(payload)
    }
    load()
  }

  async function handleDelete(id) {
    setDeleting(id)
    try {
      await api.deleteItem(id)
      load()
    } finally {
      setDeleting(null)
    }
  }

  const today = new Date().toISOString().slice(0, 10)
  const week = new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10)

  function rowStatus(item) {
    if (item.quantity <= item.threshold) return 'low'
    if (item.expiry_date && item.expiry_date >= today && item.expiry_date <= week) return 'expiring'
    return 'ok'
  }

  const rowClass = { low: 'bg-red-50', expiring: 'bg-amber-50', ok: '' }

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
        <div className="flex gap-2 flex-1">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name…"
            className="flex-1 border border-gray-200 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-400"
          />
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-400 bg-white"
          >
            <option value="">All categories</option>
            {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <button
          onClick={() => setModalItem({})}
          className="flex items-center gap-2 bg-green-600 text-white text-sm font-medium px-4 py-2 rounded-xl hover:bg-green-700 whitespace-nowrap"
        >
          <span className="text-lg leading-none">+</span> Add Item
        </button>
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl shadow-sm overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 text-xs font-semibold text-gray-500 uppercase tracking-wide">
              <th className="text-left px-5 py-3">Name</th>
              <th className="text-left px-4 py-3">Category</th>
              <th className="text-right px-4 py-3">Qty</th>
              <th className="text-right px-4 py-3">Threshold</th>
              <th className="text-left px-4 py-3">Expires</th>
              <th className="text-left px-4 py-3">Score</th>
              <th className="text-right px-5 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan="7" className="text-center py-10 text-gray-400">Loading…</td></tr>
            )}
            {!loading && items.length === 0 && (
              <tr><td colSpan="7" className="text-center py-10 text-gray-400">No items found.</td></tr>
            )}
            {items.map((item) => {
              const status = rowStatus(item)
              return (
                <tr key={item.id} className={`border-b border-gray-50 hover:bg-gray-50 transition-colors ${rowClass[status]}`}>
                  <td className="px-5 py-3 font-medium text-gray-800 max-w-48 truncate">
                    {status === 'low' && <span title="Low stock" className="mr-1">&#128308;</span>}
                    {status === 'expiring' && <span title="Expiring soon" className="mr-1">&#9888;&#65039;</span>}
                    {item.name}
                  </td>
                  <td className="px-4 py-3 text-gray-500 capitalize">{item.category}</td>
                  <td className="px-4 py-3 text-right font-mono text-gray-800">
                    {item.quantity} <span className="text-gray-400 text-xs">{item.unit}</span>
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-gray-500">{item.threshold}</td>
                  <td className="px-4 py-3 text-gray-500">{item.expiry_date || '—'}</td>
                  <td className="px-4 py-3"><ScoreBadge score={item.sustainability_score} /></td>
                  <td className="px-5 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => setPredictItem(item)}
                        title="AI Prediction"
                        className="p-1.5 rounded-lg text-blue-500 hover:bg-blue-50"
                      >
                        &#129302;
                      </button>
                      <button
                        onClick={() => setModalItem(item)}
                        title="Edit"
                        className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100"
                      >
                        &#9999;&#65039;
                      </button>
                      <button
                        onClick={() => handleDelete(item.id)}
                        disabled={deleting === item.id}
                        title="Delete"
                        className="p-1.5 rounded-lg text-red-400 hover:bg-red-50 disabled:opacity-40"
                      >
                        &#128465;&#65039;
                      </button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-xs text-gray-400 px-1">
        <span><span className="mr-1">&#128308;</span> Low stock</span>
        <span><span className="mr-1">&#9888;&#65039;</span> Expiring within 7 days</span>
        <span><span className="mr-1">&#129302;</span> AI prediction</span>
      </div>

      {modalItem !== null && (
        <ItemModal
          item={modalItem}
          onClose={() => setModalItem(null)}
          onSave={handleSave}
        />
      )}
      {predictItem && (
        <PredictPanel
          item={predictItem}
          onClose={() => setPredictItem(null)}
        />
      )}
    </div>
  )
}
