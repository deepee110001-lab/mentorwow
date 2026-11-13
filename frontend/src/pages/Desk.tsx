import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { requestApi, sessionApi } from '../api'
import { useAuth } from '../auth'
import { Avatar } from '../components/Avatar'
import { formatWhen } from '../lib'
import type { MentorshipRequest, MentorshipSession } from '../types'

export function Desk() {
  const { user, ready } = useAuth()
  const [requests, setRequests] = useState<MentorshipRequest[]>([])
  const [sessions, setSessions] = useState<MentorshipSession[]>([])
  const [error, setError] = useState('')
  const [title, setTitle] = useState('Working session')
  const [when, setWhen] = useState('')
  const [peerId, setPeerId] = useState<number | ''>('')
  const [noteDrafts, setNoteDrafts] = useState<Record<number, string>>({})

  async function load() {
    const [nextRequests, nextSessions] = await Promise.all([requestApi.list(), sessionApi.list()])
    setRequests(nextRequests)
    setSessions(nextSessions)
    setNoteDrafts(Object.fromEntries(nextSessions.map((item) => [item.id, item.notes])))
  }

  useEffect(() => {
    if (user) load().catch((err) => setError(err.message))
  }, [user])

  const matches = useMemo(() => {
    if (!user) return []
    return requests
      .filter((item) => item.status === 'accepted')
      .map((item) => (item.mentor.id === user.id ? item.mentee : item.mentor))
  }, [requests, user])

  useEffect(() => {
    if (matches.length && peerId === '') setPeerId(matches[0].id)
  }, [matches, peerId])

  if (!ready) return <main className="page">Loading desk…</main>
  if (!user) return <Navigate to="/login" replace />

  const incoming = requests.filter((item) => item.mentor.id === user.id)
  const outgoing = requests.filter((item) => item.mentee.id === user.id)
  const upcoming = sessions.filter((item) => item.status === 'scheduled')
  const past = sessions.filter((item) => item.status !== 'scheduled')

  async function changeRequest(id: number, status: MentorshipRequest['status']) {
    setError('')
    try {
      await requestApi.update(id, status)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update request')
    }
  }

  async function book(event: FormEvent) {
    event.preventDefault()
    if (peerId === '' || !when) return
    setError('')
    try {
      await sessionApi.create({
        peer_id: Number(peerId),
        title,
        scheduled_at: new Date(when).toISOString(),
        duration_minutes: 45,
      })
      setTitle('Working session')
      setWhen('')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not book')
    }
  }

  async function saveNotes(id: number) {
    await sessionApi.update(id, { notes: noteDrafts[id] ?? '' })
    await load()
  }

  return (
    <main className="page">
      <p className="eyebrow">The desk</p>
      <h1 className="serif" style={{ fontSize: 52, marginTop: 6 }}>
        Hello, {user.name.split(' ')[0]}
      </h1>
      <p className="lede">Requests on the left. Time on the right. Keep it small enough to be honest.</p>
      {error && <div className="error" style={{ marginTop: 16 }}>{error}</div>}

      <section className="split" style={{ marginTop: 28 }}>
        <div className="list">
          <h2>Asks</h2>
          {(user.role === 'mentor' ? incoming : outgoing).map((item) => {
            const other = item.mentor.id === user.id ? item.mentee : item.mentor
            return (
              <article className="card" key={item.id}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                  <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                    <Avatar name={other.name} accent={other.accent} />
                    <div>
                      <strong>{other.name}</strong>
                      <div className="empty">{other.headline}</div>
                    </div>
                  </div>
                  <span className={`status ${item.status}`}>{item.status}</span>
                </div>
                <p style={{ marginBottom: 0 }}><b>{item.goal}</b></p>
                <p>{item.message}</p>
                <div className="row-actions">
                  {user.role === 'mentor' && item.status === 'pending' && (
                    <>
                      <button className="btn sage" onClick={() => changeRequest(item.id, 'accepted')}>Accept</button>
                      <button className="btn ghost" onClick={() => changeRequest(item.id, 'declined')}>Decline</button>
                    </>
                  )}
                  {user.role === 'mentee' && item.status === 'pending' && (
                    <button className="btn ghost" onClick={() => changeRequest(item.id, 'withdrawn')}>Withdraw</button>
                  )}
                </div>
              </article>
            )
          })}
          {(user.role === 'mentor' ? incoming : outgoing).length === 0 && (
            <p className="empty">
              No asks yet. {user.role === 'mentee' ? <Link to="/discover">Find someone in the atelier.</Link> : 'When a mentee writes you, it lands here.'}
            </p>
          )}
        </div>

        <div className="list">
          <h2>Sessions</h2>
          {matches.length > 0 && (
            <form className="card form" onSubmit={book}>
              <h3 className="serif" style={{ margin: 0, fontSize: 26 }}>Book an hour</h3>
              <label className="field">
                <span>With</span>
                <select value={peerId} onChange={(event) => setPeerId(Number(event.target.value))}>
                  {matches.map((person) => (
                    <option key={person.id} value={person.id}>
                      {person.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Title</span>
                <input value={title} onChange={(event) => setTitle(event.target.value)} required />
              </label>
              <label className="field">
                <span>When</span>
                <input type="datetime-local" value={when} onChange={(event) => setWhen(event.target.value)} required />
              </label>
              <button className="btn primary" type="submit">Put it on the desk</button>
            </form>
          )}

          {upcoming.map((item) => {
            const other = item.mentor.id === user.id ? item.mentee : item.mentor
            return (
              <article className="card" key={item.id}>
                <span className={`status ${item.status}`}>{item.status}</span>
                <h3 className="serif" style={{ margin: '8px 0 4px', fontSize: 26 }}>{item.title}</h3>
                <p>{formatWhen(item.scheduled_at)} · {item.duration_minutes} min · with {other.name}</p>
                <div className="row-actions">
                  <button className="btn sage" onClick={() => sessionApi.update(item.id, { status: 'completed' }).then(load)}>Mark done</button>
                  <button className="btn ghost" onClick={() => sessionApi.update(item.id, { status: 'cancelled' }).then(load)}>Cancel</button>
                </div>
              </article>
            )
          })}

          {past.map((item) => {
            const other = item.mentor.id === user.id ? item.mentee : item.mentor
            return (
              <article className="card" key={item.id}>
                <span className={`status ${item.status}`}>{item.status}</span>
                <h3 className="serif" style={{ margin: '8px 0 4px', fontSize: 24 }}>{item.title}</h3>
                <p>{formatWhen(item.scheduled_at)} · with {other.name}</p>
                <label className="field">
                  <span>Notes</span>
                  <textarea
                    rows={3}
                    value={noteDrafts[item.id] ?? ''}
                    onChange={(event) => setNoteDrafts((current) => ({ ...current, [item.id]: event.target.value }))}
                  />
                </label>
                <button className="btn ghost" onClick={() => saveNotes(item.id)}>Save notes</button>
              </article>
            )
          })}
        </div>
      </section>
    </main>
  )
}
