async function req(path, opts = {}) {
  const res = await fetch(`/api${path}`, opts)
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail ? JSON.stringify(data.detail) : res.statusText)
  return data
}

const json = (method, body) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export const api = {
  stats: () => req('/stats'),
  list: (params) => req('/complaints?' + new URLSearchParams(Object.entries(params).filter(([, v]) => v !== '' && v != null))),
  get: (id) => req(`/complaints/${id}`),
  create: (body) => req('/complaints', json('POST', body)),
  upload: (file) => { const f = new FormData(); f.append('file', file); return req('/complaints/upload', { method: 'POST', body: f }) },
  review: (id, body) => req(`/complaints/${id}/review`, json('POST', body)),
  draft: (id) => req(`/complaints/${id}/draft`, { method: 'POST' }),
  respond: (id, body) => req(`/complaints/${id}/response`, json('POST', body)),
  duplicates: (status = 'pending') => req(`/duplicates?status=${status}`),
  resolveDup: (body) => req('/duplicates/resolve', json('POST', body)),
  trends: () => req('/trends'),
  evaluation: () => req('/evaluation'),
  retrain: () => req('/model/retrain', { method: 'POST' }),
  health: () => req('/health'),
}
