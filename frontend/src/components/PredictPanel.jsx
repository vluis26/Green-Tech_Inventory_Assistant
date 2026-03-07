import { useState } from 'react'
import { api } from '../api'

export default function PredictPanel({ item, onClose }) {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function runPrediction() {
    setLoading(true)
    setError('')
    try {
      const data = await api.predictReorder(item.id)
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-800">AI Reorder Prediction</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl leading-none">&times;</button>
        </div>

        <div className="px-6 py-4 space-y-4">
          <div className="bg-green-50 rounded-xl p-3 text-sm text-gray-700">
            <p className="font-medium text-green-800">{item.name}</p>
            <p className="text-xs text-gray-500 mt-0.5">
              {item.quantity} {item.unit} · {item.daily_usage_rate}/day · threshold {item.threshold}
            </p>
          </div>

          {!result && !loading && (
            <button
              onClick={runPrediction}
              className="w-full py-2.5 text-sm font-medium text-white bg-green-600 rounded-xl hover:bg-green-700"
            >
              Run AI Prediction
            </button>
          )}

          {loading && (
            <div className="flex items-center justify-center py-6 gap-2 text-green-700">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              <span className="text-sm">Analyzing…</span>
            </div>
          )}

          {error && (
            <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>
          )}

          {result && (
            <div className="space-y-3">
              <div className="flex items-center justify-between bg-blue-50 rounded-xl px-4 py-3">
                <span className="text-sm text-gray-600">Days until reorder</span>
                <span className="text-2xl font-bold text-blue-700">
                  {result.days_until_reorder ?? '—'}
                </span>
              </div>

              {result.reorder_date && (
                <div className="flex items-center justify-between text-sm px-1">
                  <span className="text-gray-500">Reorder by</span>
                  <span className="font-medium text-gray-800">{result.reorder_date}</span>
                </div>
              )}

              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                  Sustainable Alternatives
                </p>
                <ul className="space-y-1.5">
                  {result.sustainable_alternatives.map((alt, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                      <span className="mt-0.5 text-green-500">&#9679;</span>
                      {alt}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="bg-gray-50 rounded-xl px-4 py-3 text-xs text-gray-500">
                <span className="font-medium capitalize text-gray-700">{result.source}</span>
                {' · '}{result.reasoning}
              </div>

              <button
                onClick={runPrediction}
                className="w-full py-2 text-sm text-green-700 border border-green-200 rounded-xl hover:bg-green-50"
              >
                Refresh
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
