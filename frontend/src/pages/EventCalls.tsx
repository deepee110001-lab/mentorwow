import { useEffect, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { graphApi } from '../api'
import type { EventCallRow } from '../types'

export function EventCalls() {
  const { slug } = useOutletContext<{ slug: string }>()
  const [calls, setCalls] = useState<EventCallRow[]>([])

  async function load() {
    setCalls(await graphApi.calls(slug))
  }

  useEffect(() => {
    load()
  }, [slug])

  return (
    <section className="list" style={{ marginTop: 18 }}>
      {calls.map((call) => (
        <article className="card" key={call.id}>
          <span className={`status ${call.status}`}>{call.status}</span>
          <h3 className="serif" style={{ margin: '8px 0 4px', fontSize: 26 }}>{call.other.name}</h3>
          <p>{call.other.headline}</p>
          {call.other.email ? <p>Contact: {call.other.email}</p> : <p className="empty">Contact hidden until the call is accepted.</p>}
          {call.meeting_url && (
            <a className="btn primary" href={call.meeting_url} target="_blank" rel="noreferrer">
              Join Jitsi (5 min)
            </a>
          )}
          {call.status === 'scheduled' && (
            <form
              className="form"
              style={{ marginTop: 12 }}
              onSubmit={(e) => {
                e.preventDefault()
                const data = new FormData(e.currentTarget)
                graphApi.completeCall(call.id, { usefulness: Number(data.get('usefulness')), takeaway: String(data.get('takeaway') || '') }).then(load)
              }}
            >
              <label className="field">
                <span>Usefulness 1–5</span>
                <input name="usefulness" type="number" min={1} max={5} defaultValue={4} />
              </label>
              <label className="field">
                <span>One-line takeaway</span>
                <input name="takeaway" />
              </label>
              <button className="btn sage" type="submit">Mark complete</button>
            </form>
          )}
        </article>
      ))}
      {calls.length === 0 && <p className="empty">No calls yet. Accept a matched query on the Feed.</p>}
    </section>
  )
}
