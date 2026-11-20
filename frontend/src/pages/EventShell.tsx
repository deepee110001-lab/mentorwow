import { useEffect, useState } from 'react'
import { NavLink, Outlet, useParams } from 'react-router-dom'
import { graphApi } from '../api'
import { useAuth } from '../auth'
import type { EventInfo } from '../types'
import { Banner, Button, Page, Text } from '../ui'

export function EventShell() {
  const { slug } = useParams()
  const { user, ready } = useAuth()
  const [event, setEvent] = useState<EventInfo | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!slug || !user) return
    graphApi.event(slug).then((data) => setEvent(data.event)).catch((err) => setError(err.message))
  }, [slug, user])

  if (!ready) return <Page>Loading…</Page>
  if (!user) {
    return (
      <Page>
        <Text variant="lede">Sign in to enter this event.</Text>
        <Button to={`/login?next=/e/${slug}/feed`}>Sign in</Button>
      </Page>
    )
  }
  if (error) {
    return (
      <Page>
        <Banner>{error}</Banner>
        <Text variant="body">If you have not joined, use the event join link.</Text>
        <Button variant="ghost" to="/join/mentorwow-join">Pilot join link</Button>
      </Page>
    )
  }
  if (!event || !slug) return <Page>Loading event…</Page>

  return (
    <Page className="event-page">
      <Text variant="eyebrow">{event.status}</Text>
      <Text variant="title">{event.name}</Text>
      <nav className="tabs">
        <NavLink to={`/e/${slug}/feed`}>Feed</NavLink>
        <NavLink to={`/e/${slug}/people`}>People</NavLink>
        <NavLink to={`/e/${slug}/chat`}>Chat</NavLink>
        <NavLink to={`/e/${slug}/calls`}>My Calls</NavLink>
        <NavLink to={`/e/${slug}/profile`}>Profile</NavLink>
      </nav>
      <Outlet context={{ event, slug }} />
    </Page>
  )
}
