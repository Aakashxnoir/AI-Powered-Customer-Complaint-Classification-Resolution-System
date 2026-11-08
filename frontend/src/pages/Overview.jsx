import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api'
import { CAT_COLORS, Card, Loading, PRIORITIES, SENTIMENTS, Stat } from '../ui'

const PRI_COLORS = { critical: '#dc2626', high: '#f97316', medium: '#eab308', low: '#94a3b8' }
const SENT_COLORS = { positive: '#10b981', neutral: '#94a3b8', negative: '#f97316', highly_negative: '#dc2626' }

export default function Overview() {
  const [s, setS] = useState(null)
  const [t, setT] = useState(null)
  const [err, setErr] = useState('')
  useEffect(() => {
    api.stats().then(setS).catch((e) => setErr(e.message))
    api.trends().then(setT).catch(() => {})
  }, [])
  if (err) return <p className="text-red-600">Backend not reachable: {err}</p>
  if (!s) return <Loading />

  const cat = Object.entries(s.by_category).map(([name, value]) => ({ name, value }))
  const pri = PRIORITIES.map((p) => ({ name: p, value: s.by_priority[p] || 0 }))
  const sent = SENTIMENTS.map((p) => ({ name: p.replace('_', ' '), key: p, value: s.by_sentiment[p] || 0 }))
  const dept = Object.entries(s.by_department).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value)

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-medium text-stone-900">Overview</h1>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Complaints" value={s.total} />
        <Stat label="Critical / high" value={(s.by_priority.critical || 0) + (s.by_priority.high || 0)} />
        <Stat label="Open" value={s.by_status.new || 0} sub="no approved response yet" />
        <Stat label="Duplicates to review" value={s.pending_duplicates} />
      </div>

      {t?.alerts?.length > 0 && (
        <Card title="Emerging issues" action={<Link to="/trends" className="text-sm text-brand-600">View trends →</Link>}>
          <ul className="space-y-2">
            {t.alerts.slice(0, 3).map((a) => (
              <li key={a.dimension + a.value} className="flex items-start gap-3 rounded-lg bg-red-50 p-3 text-sm text-red-900">
                <span className="mt-0.5 rounded bg-red-600 px-1.5 text-xs font-medium text-white">+{a.increase_pct}%</span>
                {a.message}
              </li>
            ))}
          </ul>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="By category">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={cat} dataKey="value" nameKey="name" innerRadius={50} outerRadius={85} paddingAngle={2}>
                {cat.map((c) => <Cell key={c.name} fill={CAT_COLORS[c.name]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex flex-wrap gap-3 text-xs">
            {cat.map((c) => <span key={c.name} className="flex items-center gap-1"><span className="h-2 w-2 rounded-full" style={{ background: CAT_COLORS[c.name] }} />{c.name} {c.value}</span>)}
          </div>
        </Card>
        <Card title="By priority">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={pri}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" fontSize={12} /><YAxis fontSize={12} /><Tooltip />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>{pri.map((p) => <Cell key={p.name} fill={PRI_COLORS[p.name]} />)}</Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card title="By sentiment">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={sent}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" fontSize={11} /><YAxis fontSize={12} /><Tooltip />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>{sent.map((p) => <Cell key={p.key} fill={SENT_COLORS[p.key]} />)}</Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <Card title="Routed to department">
        <ResponsiveContainer width="100%" height={Math.max(160, dept.length * 34)}>
          <BarChart data={dept} layout="vertical" margin={{ left: 40 }}>
            <XAxis type="number" fontSize={12} /><YAxis type="category" dataKey="name" width={130} fontSize={12} /><Tooltip />
            <Bar dataKey="value" fill="#111111" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Card>
    </div>
  )
}
