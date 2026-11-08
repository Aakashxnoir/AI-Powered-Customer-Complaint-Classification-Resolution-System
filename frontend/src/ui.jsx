export const CATEGORIES = ['payment', 'delivery', 'product', 'refund', 'account', 'technical']
export const PRIORITIES = ['critical', 'high', 'medium', 'low']
export const SENTIMENTS = ['positive', 'neutral', 'negative', 'highly_negative']
export const DEPARTMENTS = ['Billing & Payments', 'Logistics', 'Product Quality', 'Refunds & Returns',
  'Account Services', 'Technical Support', 'Fraud & Security', 'Product Safety']

export const CAT_COLORS = {
  payment: '#6366f1', delivery: '#0ea5e9', product: '#f59e0b',
  refund: '#10b981', account: '#ec4899', technical: '#8b5cf6',
}

const TONE = {
  critical: 'bg-red-100 text-red-800 ring-red-200', high: 'bg-orange-100 text-orange-800 ring-orange-200',
  medium: 'bg-yellow-100 text-yellow-800 ring-yellow-200', low: 'bg-slate-100 text-slate-700 ring-slate-200',
  positive: 'bg-emerald-100 text-emerald-800 ring-emerald-200', neutral: 'bg-slate-100 text-slate-700 ring-slate-200',
  negative: 'bg-orange-100 text-orange-800 ring-orange-200', highly_negative: 'bg-red-100 text-red-800 ring-red-200',
  new: 'bg-blue-100 text-blue-800 ring-blue-200', approved: 'bg-emerald-100 text-emerald-800 ring-emerald-200',
  rejected: 'bg-slate-200 text-slate-700 ring-slate-300', pending: 'bg-purple-100 text-purple-800 ring-purple-200',
}

export function Badge({ value, className = '' }) {
  if (!value) return null
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${TONE[value] || 'bg-slate-100 text-slate-700 ring-slate-200'} ${className}`}>
      {value.replace('_', ' ')}
    </span>
  )
}

export function CatBadge({ value }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-700">
      <span className="h-2 w-2 rounded-full" style={{ background: CAT_COLORS[value] || '#94a3b8' }} />
      {value}
    </span>
  )
}

export function Card({ title, action, children, className = '' }) {
  return (
    <section className={`rounded-xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>
      {(title || action) && (
        <div className="mb-4 flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
          {action}
        </div>
      )}
      {children}
    </section>
  )
}

export function ScoreBar({ label, value, color = '#6366f1', highlight }) {
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className={`w-32 shrink-0 truncate ${highlight ? 'font-semibold text-slate-900' : 'text-slate-600'}`}>{label}</span>
      <div className="h-2 flex-1 rounded-full bg-slate-100">
        <div className="h-2 rounded-full" style={{ width: `${Math.max(1, value * 100)}%`, background: color }} />
      </div>
      <span className="w-12 text-right tabular-nums text-slate-600">{(value * 100).toFixed(1)}%</span>
    </div>
  )
}

export function Stat({ label, value, sub }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">{value}</div>
      {sub && <div className="mt-0.5 text-xs text-slate-500">{sub}</div>}
    </div>
  )
}

export const btn = 'inline-flex items-center justify-center gap-1 rounded-lg px-3 py-1.5 text-sm font-medium transition disabled:opacity-50'
export const btnPrimary = `${btn} bg-indigo-600 text-white hover:bg-indigo-500`
export const btnGhost = `${btn} border border-slate-300 bg-white text-slate-700 hover:bg-slate-50`
export const input = 'rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500'

export const fmtDate = (d) => new Date(d).toLocaleString(undefined, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
