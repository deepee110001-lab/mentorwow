import { useEffect, useState, type FormEvent } from 'react'
import { useOutletContext } from 'react-router-dom'
import { graphApi } from '../api'
import type { EventInfo, QueryItem } from '../types'

export function EventFeed() {
  const { slug, event } = useOutletContext<{ slug: string; event: EventInfo }>()
  const [items, setItems] = useState<QueryItem[]>([])
  const [type, setType] = useState<'skill' | 'collaboration'>('skill')
  const [body, setBody] = useState('')
  const [slot, setSlot] = useState('')
  const [error, setError] = useState('')

  async function load() {
    setItems(await graphApi.queries(slug))
  }

  useEffect(() => {
    load().catch((err) => setError(err.message))
  }, [slug])

  async function submit(ev: FormEvent) {
    ev.preventDefault()
    setError('')
    try {
      await graphApi.createQuery(slug, {
        type,
        body,
        available_slots: slot ? [{ start: new Date(slot).toISOString() }] : [{ start: new Date(Date.now() + 3600000).toISOString() }],
      })
      setBody('')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not post')
    }
  }

  async function accept(item: QueryItem) {
    const start = item.available_slots[0]?.start
    await graphApi.respond(item.id, { response: 'accepted', slot: { start } })
    await load()
  }

  return (
    <section className="list" style={{ marginTop: 18 }}>
      {!event.feed_open && <div className="error">Feed is closed. Queries are read-only.</div>}
      {error && <div className="error">{error}</div>}
      {event.feed_open && (
        <form className="card form" onSubmit={submit}>
          <div className="role-pick">
            <button type="button" className={type === 'skill' ? 'on' : ''} onClick={() => setType('skill')}>
              <b>Skill query</b>
              <div>Ask for advice. AI routes to 3–5 people.</div>
            </button>
            <button type="button" className={type === 'collaboration' ? 'on' : ''} onClick={() => setType('collaboration')}>
              <b>Collaboration</b>
              <div>Find a complement, not a résumé blast.</div>
            </button>
          </div>
          <label className="field">
            <span>Request (280 chars)</span>
            <textarea maxLength={280} rows={3} value={body} onChange={(e) => setBody(e.target.value)} required />
          </label>
          <label className="field">
            <span>Available slot</span>
            <input type="datetime-local" value={slot} onChange={(e) => setSlot(e.target.value)} />
          </label>
          <button className="btn primary" type="submit">Route this query</button>
        </form>
      )}
      {items.map((item) => (
        <article className="card" key={item.id}>
          <span className={`chip`}>{item.type}</span>
          {item.matched && item.author.user_id && <span className="status pending">matched to you</span>}
          <p><strong>{item.author.name}</strong> · {item.author.headline}</p>
          <p>{item.body}</p>
          {item.matched && item.my_response === 'pending' && event.feed_open && (
            <div className="row-actions">
              <button className="btn sage" onClick={() => accept(item)}>Accept 5 min</button>
              <button className="btn ghost" onClick={() => graphApi.respond(item.id, { response: 'declined' }).then(load)}>Decline</button>
            </div>
          )}
          {item.my_response && item.my_response !== 'pending' && <p className="empty">You {item.my_response}.</p>}
        </article>
      ))}
    </section>
  )
}
