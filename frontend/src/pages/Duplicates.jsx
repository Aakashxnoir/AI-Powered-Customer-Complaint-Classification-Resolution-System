import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Card, CatBadge, btnGhost, btnPrimary, fmtDate } from '../ui'

export default function Duplicates() {
  const [groups, setGroups] = useState(null)
  const load = () => api.duplicates().then(setGroups)
  useEffect(() => { load() }, [])
  const decide = async (complaint_id, decision) => { await api.resolveDup({ complaint_id, decision }); load() }

  if (!groups) return <p className="text-slate-500">Loading…</p>
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-slate-900">Duplicate review <span className="text-sm font-normal text-slate-500">{groups.length} groups pending</span></h1>
      <p className="text-sm text-slate-600">A duplicate is the same case raised again: MiniLM cosine ≥ 0.80 with a shared order ID or customer, or ≥ 0.88 when the customer is unknown. Different customers with similar wording are not duplicates; they appear under "Similar complaints" and in Trends. Confirm or reject each match.</p>
      {groups.length === 0 && <p className="text-slate-500">No pending duplicates.</p>}
      {groups.map((g) => (
        <Card key={g.group} title={`Group #${g.group} · ${g.members.length} complaints`}>
          <ul className="divide-y divide-slate-100">
            {g.members.map((m) => (
              <li key={m.id} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center">
                <div className="flex-1 text-sm">
                  <Link to={`/complaints/${m.id}`} className="font-medium text-indigo-600">#{m.id}</Link>
                  <span className="ml-2 text-xs text-slate-500">{fmtDate(m.created_at)}</span>
                  <span className="ml-2"><CatBadge value={m.category} /></span>
                  <p className="mt-1 text-slate-700">{m.text}</p>
                </div>
                {m.duplicate_status === 'pending' ? (
                  <div className="flex shrink-0 items-center gap-2">
                    <span className="text-xs text-slate-500">{(m.similarity * 100).toFixed(0)}% similar to #{m.duplicate_of}</span>
                    <button className={btnPrimary} onClick={() => decide(m.id, 'confirm')}>Confirm</button>
                    <button className={btnGhost} onClick={() => decide(m.id, 'reject')}>Not duplicate</button>
                  </div>
                ) : <span className="text-xs text-slate-500">{m.duplicate_status || 'original'}</span>}
              </li>
            ))}
          </ul>
        </Card>
      ))}
    </div>
  )
}
