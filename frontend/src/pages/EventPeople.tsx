import { useEffect, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { getToken, graphApi } from '../api'
import type { EventInfo, VisiblePerson } from '../types'
import { Banner, Button, Card, Row, Text } from '../ui'

export function EventPeople() {
  const { slug, event } = useOutletContext<{ slug: string; event: EventInfo }>()
  const [people, setPeople] = useState<VisiblePerson[]>([])
  const [error, setError] = useState('')

  async function load() {
    setPeople(await graphApi.people(slug))
  }

  useEffect(() => {
    load().catch((err) => setError(err.message))
  }, [slug])

  async function requestCall(person: VisiblePerson) {
    setError('')
    try {
      await graphApi.createQuery(slug, {
        type: 'skill',
        body: `5-min intro with /${person.handle || person.name}`,
        available_slots: [{ start: new Date(Date.now() + 3600000).toISOString() }],
        target_user_id: person.user_id,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not request')
    }
  }

  async function connect(person: VisiblePerson) {
    setError('')
    try {
      await graphApi.connect(slug, person.user_id)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not connect')
    }
  }

  async function respond(person: VisiblePerson, response: 'accepted' | 'declined') {
    const id = person.connection?.id
    if (!id) return
    setError('')
    try {
      await graphApi.respondConnect(id, response)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not respond')
    }
  }

  return (
    <section style={{ marginTop: 18 }}>
      {error && <Banner>{error}</Banner>}
      <div className="grid">
        {people.map((person) => {
          const state = person.connection?.state || 'none'
          return (
            <Card key={person.user_id}>
              <Text variant="heading">/{person.handle || person.name}</Text>
              <p className="empty">{person.headline}</p>
              <div className="chips">{person.skill_tags.map((t) => <span className="chip" key={t}>{t}</span>)}</div>
              <div className="chips">{person.open_to_collaborate_on.map((t) => <span className="chip" key={`c-${t}`}>collab: {t}</span>)}</div>
              {person.resume_visible && person.resume_url && (
                <Button
                  variant="ghost"
                  onClick={() => {
                    fetch(person.resume_url!, { headers: { Authorization: `Bearer ${getToken()}` } }).then((r) => r.blob()).then((b) => {
                      const url = URL.createObjectURL(b)
                      window.open(url)
                    })
                  }}
                >
                  Resume
                </Button>
              )}
              {person.email && <p>Contact: {person.email}</p>}
              {!person.is_self && (
                <Row>
                  {state === 'none' && <Button onClick={() => connect(person)}>Connect</Button>}
                  {state === 'pending_out' && <Button variant="ghost" disabled>Requested</Button>}
                  {state === 'pending_in' && (
                    <>
                      <Button onClick={() => respond(person, 'accepted')}>Accept</Button>
                      <Button variant="ghost" onClick={() => respond(person, 'declined')}>Decline</Button>
                    </>
                  )}
                  {state === 'connected' && <Button variant="secondary" disabled>Connected</Button>}
                  {event.feed_open && (
                    <Button variant="ghost" onClick={() => requestCall(person)}>Request 5-min call</Button>
                  )}
                </Row>
              )}
            </Card>
          )
        })}
      </div>
    </section>
  )
}
