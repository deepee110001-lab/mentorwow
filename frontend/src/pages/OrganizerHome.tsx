import { useEffect, useState } from 'react'
import { graphApi } from '../api'
import { useAuth } from '../auth'
import type { EventInfo } from '../types'
import { Banner, Button, Card, Page, Row, Text } from '../ui'

export function OrganizerHome() {
  const { user, ready } = useAuth()
  const [events, setEvents] = useState<EventInfo[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    if (!user) return
    graphApi.organizerEvents().then(setEvents).catch((err) => setError(err.message))
  }, [user])

  if (!ready) return <Page>Loading…</Page>
  if (!user) {
    return (
      <Page>
        <Text variant="title">Organizer home</Text>
        <Text variant="lede">Sign in to create events and copy a join link.</Text>
        <Button to="/login?next=/organizer">Sign in</Button>
      </Page>
    )
  }

  return (
    <Page>
      <Text variant="eyebrow">Organizer</Text>
      <Text variant="title">Your events</Text>
      {error && <Banner>{error}</Banner>}
      <Button to="/organizer/events/new">Create event</Button>
      <section className="list" style={{ marginTop: 22 }}>
        {events.map((event) => (
          <Card key={event.id}>
            <span className="status">{event.status}</span>
            <Text variant="heading">{event.name}</Text>
            <Text variant="muted">/{event.slug} · feed until {new Date(event.feed_closes_at).toLocaleString()}</Text>
            <Row>
              <Button variant="secondary" to={`/organizer/events/${event.id}`}>Dashboard</Button>
              <Button variant="ghost" to={`/e/${event.slug}/feed`}>Open as attendee</Button>
            </Row>
          </Card>
        ))}
        {events.length === 0 && <Text variant="muted">No events yet. Create one to get a join link.</Text>}
      </section>
    </Page>
  )
}
