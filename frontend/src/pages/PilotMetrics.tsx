import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { graphApi } from '../api'
import { useAuth } from '../auth'
import type { Insight, Metrics } from '../types'

type Pilot = Metrics & { events: Array<Metrics & { name: string; slug: string }> }

function Funnel({ steps }: { steps: NonNullable<Metrics['funnel']> }) {
  const max = Math.max(...steps.map((s) => s.count), 1)
  return (
    <ol className="funnel">
      {steps.map((step) => (
        <li key={step.id}>
          <div className="funnel-meta">
            <b>{step.count}</b>
            <span>{step.label}</span>
            <em>{step.conversion_from_prev_pct}%</em>
          </div>
          <div className="funnel-track" aria-hidden>
            <div className="funnel-fill" style={{ width: `${Math.max(6, (100 * step.count) / max)}%` }} />
          </div>
        </li>
      ))}
    </ol>
  )
}

function Insights({ items }: { items: Insight[] }) {
  if (!items.length) return null
  return (
    <section className="list">
      {items.map((item) => (
        <article className={`insight ${item.severity}`} key={item.text}>
          <p className="eyebrow">{item.severity}</p>
          <p>{item.text}</p>
        </article>
      ))}
    </section>
  )
}

export function PilotMetrics() {
  const { user, ready } = useAuth()
  const [gate, setGate] = useState('mentorwow')
  const [data, setData] = useState<Pilot | null>(null)
  const [error, setError] = useState('')

  async function load(value = gate) {
    setError('')
    try {
      setData((await graphApi.pilot(value)) as Pilot)
    } catch (err) {
      setData(null)
      setError(err instanceof Error ? err.message : 'Gated')
    }
  }

  useEffect(() => {
    if (user?.is_admin) load()
  }, [user?.is_admin])

  if (!ready) return <main className="page">Loading…</main>
  if (!user?.is_admin) return <Navigate to="/" replace />

  return (
    <main className="page">
      <p className="eyebrow">Internal · MentorWow</p>
      <h1 className="serif" style={{ fontSize: 44 }}>Pilot metrics</h1>
      <p className="lede">Funnel, conversion rates, drop-off, and product events — not just the six headline counts.</p>
      <form className="form" style={{ maxWidth: 420, margin: '16px 0' }} onSubmit={(e) => { e.preventDefault(); load() }}>
        <label className="field">
          <span>Gate (PILOT_GATE)</span>
          <input value={gate} onChange={(e) => setGate(e.target.value)} />
        </label>
        <button className="btn primary" type="submit">Refresh</button>
      </form>
      {error && <div className="error">{error}</div>}
      {data && (
        <>
          <section className="stats">
            <div className="stat"><b>{data.profiles_completed}</b><span>profiles completed ({data.profiles_completed_pct}%)</span></div>
            <div className="stat"><b>{data.match_rate_pct ?? 0}%</b><span>query match rate</span></div>
            <div className="stat"><b>{data.complete_rate_pct ?? 0}%</b><span>accepted → completed</span></div>
          </section>
          <section className="stats">
            <div className="stat"><b>{data.queries_posted}</b><span>queries posted</span></div>
            <div className="stat"><b>{data.calls_accepted}</b><span>calls accepted</span></div>
            <div className="stat"><b>{data.repeat_attendees}</b><span>repeat attendees</span></div>
          </section>
          {data.funnel && (
            <section className="card">
              <p className="eyebrow">Conversion funnel</p>
              <Funnel steps={data.funnel} />
            </section>
          )}
          <Insights items={data.insights || []} />
          {data.activity && (
            <section className="card">
              <p className="eyebrow">Last {data.activity.days} days</p>
              <p className="lede" style={{ maxWidth: 'none' }}>
                {Object.entries(data.activity.totals).length === 0
                  ? 'No client events yet. Page views and Google logins will land here.'
                  : Object.entries(data.activity.totals)
                      .map(([name, n]) => `${name.replaceAll('_', ' ')} ${n}`)
                      .join(' · ')}
              </p>
              {data.activity.top_pages.length > 0 && (
                <p className="empty">Top paths: {data.activity.top_pages.map(([path, n]) => `${path} (${n})`).join(', ')}</p>
              )}
            </section>
          )}
          <section className="list">
            {data.events.map((row) => (
              <article className="card" key={row.slug}>
                <h2 className="serif" style={{ margin: '0 0 8px', fontSize: 28 }}>{row.name}</h2>
                <p>
                  {row.profiles_completed_pct}% profiles · {row.chat_messages} chat · {row.queries_posted} queries · {row.calls_completed} calls done
                  {row.drop_off ? ` · drop-off ${row.drop_off.from_label} → ${row.drop_off.to_label}` : ''}
                </p>
                {row.funnel && <Funnel steps={row.funnel} />}
              </article>
            ))}
          </section>
        </>
      )}
    </main>
  )
}
