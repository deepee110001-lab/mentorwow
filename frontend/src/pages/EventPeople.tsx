import { useEffect, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { getToken, graphApi } from '../api'
import type { EventInfo, VisiblePerson } from '../types'

export function EventPeople() {
  const { slug, event } = useOutletContext<{ slug: string; event: EventInfo }>()
  const [people, setPeople] = useState<VisiblePerson[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    graphApi.people(slug).then(setPeople).catch((err) => setError(err.message))
  }, [slug])

  async function requestCall(person: VisiblePerson) {
    setError('')
    try {
      await graphApi.createQuery(slug, {
        type: 'skill',
        body: `5-min intro with ${person.name}`,
        available_slots: [{ start: new Date(Date.now() + 3600000).toISOString() }],
        target_user_id: person.user_id,
      })
      alert('Request sent (counts toward your weekly outgoing limit).')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not request')
    }
  }

  return (
    <section style={{ marginTop: 18 }}>
      {error && <div className="error">{error}</div>}
      <div className="grid">
        {people.map((person) => (
          <article className="card" key={person.user_id}>
            <h3 className="serif" style={{ margin: '0 0 4px', fontSize: 26 }}>{person.name}</h3>
            <p className="empty">{person.headline}</p>
            <div className="chips">{person.skill_tags.map((t) => <span className="chip" key={t}>{t}</span>)}</div>
            <div className="chips">{person.open_to_collaborate_on.map((t) => <span className="chip" key={`c-${t}`}>collab: {t}</span>)}</div>
            {person.resume_visible && person.resume_url && (
              <a className="btn ghost" href={person.resume_url} onClick={(e) => {
                e.preventDefault()
                fetch(person.resume_url!, { headers: { Authorization: `Bearer ${getToken()}` } }).then((r) => r.blob()).then((b) => {
                  const url = URL.createObjectURL(b)
                  window.open(url)
                })
              }}>Resume</a>
            )}
            {person.email && <p>Contact: {person.email}</p>}
            {!person.is_self && event.feed_open && (
              <button className="btn primary" onClick={() => requestCall(person)}>Request 5-min call</button>
            )}
          </article>
        ))}
      </div>
    </section>
  )
}
