import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { Card, btnPrimary, input } from '../ui'

const EXAMPLES = [
  'I was charged twice for order ORD-554210! ₹12,499 debited two times from my card on 5 Nov. This is unacceptable, fix it today.',
  'My SmartWatch X2 is overheating badly and smells like burning plastic. Order ORD-883120.',
  'Order ORD-120034 was supposed to arrive in Chennai on 2 Nov but tracking is stuck at the hub for a week.',
  'Someone else logged into my account and placed an order without my permission.',
]

export default function Intake() {
  const nav = useNavigate()
  const [text, setText] = useState('')
  const [customer, setCustomer] = useState('')
  const [busy, setBusy] = useState('')
  const [err, setErr] = useState('')
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)

  const submit = async (e) => {
    e.preventDefault()
    setBusy('one'); setErr('')
    try {
      const c = await api.create({ text, customer: customer || null })
      nav(`/complaints/${c.id}`)
    } catch (ex) { setErr(ex.message) } finally { setBusy('') }
  }

  const upload = async () => {
    setBusy('csv'); setErr(''); setResult(null)
    try { setResult(await api.upload(file)) } catch (ex) { setErr(ex.message) } finally { setBusy('') }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-medium text-stone-900">New complaint</h1>
      {err && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{err}</p>}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Single complaint">
          <form onSubmit={submit} className="space-y-3">
            <input className={`${input} w-full`} placeholder="Customer name / ID (optional)" value={customer} onChange={(e) => setCustomer(e.target.value)} />
            <textarea className={`${input} h-40 w-full`} placeholder="Describe the issue…" value={text} onChange={(e) => setText(e.target.value)} required minLength={10} />
            <div className="flex flex-wrap gap-2">
              {EXAMPLES.map((ex, i) => (
                <button type="button" key={i} onClick={() => setText(ex)} className="rounded-full bg-stone-100 px-2.5 py-1 text-xs text-stone-600 hover:bg-stone-200">Example {i + 1}</button>
              ))}
            </div>
            <button className={btnPrimary} disabled={busy}>{busy === 'one' ? 'Analysing…' : 'Analyse complaint'}</button>
          </form>
        </Card>

        <Card title="Batch CSV upload">
          <p className="mb-3 text-sm text-stone-600">
            CSV with a <code className="rounded bg-stone-100 px-1">text</code> column. Optional: <code className="rounded bg-stone-100 px-1">customer</code>, <code className="rounded bg-stone-100 px-1">created_at</code>. Max 2000 rows.
            Rows that are empty, too short or exact repeats are reported and skipped.
          </p>
          <input type="file" accept=".csv" onChange={(e) => setFile(e.target.files[0])} className="mb-3 block text-sm" />
          <button className={btnPrimary} disabled={!file || busy} onClick={upload}>{busy === 'csv' ? 'Processing…' : 'Upload & analyse'}</button>
          {result && (
            <div className="mt-4 space-y-2 text-sm">
              <p><b>{result.processed}</b> of {result.received} rows processed · <b>{result.duplicates_found}</b> likely duplicates</p>
              <p className="text-stone-600">Categories: {Object.entries(result.by_category).map(([k, v]) => `${k} ${v}`).join(' · ')}</p>
              <p className="text-stone-600">Priority: {Object.entries(result.by_priority).map(([k, v]) => `${k} ${v}`).join(' · ')}</p>
              {result.errors.length > 0 && (
                <details className="rounded-lg bg-amber-50 p-2 text-amber-900">
                  <summary>{result.errors.length} rows skipped</summary>
                  <ul className="mt-1 list-disc pl-5">{result.errors.slice(0, 50).map((e) => <li key={e.row}>Row {e.row}: {e.error}</li>)}</ul>
                </details>
              )}
              <Link to="/inbox" className="text-brand-600">Open inbox →</Link>
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}
