import { useEffect, useState } from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
import { api } from './api'
import Overview from './pages/Overview'
import Intake from './pages/Intake'
import Inbox from './pages/Inbox'
import Detail from './pages/Detail'
import Duplicates from './pages/Duplicates'
import Trends from './pages/Trends'
import Evaluation from './pages/Evaluation'
import { Toast } from './ui'

const NAV = [
  ['/', 'Overview'], ['/intake', 'New complaint'], ['/inbox', 'Inbox'],
  ['/duplicates', 'Duplicates'], ['/trends', 'Trends'], ['/evaluation', 'Evaluation'],
]

export default function App() {
  const [llm, setLlm] = useState('')
  useEffect(() => { api.health().then((h) => setLlm(h.llm)).catch(() => setLlm('offline')) }, [])
  return (
    <div className="min-h-screen bg-page text-stone-800 md:flex">
      <aside className="border-b border-stone-200 bg-white md:fixed md:inset-y-0 md:w-56 md:border-b-0 md:border-r">
        <div className="px-5 py-4">
          <a href="/" className="flex items-center gap-2 text-lg font-medium tracking-tight text-ink">
            <svg viewBox="0 0 24 24" className="h-5 w-5 fill-brand-600" aria-hidden="true"><circle cx="6.5" cy="6.5" r="4.5" /><circle cx="17.5" cy="6.5" r="4.5" /><circle cx="6.5" cy="17.5" r="4.5" /><rect x="13" y="13" width="9" height="9" rx="1.5" /></svg>
            ComplaintIQ
          </a>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-col md:overflow-visible">
          {NAV.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === '/'}
              className={({ isActive }) => `whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium ${isActive ? 'bg-brand-50 text-brand-700' : 'text-stone-600 hover:bg-stone-100'}`}>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="hidden px-5 py-4 text-xs text-stone-500 md:absolute md:bottom-0 md:block">
          Drafting: <span className="font-medium text-stone-700">{llm || '…'}</span>
        </div>
      </aside>
      <main className="min-w-0 flex-1 p-4 md:ml-56 md:p-8">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/intake" element={<Intake />} />
          <Route path="/inbox" element={<Inbox />} />
          <Route path="/complaints/:id" element={<Detail />} />
          <Route path="/duplicates" element={<Duplicates />} />
          <Route path="/trends" element={<Trends />} />
          <Route path="/evaluation" element={<Evaluation />} />
        </Routes>
      </main>
      <Toast />
    </div>
  )
}
