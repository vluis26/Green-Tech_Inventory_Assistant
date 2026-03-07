const BASE = '/api'

async function req(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  getItems: (search, category) => {
    const params = new URLSearchParams()
    if (search) params.set('search', search)
    if (category) params.set('category', category)
    const qs = params.toString()
    return req(`/items${qs ? `?${qs}` : ''}`)
  },
  createItem: (data) => req('/items', { method: 'POST', body: JSON.stringify(data) }),
  updateItem: (id, data) => req(`/items/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteItem: (id) => req(`/items/${id}`, { method: 'DELETE' }),
  getDashboard: () => req('/dashboard'),
  predictReorder: (id) => req(`/items/${id}/predict`),
  getCategories: () => req('/categories'),
  parseDescription: (description) => req('/items/parse-description', { method: 'POST', body: JSON.stringify({ description }) }),
}
