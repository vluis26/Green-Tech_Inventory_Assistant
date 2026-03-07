import { useState, useEffect } from 'react'
import { api } from '../api'

const CATEGORIES = ['office supplies', 'food/beverage', 'cleaning', 'lab equipment']

const EMPTY = {
  name: '',
  category: 'office supplies',
  quantity: '',
  unit: '',
  expiry_date: '',
  daily_usage_rate: '',
  threshold: '',
}

export default function ItemModal({ item, onClose, onSave }) {
  const [form, setForm] = useState(EMPTY)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const [description, setDescription] = useState('')
  const [parsing, setParsing] = useState(false)
  const [parseError, setParseError] = useState('')

  useEffect(() => {
    if (item) {
      setForm({
        name: item.name ?? '',
        category: item.category ?? 'office supplies',
        quantity: item.quantity ?? '',
        unit: item.unit ?? '',
        expiry_date: item.expiry_date ?? '',
        daily_usage_rate: item.daily_usage_rate ?? '',
        threshold: item.threshold ?? '',
      })
    }
  }, [item])

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }))

  async function handleAutofill() {
    if (!description.trim()) return
    setParsing(true)
    setParseError('')
    try {
      const parsed = await api.parseDescription(description.trim())
      setForm((f) => ({
        name: parsed.name ?? f.name,
        category: parsed.category ?? f.category,
        quantity: parsed.quantity != null ? String(parsed.quantity) : f.quantity,
        unit: parsed.unit ?? f.unit,
        expiry_date: parsed.expiry_date ?? f.expiry_date,
        daily_usage_rate: parsed.daily_usage_rate != null ? String(parsed.daily_usage_rate) : f.daily_usage_rate,
        threshold: parsed.threshold != null ? String(parsed.threshold) : f.threshold,
      }))
    } catch (err) {
      setParseError(err.message)
    } finally {
      setParsing(false)
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      const payload = {
        ...form,
        quantity: parseFloat(form.quantity),
        daily_usage_rate: parseFloat(form.daily_usage_rate),
        threshold: parseFloat(form.threshold),
        expiry_date: form.expiry_date || null,
      }
      await onSave(payload)
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-800">
            {item?.id ? 'Edit Item' : 'Add Item'}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl leading-none">&times;</button>
        </div>

        {/* Quick Add strip — only shown when creating a new item */}
        {!item?.id && (
          <div className="px-6 pt-4 pb-0 space-y-2">
            <label className="block text-xs font-semibold text-green-700 uppercase tracking-wide">
              Quick Add — describe the item
            </label>
            <div className="flex gap-2">
              <input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAutofill())}
                placeholder='e.g. "50 coffee bags, expires June 2026, we use about 2 per day"'
                className="flex-1 border border-green-200 bg-green-50 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-400 placeholder:text-gray-400"
              />
              <button
                type="button"
                onClick={handleAutofill}
                disabled={parsing || !description.trim()}
                className="px-3 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50 whitespace-nowrap"
              >
                {parsing ? '…' : 'Auto-fill'}
              </button>
            </div>
            {parseError && (
              <p className="text-xs text-red-600">{parseError}</p>
            )}
            <div className="border-t border-gray-100 pt-1" />
          </div>
        )}

        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
          {error && (
            <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1">Name</label>
              <input
                required
                value={form.name}
                onChange={set('name')}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-400"
                placeholder="e.g. Recycled Copy Paper"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Category</label>
              <select
                value={form.category}
                onChange={set('category')}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-400"
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Unit</label>
              <input
                required
                value={form.unit}
                onChange={set('unit')}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-400"
                placeholder="e.g. sheets, bottles"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Quantity</label>
              <input
                required
                type="number"
                min="0"
                step="any"
                value={form.quantity}
                onChange={set('quantity')}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-400"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Daily Usage Rate</label>
              <input
                required
                type="number"
                min="0"
                step="any"
                value={form.daily_usage_rate}
                onChange={set('daily_usage_rate')}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-400"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Reorder Threshold</label>
              <input
                required
                type="number"
                min="0"
                step="any"
                value={form.threshold}
                onChange={set('threshold')}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-400"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Expiry Date (optional)</label>
              <input
                type="date"
                value={form.expiry_date}
                onChange={set('expiry_date')}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-400"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 border border-gray-200 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50"
            >
              {saving ? 'Saving…' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
