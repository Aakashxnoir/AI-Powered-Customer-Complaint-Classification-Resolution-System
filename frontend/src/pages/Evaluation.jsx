import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api'
import { Card, Loading, Stat, btnPrimary, notify } from '../ui'

const pct = (v) => (v == null ? '—' : `${(v * 100).toFixed(1)}%`)

function Confusion({ labels, matrix }) {
  const max = Math.max(...matrix.flat())
  return (
    <div className="overflow-x-auto">
      <table className="text-xs">
        <thead><tr><th className="p-1 text-left text-stone-500">true ↓ / pred →</th>{labels.map((l) => <th key={l} className="p-1 font-medium text-stone-600">{l.replace('_', ' ')}</th>)}</tr></thead>
        <tbody>{matrix.map((row, i) => (
          <tr key={i}><td className="p-1 font-medium text-stone-600">{labels[i].replace('_', ' ')}</td>
            {row.map((v, j) => (
              <td key={j} className="h-9 w-16 text-center tabular-nums" style={{ background: `rgba(${i === j ? '17,17,17' : '196,28,28'},${v / max * 0.85})`, color: v / max > 0.5 ? 'white' : '#334155' }}>{v}</td>
            ))}</tr>
        ))}</tbody>
      </table>
    </div>
  )
}

export default function Evaluation() {
  const [d, setD] = useState(null)
  const [rt, setRt] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const load = () => api.evaluation().then(setD).catch((e) => setErr(e.message))
  useEffect(() => { load() }, [])
  const retrain = async () => {
    setBusy(true)
    try {
      const r = await api.retrain(); setRt(r)
      notify(r.deployed ? 'New model deployed' : 'Accuracy dropped, current model kept')
    } catch (e) { setRt({ error: e.message }) } finally { setBusy(false); load() }
  }
  if (err && !d) return <p className="text-red-600">Backend not reachable: {err}</p>
  if (!d) return <Loading />
  const cm = d.offline.classifier_metrics
  const ev = d.offline.evaluation
  const fb = d.feedback

  const compare = cm && Object.keys(cm.minilm_logreg.per_class).map((k) => ({
    name: k, 'TF-IDF + LR': cm.tfidf_logreg.per_class[k]['f1-score'], 'MiniLM + LR': cm.minilm_logreg.per_class[k]['f1-score'],
  }))

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-medium text-stone-900">Evaluation & feedback</h1>

      {cm && <>
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Stat label="Category accuracy" value={pct(cm.minilm_logreg.accuracy)} sub={`macro-F1 ${cm.minilm_logreg.macro_f1} · test n=${cm.splits.test}`} />
          <Stat label="Baseline (TF-IDF)" value={pct(cm.tfidf_logreg.accuracy)} sub={`macro-F1 ${cm.tfidf_logreg.macro_f1}`} />
          {ev && <Stat label="Sentiment (3-class)" value={pct(ev.sentiment.accuracy_3class)} sub={`4-level ${pct(ev.sentiment.accuracy)}`} />}
          {ev && <Stat label="Duplicate F1" value={pct(ev.duplicates.f1)} sub={`P ${pct(ev.duplicates.precision)} · R ${pct(ev.duplicates.recall)}`} />}
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <Card title="Per-class F1 on test set">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={compare}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" fontSize={11} /><YAxis domain={[0, 1]} fontSize={12} /><Tooltip /><Legend />
                <Bar dataKey="TF-IDF + LR" fill="#d3cec6" /><Bar dataKey="MiniLM + LR" fill="#111111" />
              </BarChart>
            </ResponsiveContainer>
            <p className="mt-2 text-xs text-stone-500">Split train/val/test = {cm.splits.train}/{cm.splits.val}/{cm.splits.test}. Accuracy by source: {Object.entries(cm.minilm_by_source).map(([k, v]) => `${k} ${pct(v)}`).join(' · ')} (synthetic test uses unseen templates).</p>
          </Card>
          <Card title="Category confusion matrix (MiniLM + LR)"><Confusion {...cm.minilm_logreg.confusion_matrix} /></Card>
        </div>
      </>}

      {ev && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card title="Sentiment confusion matrix"><Confusion {...ev.sentiment.confusion_matrix} /></Card>
          <Card title="Entity extraction & trends">
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-stone-500"><tr><th>Entity</th><th>Precision</th><th>Recall</th><th>F1</th></tr></thead>
              <tbody>{Object.entries(ev.entities).map(([k, v]) => <tr key={k}><td className="py-1">{k}</td><td>{pct(v.precision)}</td><td>{pct(v.recall)}</td><td>{pct(v.f1)}</td></tr>)}</tbody>
            </table>
            <p className="mt-4 text-sm">Spike detection: <b>{pct(ev.trends.recall)}</b> of injected spikes found
              ({ev.trends.expected_spikes.map((s) => s[1]).join(', ')}); false alarms: {ev.trends.false_alarms.length ? ev.trends.false_alarms.map((s) => s[1]).join(', ') : 'none'}.</p>
          </Card>
        </div>
      )}

      {cm && (
        <Card title="Sample predictions (test set)">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[600px] text-sm">
              <thead className="text-left text-xs text-stone-500"><tr><th className="p-2">Text</th><th className="p-2">True</th><th className="p-2">Predicted</th><th className="p-2">Conf.</th></tr></thead>
              <tbody className="divide-y divide-stone-100">{cm.samples.map((s, i) => (
                <tr key={i} className={s.category !== s.predicted ? 'bg-red-50' : ''}><td className="p-2">{s.text}</td><td className="p-2">{s.category}</td><td className="p-2">{s.predicted}</td><td className="p-2">{pct(s.confidence)}</td></tr>
              ))}</tbody>
            </table>
          </div>
        </Card>
      )}

      <h2 className="pt-2 text-lg font-medium text-stone-900">Live feedback from agents</h2>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {['category', 'priority', 'department', 'sentiment'].map((f) => (
          <Stat key={f} label={`${f} agreement`} value={pct(fb.fields[f]?.accuracy)} sub={`${fb.fields[f]?.reviewed || 0} reviewed · ${fb.fields[f]?.corrected || 0} corrected`} />
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Where the system performs poorly">
          {fb.weak_spots.length === 0 ? <p className="text-sm text-stone-500">No weak categories yet (needs ≥2 reviews per category with &lt;90% agreement).</p> : (
            <ul className="space-y-1 text-sm">{fb.weak_spots.map((w) => <li key={w.category}><b>{w.category}</b>: {pct(w.accuracy)} agreement over {w.reviewed} reviews</li>)}</ul>
          )}
          <p className="mt-3 text-sm text-stone-600">{pct(fb.low_confidence_share)} of complaints have category confidence below 60%.</p>
          <p className="mt-1 text-sm text-stone-600">Drafts: {Object.entries(fb.responses).map(([k, v]) => `${v} ${k}`).join(' · ') || 'no decisions yet'}{fb.fields.duplicate && ` · duplicates: ${fb.fields.duplicate.reviewed} reviewed, ${fb.fields.duplicate.corrected} rejected`}</p>
          {fb.recent_corrections.length > 0 && (
            <div className="mt-3 text-sm"><p className="font-medium">Recent corrections</p>
              <ul className="mt-1 space-y-0.5 text-stone-600">{fb.recent_corrections.map((r, i) => <li key={i}>#{r.complaint_id} {r.field}: {r.predicted} → <b>{r.corrected}</b></li>)}</ul></div>
          )}
        </Card>
        <Card title="Retrain classifier with feedback">
          <p className="text-sm text-stone-600">Refits the classifier on the training set plus every reviewer-corrected complaint (weighted ×3), then checks held-out test accuracy. The new model is deployed only if accuracy drops by no more than 1 point, so bad feedback cannot silently break the model.</p>
          <button className={`${btnPrimary} mt-3`} onClick={retrain} disabled={busy}>{busy ? 'Retraining…' : 'Retrain now'}</button>
          {rt && (rt.error ? <p className="mt-2 text-sm text-red-600">{rt.error}</p> :
            <p className="mt-2 text-sm">Learned from <b>{rt.feedback_examples}</b> corrections. Test accuracy {pct(rt.test_accuracy_before)} → <b>{pct(rt.test_accuracy_after)}</b>. {rt.deployed ? 'New model deployed.' : 'Accuracy dropped, so the current model was kept. Check the corrections.'}</p>)}
        </Card>
      </div>
    </div>
  )
}
