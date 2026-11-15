import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { graphApi } from '../api'
import { useAuth } from '../auth'
import type { EventInfo } from '../types'

export function OrganizerHome() {
  const { user, ready } = useAuth()
  const [events, setEvents] = useState<EventInfo[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    if (!user) return
    graphApi.organizerEvents().then(setEvents).catch((err) => setError(err.message))
  }, [user])

  if (!ready) return <main className="page">Loading…</main>
  if (!user) {
    return (
      <main className="page">
        <h1 className="serif">Organizer home</h1>
        <p>Sign in to create events and copy a join link.</p>
        <Link className="btn primary" to="/login?next=/organizer">Sign in</Link>
      </main>
    )
  }

  return (
    <main className="page">
      <p className="eyebrow">Organizer</p>
      <h1 className="serif" style={{ fontSize: 48, margin: '4px 0 12px' }}>Your events</h1>
      {error && <div className="error">{error}</div>}
      <Link className="btn primary" to="/organizer/events/new">Create event</Link>
      <section className="list" style={{ marginTop: 22 }}>
        {events.map((event) => (
          <article className="card" key={event.id}>
            <span className="status">{event.status}</span>
            <h2 className="serif" style={{ margin: '8px 0 6px', fontSize: 32 }}>{event.name}</h2>
            <p className="empty">/{event.slug} · feed until {new Date(event.feed_closes_at).toLocaleString()}</p>
            <div className="row-actions">
              <Link className="btn sage" to={`/organizer/events/${event.id}`}>Dashboard</Link>
              <Link className="btn ghost" to={`/e/${event.slug}/feed`}>Open as attendee</Link>
            </div>
          </article>
        ))}
        {events.length === 0 && <p className="empty">No events yet. Create one to get a join link.</p>}
      </section>
    </main>
  )
}
