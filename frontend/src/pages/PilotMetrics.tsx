import { useEffect, useState } from 'react'
import { graphApi } from '../api'
import type { Metrics } from '../types'

type Pilot = Metrics & { events: Array<Metrics & { name: string; slug: string }> }

export function PilotMetrics() {
  const [gate, setGate] = useState('mentorwow')
  const [data, setData] = useState<Pilot | null>(null)
  const [error, setError] = useState('')

  async function load(value = gate) {
    setError('')
    try {
      setData(await graphApi.pilot(value) as Pilot)
    } catch (err) {
      setData(null)
      setError(err instanceof Error ? err.message : 'Gated')
    }
  }

  useEffect(() => {
    load()
  }, [])

  return (
    <main className="page">
      <p className="eyebrow">Internal · CEDAT</p>
      <h1 className="serif" style={{ fontSize: 44 }}>Pilot metrics</h1>
      <p className="lede">Six numbers for the room: completed profiles, chat, queries, matches, accepted calls, completed calls — plus repeats.</p>
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
            <div className="stat"><b>{data.profiles_completed}</b><span>profiles completed</span></div>
            <div className="stat"><b>{data.chat_messages}</b><span>chat messages</span></div>
            <div className="stat"><b>{data.queries_posted}</b><span>queries posted</span></div>
          </section>
          <section className="stats">
            <div className="stat"><b>{data.queries_matched}</b><span>queries matched</span></div>
            <div className="stat"><b>{data.calls_accepted}</b><span>queries accepted → calls</span></div>
            <div className="stat"><b>{data.calls_completed}</b><span>calls completed</span></div>
          </section>
          <p className="lede">Repeat attendees: {data.repeat_attendees}</p>
          <section className="list">
            {data.events.map((row) => (
              <article className="card" key={row.slug}>
                <h2 className="serif" style={{ margin: '0 0 8px', fontSize: 28 }}>{row.name}</h2>
                <p>{row.profiles_completed_pct}% profiles · {row.chat_messages} chat · {row.queries_posted} queries · {row.calls_completed} calls done</p>
              </article>
            ))}
          </section>
        </>
      )}
    </main>
  )
}
