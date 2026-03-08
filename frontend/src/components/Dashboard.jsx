import { useEffect, useState } from 'react'
import { api } from '../api'
import ScoreBadge from './ScoreBadge'

function StatCard({ label, value, sub, color = 'green', icon }) {
  const ring = { green: 'ring-green-200', amber: 'ring-amber-200', red: 'ring-red-200', blue: 'ring-blue-200' }
  const text = { green: 'text-green-700', amber: 'text-amber-700', red: 'text-red-700', blue: 'text-blue-700' }
  return (
    <div className={`bg-white rounded-2xl p-5 ring-1 ${ring[color]}`}>
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
        {icon && <span className="text-lg">{icon}</span>}
      </div>
      <p className={`text-3xl font-bold mt-1 ${text[color]}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  )
}

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [waste, setWaste] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([api.getDashboard(), api.getWasteSavings()])
      .then(([d, w]) => { setData(d); setWaste(w) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="flex items-center justify-center h-40 text-gray-400 text-sm">Loading dashboard…</div>
  )
  if (!data) return null

  const wasteCount = waste?.items_reordered_this_month ?? 0
  const wasteValue = wasteCount === 0
    ? <span className="text-lg font-semibold text-green-600">All clear</span>
    : wasteCount

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <StatCard label="Total Items" value={data.total_items} color="blue" />
        <StatCard label="Low Stock" value={data.low_stock.length} sub="at or below threshold" color="red" />
        <StatCard label="Expiring Soon" value={data.expiring_soon.length} sub="within 7 days" color="amber" />
        <StatCard label="Avg Sustainability" value={`${data.average_sustainability_score}/100`} color="green" />
        <StatCard
          label="Waste Prevented"
          icon="🌿"
          value={wasteValue}
          sub={
            wasteCount === 0
              ? "No alerts yet — you're well stocked!"
              : "items flagged before stockout this month"
          }
          color="green"
        />
      </div>

      {waste?.most_at_risk_item && wasteCount > 0 && (
        <div className="flex items-center gap-3 bg-green-50 border border-green-100 rounded-2xl px-5 py-3 text-sm">
          <span className="text-base">🌿</span>
          <span className="text-gray-600">
            Most flagged item this month:{' '}
            <span className="font-medium text-gray-800">{waste.most_at_risk_item.name}</span>
            {' '}—{' '}
            <span className="text-green-700">{waste.most_at_risk_item.count} reorder event{waste.most_at_risk_item.count !== 1 ? 's' : ''}</span>
          </span>
        </div>
      )}

      {data.low_stock.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-red-700 mb-2">Low Stock Items</h3>
          <div className="space-y-2">
            {data.low_stock.map((item) => (
              <div key={item.id} className="flex items-center justify-between bg-red-50 border border-red-100 rounded-xl px-4 py-3">
                <div>
                  <p className="text-sm font-medium text-gray-800">{item.name}</p>
                  <p className="text-xs text-gray-500">{item.category} · threshold {item.threshold} {item.unit}</p>
                </div>
                <span className="text-lg font-bold text-red-700">{item.quantity} <span className="text-xs font-normal text-gray-400">{item.unit}</span></span>
              </div>
            ))}
          </div>
        </section>
      )}

      {data.expiring_soon.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-amber-700 mb-2">Expiring Within 7 Days</h3>
          <div className="space-y-2">
            {data.expiring_soon.map((item) => (
              <div key={item.id} className="flex items-center justify-between bg-amber-50 border border-amber-100 rounded-xl px-4 py-3">
                <div>
                  <p className="text-sm font-medium text-gray-800">{item.name}</p>
                  <p className="text-xs text-gray-500">{item.category}</p>
                </div>
                <div className="text-right">
                  <ScoreBadge score={item.sustainability_score} itemId={item.id} />
                  <p className="text-xs text-amber-700 mt-1">Expires {item.expiry_date}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {data.low_stock.length === 0 && data.expiring_soon.length === 0 && (
        <div className="flex items-center gap-3 bg-green-50 border border-green-100 rounded-2xl px-5 py-4">
          <span className="text-2xl">&#10003;</span>
          <p className="text-sm text-green-700 font-medium">All items are well-stocked and within date. Great job!</p>
        </div>
      )}
    </div>
  )
}
