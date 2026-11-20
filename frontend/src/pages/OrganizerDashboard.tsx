import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getToken, graphApi } from '../api'
import type { EventInfo } from '../types'

export function OrganizerDashboard() {
  const { id } = useParams()
  const [event, setEvent] = useState<EventInfo | null>(null)
  const [copied, setCopied] = useState('')
  const [error, setError] = useState('')

  async function load() {
    if (!id) return
    setEvent(await graphApi.dashboard(Number(id)))
  }

  useEffect(() => {
    load().catch((err) => setError(err.message))
  }, [id])

  if (error) return <main className="page"><div className="error">{error}</div></main>
  if (!event) return <main className="page">Loading dashboard…</main>
  const row = event
  const m = row.metrics
  const join = row.join_url || `${window.location.origin}/join/${row.join_link_token}`

  async function copy() {
    await navigator.clipboard.writeText(join)
    setCopied('Copied join link')
  }

  async function downloadCsv() {
    const response = await fetch(`/api/organizer/events/${row.id}/csv`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${row.slug}-attendees.csv`
    a.click()
  }

  return (
    <main className="page">
      <p className="eyebrow">{row.status}</p>
      <h1 className="serif" style={{ fontSize: 44, margin: '4px 0 10px' }}>{row.name}</h1>
      {copied && <div className="success">{copied}</div>}
      <section className="card">
        <p className="eyebrow">Join link</p>
        <p style={{ wordBreak: 'break-all' }}>{join}</p>
        <div className="row-actions">
          <button className="btn primary" onClick={copy}>Copy</button>
          <Link className="btn ghost" to={`/join/${row.join_link_token}`}>Open join page</Link>
        </div>
        <img
          className="qr"
          alt="Join QR"
          src={`https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(join)}`}
        />
      </section>
      {m && (
        <>
          <section className="stats">
            <div className="stat"><b>{m.profiles_completed_pct}%</b><span>profiles completed ({m.profiles_completed}/{m.member_count})</span></div>
            <div className="stat"><b>{m.chat_messages}</b><span>chat messages · {m.unique_posters} posters</span></div>
            <div className="stat"><b>{m.repeat_attendees}</b><span>repeat attendees</span></div>
          </section>
          <section className="card">
            <p className="eyebrow">Funnel</p>
            <p>
              {m.queries_posted} posted → {m.queries_matched} matched ({m.match_rate_pct ?? 0}%) → {m.calls_accepted} accepted ({m.accept_rate_pct ?? 0}%) → {m.calls_completed} completed ({m.complete_rate_pct ?? 0}%)
            </p>
          </section>
          {(m.insights || []).length > 0 && (
            <section className="list">
              {m.insights!.map((item) => (
                <article className={`insight ${item.severity}`} key={item.text}>
                  <p className="eyebrow">{item.severity}</p>
                  <p>{item.text}</p>
                </article>
              ))}
            </section>
          )}
          <section className="grid">
            {(['skill_tags', 'can_advise_on', 'open_to_collaborate_on'] as const).map((key) => (
              <article className="card" key={key}>
                <p className="eyebrow">{key.replaceAll('_', ' ')}</p>
                {(m.group_strengths?.[key] || []).map(([tag, n]) => (
                  <p key={tag}>{tag} · {n}</p>
                ))}
                {(m.group_strengths?.[key] || []).length === 0 && <p className="empty">No consented tags yet.</p>}
              </article>
            ))}
          </section>
        </>
      )}
      <div className="row-actions">
        <button className="btn ghost" onClick={() => graphApi.closeChat(row.id).then(load)}>Close chat now</button>
        <button className="btn ghost" onClick={() => graphApi.closeFeed(row.id).then(load)}>Close feed now</button>
        <button className="btn sage" onClick={downloadCsv}>Download attendees CSV</button>
        <button className="btn primary" onClick={() => graphApi.askEvent2(row.id).then(() => setCopied('Asked for event #2'))}>
          Ask for event #2
        </button>
      </div>
    </main>
  )
}
