import { useEffect, useState } from 'react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api'
import { CAT_COLORS, Card, Loading } from '../ui'

export default function Trends() {
  const [t, setT] = useState(null)
  const [err, setErr] = useState('')
  useEffect(() => { api.trends().then(setT).catch((e) => setErr(e.message)) }, [])
  if (err) return <p className="text-red-600">Backend not reachable: {err}</p>
  if (!t) return <Loading />
  const cats = Object.keys(CAT_COLORS)
  const toBars = (o) => Object.entries(o).map(([name, value]) => ({ name, value }))

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-medium text-stone-900">Complaint trends</h1>
      <Card title={`Emerging issues (${t.alerts.length})`}>
        <p className="mb-3 text-xs text-stone-500">Last 3 days vs previous 14-day baseline, per category, product and location. Flagged when z-score ≥ 2.5 and at least 6 complaints.</p>
        {t.alerts.length === 0 ? <p className="text-sm text-stone-500">No unusual spikes detected.</p> : (
          <div className="grid gap-3 md:grid-cols-2">
            {t.alerts.map((a) => (
              <div key={a.dimension + a.value} className="rounded-lg border border-red-200 bg-red-50 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium capitalize text-red-700">{a.dimension}</span>
                  <span className="rounded bg-red-600 px-2 py-0.5 text-xs font-medium text-white">+{a.increase_pct}%</span>
                </div>
                <p className="mt-1 text-lg font-medium text-stone-900">{a.value}</p>
                <p className="text-sm tabular-nums text-stone-700">{a.recent_daily_avg}/day now vs {a.baseline_daily_avg}/day baseline · z = {a.z_score}</p>
                {a.dominant_category && <p className="text-xs text-stone-500">Mostly <b>{a.dominant_category}</b> complaints</p>}
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card title="Daily complaints by category">
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={t.by_category}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="day" fontSize={11} tickFormatter={(d) => d.slice(5)} /><YAxis fontSize={12} /><Tooltip /><Legend />
            {cats.map((c) => <Area key={c} type="monotone" dataKey={c} stackId="1" stroke={CAT_COLORS[c]} fill={CAT_COLORS[c]} fillOpacity={0.6} />)}
          </AreaChart>
        </ResponsiveContainer>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        {[['Top products', t.top_products, '#fe7a2f'], ['Top locations', t.top_locations, '#03b2cb']].map(([title, data, color]) => (
          <Card key={title} title={title}>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={toBars(data)} layout="vertical" margin={{ left: 30 }}>
                <XAxis type="number" fontSize={12} /><YAxis type="category" dataKey="name" width={140} fontSize={12} /><Tooltip />
                <Bar dataKey="value" fill={color} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        ))}
      </div>
    </div>
  )
}
