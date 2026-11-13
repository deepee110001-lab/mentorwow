import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { mentorApi, requestApi } from '../api'
import { useAuth } from '../auth'
import { Avatar } from '../components/Avatar'
import type { Mentor } from '../types'

export function MentorDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [mentor, setMentor] = useState<Mentor | null>(null)
  const [goal, setGoal] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)

  useEffect(() => {
    if (!id) return
    mentorApi.get(Number(id)).then(setMentor)
  }, [id])

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError('')
    if (!user) {
      navigate('/login')
      return
    }
    if (!mentor) return
    try {
      await requestApi.create({ mentor_id: mentor.id, goal, message })
      setDone(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not send request')
    }
  }

  if (!mentor) return <main className="page">Loading studio…</main>

  return (
    <main className="page">
      <Link to="/discover">← Atelier</Link>
      <section className="profile-hero" style={{ marginTop: 18 }}>
        <div>
          <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
            <Avatar name={mentor.name} accent={mentor.accent} size={64} />
            <div>
              <p className="eyebrow">{mentor.location}</p>
              <h1>{mentor.name}</h1>
            </div>
          </div>
          <p className="lede">{mentor.headline}</p>
          <p style={{ maxWidth: '62ch', fontSize: 17, color: 'var(--ink-soft)' }}>{mentor.bio}</p>
          <div className="chips">
            {mentor.skills.map((skill) => (
              <span className="chip" key={skill}>
                {skill}
              </span>
            ))}
          </div>
          <div className="meta">
            <span>{mentor.years_experience} years</span>
            <span>{mentor.availability}</span>
            <span>{mentor.mentee_count} accepted mentees</span>
          </div>
        </div>
        <aside className="card">
          {user?.role === 'mentor' ? (
            <p>You are browsing as a mentor. Switch to a mentee account to send an ask.</p>
          ) : done ? (
            <div>
              <p className="success">Ask sent. You will see it on The desk.</p>
              <Link className="btn" to="/desk" style={{ marginTop: 14 }}>
                Open the desk
              </Link>
            </div>
          ) : (
            <form className="form" onSubmit={onSubmit}>
              <h3 className="serif" style={{ margin: 0, fontSize: 28 }}>
                Ask to sit with {mentor.name.split(' ')[0]}
              </h3>
              {error && <div className="error">{error}</div>}
              <label className="field">
                <span>The goal</span>
                <input value={goal} onChange={(event) => setGoal(event.target.value)} required minLength={4} placeholder="Staff promo packet, founder sales, first 1:1s…" />
              </label>
              <label className="field">
                <span>Why this person</span>
                <textarea
                  rows={5}
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  required
                  minLength={10}
                  placeholder="Be specific. What have you already tried?"
                />
              </label>
              <button className="btn primary" type="submit">
                Send the ask
              </button>
            </form>
          )}
        </aside>
      </section>
    </main>
  )
}
