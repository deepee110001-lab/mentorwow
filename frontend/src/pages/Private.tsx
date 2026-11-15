import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { meApi } from '../api'
import { useAuth } from '../auth'
import type { PrivateStats } from '../types'

export function Private() {
  const { user, ready } = useAuth()
  const [stats, setStats] = useState<PrivateStats | null>(null)

  useEffect(() => {
    if (user) meApi.private().then(setStats)
  }, [user])

  if (!ready) return <main className="page">Loading…</main>
  if (!user) return <Navigate to="/login" replace />
  if (!stats) return <main className="page">Loading private ledger…</main>

  return (
    <main className="page">
      <p className="eyebrow">Only you can see this</p>
      <h1 className="serif" style={{ fontSize: 52, marginTop: 6 }}>Minutes</h1>
      <p className="lede">Topics you sat on, given and received. Never published on the handle.</p>
      <section className="stats">
        <div className="stat">
          <b>{stats.given_minutes}</b>
          <span>minutes given</span>
        </div>
        <div className="stat">
          <b>{stats.received_minutes}</b>
          <span>minutes received</span>
        </div>
        <div className="stat">
          <b>{stats.guru_balance}</b>
          <span>GURU on the chair</span>
        </div>
      </section>
      <div className="list">
        {stats.topics.map((row) => (
          <article className="card" key={row.topic}>
            <h3 className="serif" style={{ margin: 0, fontSize: 28 }}>{row.topic}</h3>
            <p>Gave {row.given_minutes} min · received {row.received_minutes} min</p>
          </article>
        ))}
        {stats.topics.length === 0 && <p className="empty">No sessions yet. The booth will write them here.</p>}
      </div>
    </main>
  )
}
