import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { graphApi } from '../api'
import { useAuth } from '../auth'
import type { EventInfo } from '../types'

export function Join() {
  const { token } = useParams()
  const { user, ready } = useAuth()
  const navigate = useNavigate()
  const [event, setEvent] = useState<EventInfo | null>(null)
  const [error, setError] = useState('')
  const [name, setName] = useState(user?.name || '')
  const [headline, setHeadline] = useState(user?.headline || '')
  const [skills, setSkills] = useState('')
  const [advise, setAdvise] = useState('')
  const [collab, setCollab] = useState('')
  const [showAttendance, setShowAttendance] = useState(true)
  const [resumeVisible, setResumeVisible] = useState(false)
  const [showContact, setShowContact] = useState(true)
  const [accepted, setAccepted] = useState(false)

  useEffect(() => {
    if (!token) return
    graphApi
      .resolveJoin(token)
      .then((data) => {
        setEvent(data.event)
        if (data.joined) navigate(`/e/${data.event.slug}/feed`)
      })
      .catch((err) => setError(err.message))
  }, [token, user])

  useEffect(() => {
    if (user) {
      setName(user.name)
      setHeadline(user.headline)
    }
  }, [user])

  if (!ready) return <main className="page">Loading…</main>
  if (error) return <main className="page"><div className="error">{error}</div></main>
  if (!event) return <main className="page">Loading join link…</main>

  const next = `/join/${token}`

  async function onJoin(ev: FormEvent) {
    ev.preventDefault()
    if (!token) return
    try {
      const result = await graphApi.join(token, {
        accepted_join: accepted,
        show_attendance: showAttendance,
        resume_visible_this_event: resumeVisible,
        show_contact_after_call: showContact,
        name,
        headline,
        skill_tags: skills.split(',').map((s) => s.trim()).filter(Boolean),
        can_advise_on: advise.split(',').map((s) => s.trim()).filter(Boolean),
        open_to_collaborate_on: collab.split(',').map((s) => s.trim()).filter(Boolean),
      })
      navigate(`/e/${result.slug}/feed`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not join')
    }
  }

  async function onResume(file: File) {
    const tags = await graphApi.uploadResume(file)
    setSkills(tags.skill_tags.join(', '))
    setAdvise(tags.can_advise_on.join(', '))
    setCollab(tags.open_to_collaborate_on.join(', '))
  }

  return (
    <main className="page">
      <p className="eyebrow">Join event</p>
      <h1 className="serif" style={{ fontSize: 44 }}>{event.name}</h1>
      {!user ? (
        <div className="card">
          <p>Sign in with email or LinkedIn to join. We only store name, headline, photo, and email from LinkedIn.</p>
          <div className="row-actions">
            <Link className="btn primary" to={`/login?next=${encodeURIComponent(next)}`}>Sign in</Link>
            <Link className="btn ghost" to={`/register?next=${encodeURIComponent(next)}`}>Create account</Link>
          </div>
        </div>
      ) : (
        <form className="form" onSubmit={onJoin} style={{ maxWidth: 640 }}>
          <p className="lede">Your profile is portable. Chat and feed for this event are not.</p>
          <label className="field"><span>Name</span><input value={name} onChange={(e) => setName(e.target.value)} required /></label>
          <label className="field"><span>Headline</span><input value={headline} onChange={(e) => setHeadline(e.target.value)} /></label>
          <label className="field">
            <span>Resume PDF (optional — parsed for tags, never scraped from LinkedIn)</span>
            <input type="file" accept="application/pdf" onChange={(e) => e.target.files?.[0] && onResume(e.target.files[0])} />
          </label>
          <label className="field"><span>Skills</span><input value={skills} onChange={(e) => setSkills(e.target.value)} placeholder="comma separated, edit after parse" /></label>
          <label className="field"><span>Can advise on</span><input value={advise} onChange={(e) => setAdvise(e.target.value)} /></label>
          <label className="field"><span>Open to collaborate on</span><input value={collab} onChange={(e) => setCollab(e.target.value)} /></label>
          <label className="consent"><input type="checkbox" checked={showAttendance} onChange={(e) => setShowAttendance(e.target.checked)} /> Show my attendance to other attendees</label>
          <label className="consent"><input type="checkbox" checked={resumeVisible} onChange={(e) => setResumeVisible(e.target.checked)} /> Show my resume to other attendees for THIS event (off unless you opt in)</label>
          <label className="consent"><input type="checkbox" checked={showContact} onChange={(e) => setShowContact(e.target.checked)} /> Show my contact info after a call is accepted</label>
          <label className="consent"><input type="checkbox" checked={accepted} onChange={(e) => setAccepted(e.target.checked)} required /> I agree to join this event (required)</label>
          <button className="btn primary" type="submit" disabled={!accepted}>Enter the room</button>
        </form>
      )}
    </main>
  )
}
