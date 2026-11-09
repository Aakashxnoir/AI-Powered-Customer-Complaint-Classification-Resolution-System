import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Card, CatBadge, Loading, btnGhost, btnPrimary, fmtDate, notify } from '../ui'

export default function Duplicates() {
  const [groups, setGroups] = useState(null)
  const [err, setErr] = useState('')
  const load = () => api.duplicates().then(setGroups).catch((e) => setErr(e.message))
  useEffect(() => { load() }, [])
  const [busy, setBusy] = useState(false)
  const decide = async (complaint_id, decision) => {
    setBusy(true); setErr('')
    try {
      await api.resolveDup({ complaint_id, decision })
      notify(decision === 'confirm' ? `#${complaint_id} confirmed as a duplicate` : `#${complaint_id} kept as its own complaint`)
    } catch (e) { setErr(e.message) } finally { setBusy(false); load() }
  }

  if (err && !groups) return <p className="text-error">Backend not reachable: {err}</p>
  if (!groups) return <Loading />
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-medium text-stone-900">Duplicate review <span className="text-sm font-normal text-stone-500">{groups.length} groups pending</span></h1>
      <p className="text-sm text-stone-600">A duplicate is the same case raised again: MiniLM cosine ≥ 0.80 with a shared order ID or customer, or ≥ 0.88 when the customer is unknown. Different customers with similar wording are not duplicates; they appear under "Similar complaints" and in Trends. Confirm or reject each match.</p>
      {err && <p role="alert" className="text-sm text-error">{err}</p>}
      {groups.length === 0 && <p className="text-stone-500">No pending duplicates.</p>}
      {groups.map((g) => (
        <Card key={g.group} title={`Group #${g.group} · ${g.members.length} complaints`}>
          <ul className="divide-y divide-stone-100">
            {g.members.map((m) => (
              <li key={m.id} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center">
                <div className="flex-1 text-sm">
                  <Link to={`/complaints/${m.id}`} className="font-medium text-brand-600">#{m.id}</Link>
                  <span className="ml-2 text-xs text-stone-500">{fmtDate(m.created_at)}</span>
                  <span className="ml-2"><CatBadge value={m.category} /></span>
                  <p className="mt-1 text-stone-700">{m.text}</p>
                </div>
                {m.duplicate_status === 'pending' ? (
                  <div className="flex shrink-0 items-center gap-2">
                    <span className="text-xs text-stone-500">{(m.similarity * 100).toFixed(0)}% similar to #{m.duplicate_of}</span>
                    <button className={btnPrimary} disabled={busy} onClick={() => decide(m.id, 'confirm')}>Confirm</button>
                    <button className={btnGhost} disabled={busy} onClick={() => decide(m.id, 'reject')}>Not duplicate</button>
                  </div>
                ) : <span className="text-xs text-stone-500">{m.duplicate_status || 'original'}</span>}
              </li>
            ))}
          </ul>
        </Card>
      ))}
    </div>
  )
}
