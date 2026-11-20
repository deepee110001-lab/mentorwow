import { useEffect, useState } from 'react'
import { graphApi } from '../api'
import { useAuth } from '../auth'
import type { ChatMsg, ConnectionPerson } from '../types'
import { Banner, Button, Card, Page, Row, Text } from '../ui'

export function Connected() {
  const { user, ready } = useAuth()
  const [incoming, setIncoming] = useState<ConnectionPerson[]>([])
  const [outgoing, setOutgoing] = useState<ConnectionPerson[]>([])
  const [connected, setConnected] = useState<ConnectionPerson[]>([])
  const [polls, setPolls] = useState<ChatMsg[]>([])
  const [error, setError] = useState('')

  async function load() {
    const [graph, mine] = await Promise.all([graphApi.connections(), graphApi.myPolls()])
    setIncoming(graph.incoming)
    setOutgoing(graph.outgoing)
    setConnected(graph.connected)
    setPolls(mine)
  }

  useEffect(() => {
    if (!user) return
    load().catch((err) => setError(err instanceof Error ? err.message : 'Could not load'))
  }, [user])

  if (!ready) return <Page>Loading…</Page>
  if (!user) {
    return (
      <Page>
        <Text variant="lede">Sign in to see people you connected with.</Text>
        <Button to="/login?next=/connected">Sign in</Button>
      </Page>
    )
  }

  return (
    <Page>
      <Text variant="eyebrow">Always there</Text>
      <Text variant="title">Connected</Text>
      <Text variant="lede">People you connect with in a room stay here after the event closes. Email still stays hidden until a call.</Text>
      {error && <Banner>{error}</Banner>}

      {incoming.length > 0 && (
        <section className="list" style={{ marginTop: 28 }}>
          <Text variant="heading">Requests</Text>
          {incoming.map((person) => (
            <Card key={person.id}>
              <Text variant="heading">/{person.handle}</Text>
              <p className="empty">{person.headline || 'Wants to stay connected'}</p>
              <Row>
                <Button onClick={() => graphApi.respondConnect(person.id, 'accepted').then(load).catch((err) => setError(err.message))}>
                  Accept
                </Button>
                <Button variant="ghost" onClick={() => graphApi.respondConnect(person.id, 'declined').then(load).catch((err) => setError(err.message))}>
                  Decline
                </Button>
              </Row>
            </Card>
          ))}
        </section>
      )}

      <section className="list" style={{ marginTop: 28 }}>
        <Text variant="heading">Your people</Text>
        {connected.map((person) => (
          <Card key={person.id}>
            <Text variant="heading">/{person.handle}</Text>
            <p className="empty">
              {person.headline}
              {person.event_name ? ` · met at ${person.event_name}` : ''}
            </p>
            <Row>
              <Button
                variant="ghost"
                onClick={() => graphApi.disconnect(person.id).then(load).catch((err) => setError(err.message))}
              >
                Disconnect
              </Button>
            </Row>
          </Card>
        ))}
        {connected.length === 0 && <p className="empty">No one yet. Open an event People tab and tap Connect.</p>}
      </section>

      {outgoing.length > 0 && (
        <section className="list" style={{ marginTop: 28 }}>
          <Text variant="heading">Waiting</Text>
          {outgoing.map((person) => (
            <Card key={person.id}>
              <Text variant="heading">/{person.handle}</Text>
              <p className="empty">Requested{person.event_name ? ` at ${person.event_name}` : ''}</p>
            </Card>
          ))}
        </section>
      )}

      <section className="list" style={{ marginTop: 28 }}>
        <Text variant="heading">Your polls</Text>
        {polls.map((poll) => (
          <Card key={poll.id} className="poll">
            <p className="eyebrow">{poll.event?.name || 'Yay or Nay'}</p>
            <p>{poll.body}</p>
            {poll.poll && (
              <p className="empty">
                Yay {poll.poll.yay} · Nay {poll.poll.nay} · {poll.poll.total} vote{poll.poll.total === 1 ? '' : 's'}
              </p>
            )}
          </Card>
        ))}
        {polls.length === 0 && <p className="empty">Polls you attach in chat show up here.</p>}
      </section>
    </Page>
  )
}
