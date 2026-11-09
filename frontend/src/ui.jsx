import { useEffect, useState } from 'react'

export const CATEGORIES = ['payment', 'delivery', 'product', 'refund', 'account', 'technical']
export const PRIORITIES = ['critical', 'high', 'medium', 'low']
export const SENTIMENTS = ['positive', 'neutral', 'negative', 'highly_negative']
export const DEPARTMENTS = ['Billing & Payments', 'Logistics', 'Product Quality', 'Refunds & Returns',
  'Account Services', 'Technical Support', 'Fraud & Security', 'Product Safety']

export const CAT_COLORS = {
  payment: '#65b5ff', delivery: '#03b2cb', product: '#8a7cf0',  // orange is reserved for AI marks
  refund: '#0bb04a', account: '#ff2067', technical: '#9cc417',
}

// Severity reads by weight of the error token: filled > outlined > neutral.
const ERR = 'bg-error text-white ring-error', ERR_SOFT = 'bg-white text-error ring-error/40'
const NEUTRAL = 'bg-surface-2 text-ink ring-hairline', QUIET = 'bg-white text-ink-muted ring-hairline'
const TONE = {
  critical: ERR, high: ERR_SOFT, medium: NEUTRAL, low: QUIET,
  highly_negative: ERR, negative: ERR_SOFT, neutral: QUIET, positive: 'bg-white text-success ring-success/40',
  new: NEUTRAL, approved: 'bg-success text-white ring-success', rejected: QUIET,
  pending: 'bg-white text-ai-accent ring-ai-accent/40',
}

// Marks what the model produced (DESIGN.md: one orange, for the AI only).
export function AiMark({ children = 'AI' }) {
  return <span className="text-xs font-medium text-ai-accent">{children}</span>
}

export function Badge({ value, className = '' }) {
  if (!value) return null
  return (
    <span className={`inline-flex items-center whitespace-nowrap rounded px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${TONE[value] || NEUTRAL} ${className}`}>
      {value.replace('_', ' ')}
    </span>
  )
}

export function CatBadge({ value }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium text-stone-700">
      <span className="h-2 w-2 rounded-full" style={{ background: CAT_COLORS[value] || 'var(--color-ink-subtle)' }} />
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

export const btn = 'inline-flex items-center justify-center gap-1 rounded-lg px-[18px] py-2 text-sm font-medium transition hover:-translate-y-px active:translate-y-0 active:scale-[.98] disabled:pointer-events-none disabled:opacity-50'
export const btnPrimary = `${btn} bg-brand-600 text-white hover:bg-brand-500`
export const btnGhost = `${btn} border border-hairline bg-white text-ink hover:bg-surface-2`
export const input = 'rounded-lg border border-hairline bg-white px-3 py-1.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500'

export const fmtDate = (d) => new Date(d).toLocaleString(undefined, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
