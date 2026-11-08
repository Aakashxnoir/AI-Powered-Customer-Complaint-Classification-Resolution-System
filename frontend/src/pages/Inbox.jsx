import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { Badge, CATEGORIES, CatBadge, DEPARTMENTS, PRIORITIES, btnGhost, fmtDate, input } from '../ui'

const PAGE = 25

export default function Inbox() {
  const nav = useNavigate()
  const [f, setF] = useState({ category: '', priority: '', status: '', department: '', q: '' })
  const [page, setPage] = useState(0)
  const [data, setData] = useState({ total: 0, items: [] })

  useEffect(() => {
    const t = setTimeout(() => api.list({ ...f, limit: PAGE, offset: page * PAGE }).then(setData), 200)
    return () => clearTimeout(t)
  }, [f, page])

  const set = (k) => (e) => { setPage(0); setF({ ...f, [k]: e.target.value }) }
  const select = (k, opts) => (
    <select className={input} value={f[k]} onChange={set(k)}>
      <option value="">All {k}</option>
      {opts.map((o) => <option key={o} value={o}>{o}</option>)}
    </select>
  )

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-slate-900">Inbox <span className="text-sm font-normal text-slate-500">{data.total} complaints</span></h1>
      <div className="flex flex-wrap gap-2">
        <input className={`${input} w-full sm:w-64`} placeholder="Search text…" value={f.q} onChange={set('q')} />
        {select('category', CATEGORIES)}
        {select('priority', PRIORITIES)}
        {select('department', DEPARTMENTS)}
        {select('status', ['new', 'approved', 'rejected'])}
      </div>
      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full min-w-[800px] text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr><th className="p-3">#</th><th className="p-3">Complaint</th><th className="p-3">Category</th><th className="p-3">Priority</th><th className="p-3">Sentiment</th><th className="p-3">Department</th><th className="p-3">Status</th><th className="p-3">Date</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data.items.map((c) => (
              <tr key={c.id} onClick={() => nav(`/complaints/${c.id}`)} className="cursor-pointer hover:bg-slate-50">
                <td className="p-3 text-slate-400">{c.id}</td>
                <td className="max-w-md p-3"><div className="line-clamp-2">{c.text}</div>
                  {c.duplicate_group && <span className="text-xs text-purple-600">duplicate group #{c.duplicate_group}</span>}</td>
                <td className="p-3"><CatBadge value={c.category} /><div className="text-xs text-slate-400">{(c.category_confidence * 100).toFixed(0)}%</div></td>
                <td className="p-3"><Badge value={c.priority} /></td>
                <td className="p-3"><Badge value={c.sentiment} /></td>
                <td className="p-3 text-slate-600">{c.department}</td>
                <td className="p-3"><Badge value={c.status} /></td>
                <td className="whitespace-nowrap p-3 text-slate-500">{fmtDate(c.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center gap-2 text-sm">
        <button className={btnGhost} disabled={page === 0} onClick={() => setPage(page - 1)}>Prev</button>
        <span className="text-slate-500">Page {page + 1} of {Math.max(1, Math.ceil(data.total / PAGE))}</span>
        <button className={btnGhost} disabled={(page + 1) * PAGE >= data.total} onClick={() => setPage(page + 1)}>Next</button>
      </div>
    </div>
  )
}
