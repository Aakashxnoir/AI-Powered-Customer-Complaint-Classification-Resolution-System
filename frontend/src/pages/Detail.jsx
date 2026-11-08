import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import { Badge, CAT_COLORS, CATEGORIES, Card, CatBadge, DEPARTMENTS, Loading, PRIORITIES, SENTIMENTS, ScoreBar, btnGhost, btnPrimary, fmtDate, input, notify } from '../ui'

const ENTITY_LABELS = { order_ids: 'Order ID', amounts: 'Amount', products: 'Product', locations: 'Location', dates: 'Date', emails: 'Email', phones: 'Phone' }

function highlight(text, words) {
  if (!words.length) return text
  const set = new Set(words.map((w) => w.toLowerCase()))
  return text.split(/(\s+)/).map((tok, i) =>
    set.has(tok.replace(/[.,!?]/g, '').toLowerCase())
      ? <mark key={i} className="rounded bg-amber-200 px-0.5">{tok}</mark> : tok)
}

function Correct({ field, value, options, onSave }) {
  const [open, setOpen] = useState(false)
  const [v, setV] = useState(value)
  if (!open) return <button className="text-xs text-brand-600 hover:underline" onClick={() => setOpen(true)}>correct</button>
  return (
    <span className="inline-flex gap-1">
      <select className={`${input} py-0.5 text-xs`} value={v} onChange={(e) => setV(e.target.value)}>
        {options.map((o) => <option key={o}>{o}</option>)}
      </select>
      <button className="text-xs font-medium text-brand-600" onClick={() => { onSave(field, v); setOpen(false) }}>save</button>
    </span>
  )
}

export default function Detail() {
  const { id } = useParams()
  const [c, setC] = useState(null)
  const [busy, setBusy] = useState('')
  const [reply, setReply] = useState('')
  const [err, setErr] = useState('')

  const load = () => api.get(id).then((d) => { setC(d); setReply(d.final_response || d.draft?.response || '') }).catch((e) => setErr(e.message))
  useEffect(() => { load() }, [id])

  const review = async (field, value) => { await api.review(id, { field, value }); notify(`${field} set to ${value}`); load() }
  const confirmAll = async () => {
    for (const f of ['category', 'priority', 'department', 'sentiment']) await api.review(id, { field: f, value: c[f] })
    notify('All four predictions confirmed')
    load()
  }
  const draft = async () => {
    setBusy('draft'); setErr('')
    try { const d = await api.draft(id); setC({ ...c, draft: d }); setReply(d.response) } catch (e) { setErr(e.message) } finally { setBusy('') }
  }
  const respond = async (action) => {
    setBusy(action); await api.respond(id, { action, text: reply }); await load(); setBusy('')
    notify(action === 'approve' ? 'Reply approved' : 'Draft rejected')
  }

  if (err && !c) return <p className="text-red-600">{err}</p>
  if (!c) return <Loading />
  const scores = Object.entries(c.category_scores).sort((a, b) => b[1] - a[1])
  const ents = Object.entries(c.entities).filter(([, v]) => v.length)

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <Link to="/inbox" className="text-sm text-brand-600">← Inbox</Link>
          <h1 className="text-xl font-medium text-stone-900">Complaint #{c.id}</h1>
          <p className="text-sm text-stone-500">{fmtDate(c.created_at)} · via {c.channel}{c.customer && ` · ${c.customer}`}</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge value={c.status} />
          {c.reviewed ? <span className="text-xs text-emerald-700">✓ reviewed</span>
            : <button className={btnGhost} onClick={confirmAll}>Confirm all predictions</button>}
        </div>
      </div>

      <Card title="Complaint text" action={<span className="text-xs text-stone-500">highlighted = words that drove the category</span>}>
        <p className="leading-relaxed">{highlight(c.text, c.explanation.map((e) => e.word))}</p>
        {ents.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {ents.map(([k, v]) => v.map((x) => (
              <span key={k + x} className="rounded-md bg-stone-100 px-2 py-1 text-xs"><span className="text-stone-500">{ENTITY_LABELS[k]}:</span> <b>{k === 'amounts' ? `₹${Number(x).toLocaleString()}` : x}</b></span>
            )))}
          </div>
        )}
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Category" action={<Correct field="category" value={c.category} options={CATEGORIES} onSave={review} />}>
          <div className="mb-3 flex items-center gap-2"><CatBadge value={c.category} />
            {c.analysis.original?.category !== c.category && <span className="text-xs text-stone-500">(model said {c.analysis.original.category})</span>}</div>
          <div className="space-y-1.5">{scores.map(([k, v]) => <ScoreBar key={k} label={k} value={v} color={CAT_COLORS[k]} highlight={k === c.category} />)}</div>
          {c.explanation.length > 0 && (
            <p className="mt-3 text-xs text-stone-600">Why: removing <b>{c.explanation.slice(0, 3).map((e) => `"${e.word}"`).join(', ')}</b> lowers the {c.analysis.original?.category} score by {c.explanation.slice(0, 3).map((e) => (e.impact * 100).toFixed(1) + '%').join(', ')}.</p>
          )}
        </Card>

        <Card title="Sentiment & emotion" action={<Correct field="sentiment" value={c.sentiment} options={SENTIMENTS} onSave={review} />}>
          <div className="mb-3 flex items-center gap-2"><Badge value={c.sentiment} />
            <span className="text-xs text-stone-500">{(c.sentiment_confidence * 100).toFixed(0)}% · emotion <b>{c.analysis.emotion}</b> · frustration {(c.analysis.frustration * 100).toFixed(0)}%</span></div>
          <div className="space-y-1.5">
            {Object.entries(c.analysis.sentiment_scores).map(([k, v]) => <ScoreBar key={k} label={k} value={v} color="#64748b" />)}
            <div className="pt-2" />
            {Object.entries(c.analysis.emotion_scores).sort((a, b) => b[1] - a[1]).slice(0, 4).map(([k, v]) => <ScoreBar key={k} label={k} value={v} color="#f97316" />)}
          </div>
        </Card>

        <Card title="Priority" action={<Correct field="priority" value={c.priority} options={PRIORITIES} onSave={review} />}>
          <div className="mb-3 flex items-center gap-2"><Badge value={c.priority} /><span className="text-xs text-stone-500">score {c.priority_score} (critical ≥8, high ≥5, medium ≥3)</span></div>
          <ul className="space-y-1 text-sm">
            {c.priority_factors.map((f, i) => <li key={i} className="flex gap-2"><span className="w-8 shrink-0 text-right tabular-nums text-stone-500">+{f.points}</span>{f.reason}</li>)}
          </ul>
        </Card>

        <Card title="Routing" action={<Correct field="department" value={c.department} options={DEPARTMENTS} onSave={review} />}>
          <p className="text-lg font-medium text-stone-900">{c.department}</p>
          <p className="mt-1 text-sm text-stone-600">{c.routing_reason}</p>
          {c.duplicates?.length > 0 && (
            <div className="mt-4 rounded-lg bg-brand-50 p-3 text-sm">
              <p className="font-medium text-brand-900">Possible duplicate{c.duplicate_similarity && ` (similarity ${(c.duplicate_similarity * 100).toFixed(0)}%)`}</p>
              {c.duplicates.map((d) => <Link key={d.id} to={`/complaints/${d.id}`} className="mt-1 block truncate text-brand-700 hover:underline">#{d.id}: {d.text}</Link>)}
            </div>
          )}
        </Card>
      </div>

      {c.similar?.length > 0 && (
        <Card title="Similar complaints (semantic search, all customers)">
          <ul className="space-y-1 text-sm">
            {c.similar.map((s) => (
              <li key={s.id} className="flex gap-3">
                <span className="w-12 shrink-0 tabular-nums text-stone-500">{(s.similarity * 100).toFixed(0)}%</span>
                <Link to={`/complaints/${s.id}`} className="truncate text-brand-600 hover:underline">#{s.id}: {s.text}</Link>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Card title="Resolution assistant" action={<button className={btnGhost} onClick={draft} disabled={!!busy}>{busy === 'draft' ? 'Drafting…' : c.draft ? 'Regenerate' : 'Generate draft'}</button>}>
        {err && <p className="mb-2 text-sm text-red-600">{err}</p>}
        {!c.draft ? <p className="text-sm text-stone-500">Generate a reply grounded in approved support guidance. Nothing is sent without approval.</p> : (
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2 text-xs text-stone-500">
              <span>Generated by <b>{c.draft.generator}</b></span>
              {c.draft.llm_error && <span className="text-amber-700">(LLM failed, template used)</span>}
              <span>· Grounded in: {c.draft.sources.map((s) => <span key={s.id} className="ml-1 rounded bg-stone-100 px-1.5 py-0.5">{s.title}</span>)}</span>
            </div>
            <textarea className={`${input} h-48 w-full font-sans`} value={reply} onChange={(e) => setReply(e.target.value)} disabled={c.status !== 'new'} />
            <p className="text-sm"><span className="font-medium">Next action for staff:</span> {c.draft.next_action}</p>
            {c.status === 'new' ? (
              <div className="flex gap-2">
                <button className={btnPrimary} disabled={!!busy} onClick={() => respond('approve')}>Approve & send</button>
                <button className={btnGhost} disabled={!!busy} onClick={() => respond('reject')}>Reject draft</button>
              </div>
            ) : <p className="text-sm text-emerald-700">Response {c.status}.</p>}
          </div>
        )}
      </Card>
    </div>
  )
}
