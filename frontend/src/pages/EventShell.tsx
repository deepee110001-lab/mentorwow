import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useParams } from 'react-router-dom'
import { graphApi } from '../api'
import { useAuth } from '../auth'
import type { EventInfo } from '../types'

export function EventShell() {
  const { slug } = useParams()
  const { user, ready } = useAuth()
  const [event, setEvent] = useState<EventInfo | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!slug || !user) return
    graphApi.event(slug).then((data) => setEvent(data.event)).catch((err) => setError(err.message))
  }, [slug, user])

  if (!ready) return <main className="page">Loading…</main>
  if (!user) {
    return (
      <main className="page">
        <p>Sign in to enter this event.</p>
        <Link className="btn primary" to={`/login?next=/e/${slug}/feed`}>Sign in</Link>
      </main>
    )
  }
  if (error) {
    return (
      <main className="page">
        <div className="error">{error}</div>
        <p>If you have not joined, use the event join link.</p>
        <Link className="btn ghost" to="/join/cedat-join-demo">Pilot join link</Link>
      </main>
    )
  }
  if (!event || !slug) return <main className="page">Loading event…</main>

  return (
    <main className="page event-page">
      <p className="eyebrow">{event.status}</p>
      <h1 className="serif" style={{ fontSize: 40, margin: '4px 0 12px' }}>{event.name}</h1>
      <nav className="tabs">
        <NavLink to={`/e/${slug}/feed`}>Feed</NavLink>
        <NavLink to={`/e/${slug}/people`}>People</NavLink>
        <NavLink to={`/e/${slug}/chat`}>Chat</NavLink>
        <NavLink to={`/e/${slug}/calls`}>My Calls</NavLink>
        <NavLink to={`/e/${slug}/profile`}>Profile</NavLink>
      </nav>
      <Outlet context={{ event, slug }} />
    </main>
  )
}
