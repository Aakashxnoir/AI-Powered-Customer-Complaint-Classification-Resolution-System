import { useEffect, useState } from 'react'

export const CATEGORIES = ['payment', 'delivery', 'product', 'refund', 'account', 'technical']
export const PRIORITIES = ['critical', 'high', 'medium', 'low']
export const SENTIMENTS = ['positive', 'neutral', 'negative', 'highly_negative']
export const DEPARTMENTS = ['Billing & Payments', 'Logistics', 'Product Quality', 'Refunds & Returns',
  'Account Services', 'Technical Support', 'Fraud & Security', 'Product Safety']

export const CAT_COLORS = {
  payment: '#65b5ff', delivery: '#03b2cb', product: '#fe7a2f',
  refund: '#0bb04a', account: '#ff2067', technical: '#9cc417',
}

const TONE = {
  critical: 'bg-red-100 text-red-800 ring-red-200', high: 'bg-orange-100 text-orange-800 ring-orange-200',
  medium: 'bg-yellow-100 text-yellow-800 ring-yellow-200', low: 'bg-stone-100 text-stone-700 ring-stone-200',
  positive: 'bg-emerald-100 text-emerald-800 ring-emerald-200', neutral: 'bg-stone-100 text-stone-700 ring-stone-200',
  negative: 'bg-orange-100 text-orange-800 ring-orange-200', highly_negative: 'bg-red-100 text-red-800 ring-red-200',
  new: 'bg-blue-100 text-blue-800 ring-blue-200', approved: 'bg-emerald-100 text-emerald-800 ring-emerald-200',
  rejected: 'bg-stone-200 text-stone-700 ring-stone-300', pending: 'bg-brand-100 text-brand-800 ring-brand-200',
}

export function Badge({ value, className = '' }) {
  if (!value) return null
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${TONE[value] || 'bg-stone-100 text-stone-700 ring-stone-200'} ${className}`}>
      {value.replace('_', ' ')}
    </span>
  )
}

export function CatBadge({ value }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium text-stone-700">
      <span className="h-2 w-2 rounded-full" style={{ background: CAT_COLORS[value] || '#94a3b8' }} />
      {value}
    </span>
  )
}

export function Card({ title, action, children, className = '' }) {
  return (
    <section className={`rounded-xl border border-hairline bg-white p-5 ${className}`}>
      {(title || action) && (
        <div className="mb-4 flex items-center justify-between gap-2">
          <h2 className="text-sm font-medium text-stone-900">{title}</h2>
          {action}
        </div>
      )}
      {children}
    </section>
  )
}

export function ScoreBar({ label, value, color = '#111111', highlight }) {
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className={`w-32 shrink-0 truncate ${highlight ? 'font-medium text-stone-900' : 'text-stone-600'}`}>{label}</span>
      <div className="h-2 flex-1 rounded-full bg-stone-100">
        <div className="h-2 rounded-full" style={{ width: `${Math.max(1, value * 100)}%`, background: color }} />
      </div>
      <span className="w-12 text-right tabular-nums text-stone-600">{(value * 100).toFixed(1)}%</span>
    </div>
  )
}

export function Stat({ label, value, sub }) {
  return (
    <div className="rounded-xl border border-hairline bg-white p-4">
      <div className="text-xs font-medium text-stone-500">{label}</div>
      <div className="mt-1 text-2xl font-medium tabular-nums text-stone-900">{value}</div>
      {sub && <div className="mt-0.5 text-xs text-stone-500">{sub}</div>}
    </div>
  )
}

export function Loading() {
  return (
    <div role="status" aria-label="Loading" className="space-y-4">
      <div className="h-7 w-48 animate-pulse rounded-lg bg-stone-200" />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => <div key={i} className="h-24 animate-pulse rounded-xl bg-stone-200/70" />)}
      </div>
      <div className="h-64 animate-pulse rounded-xl bg-stone-200/70" />
    </div>
  )
}

export const notify = (text) => window.dispatchEvent(new CustomEvent('ciq-toast', { detail: text }))

export function Toast() {
  const [msg, setMsg] = useState(null)
  useEffect(() => {
    let t
    const on = (e) => { setMsg({ text: e.detail, key: Date.now() }); clearTimeout(t); t = setTimeout(() => setMsg(null), 2600) }
    window.addEventListener('ciq-toast', on)
    return () => { window.removeEventListener('ciq-toast', on); clearTimeout(t) }
  }, [])
  if (!msg) return null
  return <div key={msg.key} role="status" className="toast fixed bottom-5 right-5 z-50 rounded-lg bg-ink px-4 py-2.5 text-sm text-white">{msg.text}</div>
}

export const btn = 'inline-flex items-center justify-center gap-1 rounded-lg px-3 py-1.5 text-sm font-medium transition hover:-translate-y-px active:translate-y-0 active:scale-[.98] disabled:pointer-events-none disabled:opacity-50'
export const btnPrimary = `${btn} bg-brand-600 text-white hover:bg-brand-500`
export const btnGhost = `${btn} border border-stone-300 bg-white text-stone-700 hover:bg-stone-50`
export const input = 'rounded-lg border border-stone-300 bg-white px-3 py-1.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500'

export const fmtDate = (d) => new Date(d).toLocaleString(undefined, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
