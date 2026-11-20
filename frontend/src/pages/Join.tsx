import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { graphApi } from '../api'
import { useAuth } from '../auth'
import { SocialAuth } from '../SocialAuth'
import { track } from '../metrics'
import type { EventInfo } from '../types'
import { Banner, Button, Card, Field, Page, Text } from '../ui'

export function Join() {
  const { token } = useParams()
  const { user, ready, loginGoogle } = useAuth()
  const navigate = useNavigate()
  const [event, setEvent] = useState<EventInfo | null>(null)
  const [loadError, setLoadError] = useState('')
  const [error, setError] = useState('')
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
        track('join_link_opened', { slug: data.event.slug }, data.event.id)
        if (data.joined) navigate(`/e/${data.event.slug}/feed`)
      })
      .catch((err) => setLoadError(err.message))
  }, [token, user])

  useEffect(() => {
    if (user) setHeadline(user.headline)
  }, [user])

  if (!ready) return <Page>Loading…</Page>
  if (loadError) return <Page><Banner>{loadError}</Banner></Page>
  if (!event) return <Page>Loading join link…</Page>

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
        headline,
        skill_tags: skills.split(',').map((s) => s.trim()).filter(Boolean),
        can_advise_on: advise.split(',').map((s) => s.trim()).filter(Boolean),
        open_to_collaborate_on: collab.split(',').map((s) => s.trim()).filter(Boolean),
      })
      track('join_event', { slug: result.slug }, result.event.id)
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
    <Page>
      <Text variant="eyebrow">Join event</Text>
      <Text variant="title">{event.name}</Text>
      {!user ? (
        <Card as="div">
          <Text variant="lede">Continue with Google. You get a handle automatically. Email is the fallback.</Text>
          {error && <Banner>{error}</Banner>}
          <SocialAuth
            onGoogle={async (credential) => {
              setError('')
              try {
                const isNew = await loginGoogle(credential)
                track(isNew ? 'register_google' : 'login_google', { method: 'google', source: 'join', is_new: String(isNew) })
              } catch (err) {
                setError(err instanceof Error ? err.message : 'Google sign-in failed')
              }
            }}
          />
          <Button variant="ghost" to={`/login?next=${encodeURIComponent(next)}`}>
            Email instead
          </Button>
        </Card>
      ) : (
        <form className="form" onSubmit={onJoin} style={{ maxWidth: 640 }}>
          <Text variant="lede">You’re /{user.handle}. Chat and feed for this event stay in the room.</Text>
          {error && <Banner>{error}</Banner>}
          <Field label="Headline">
            <input value={headline} onChange={(e) => setHeadline(e.target.value)} />
          </Field>
          <Field label="Resume PDF (optional)">
            <input type="file" accept="application/pdf" onChange={(e) => e.target.files?.[0] && onResume(e.target.files[0])} />
          </Field>
          <Field label="Skills">
            <input value={skills} onChange={(e) => setSkills(e.target.value)} placeholder="comma separated" />
          </Field>
          <Field label="Can advise on">
            <input value={advise} onChange={(e) => setAdvise(e.target.value)} />
          </Field>
          <Field label="Open to collaborate on">
            <input value={collab} onChange={(e) => setCollab(e.target.value)} />
          </Field>
          <label className="consent"><input type="checkbox" checked={showAttendance} onChange={(e) => setShowAttendance(e.target.checked)} /> Show my attendance to other attendees</label>
          <label className="consent"><input type="checkbox" checked={resumeVisible} onChange={(e) => setResumeVisible(e.target.checked)} /> Show my resume to other attendees for THIS event (off unless you opt in)</label>
          <label className="consent"><input type="checkbox" checked={showContact} onChange={(e) => setShowContact(e.target.checked)} /> Show my contact info after a call is accepted</label>
          <label className="consent"><input type="checkbox" checked={accepted} onChange={(e) => setAccepted(e.target.checked)} required /> I agree to join this event (required)</label>
          <Button type="submit" disabled={!accepted}>Enter the room</Button>
        </form>
      )}
    </Page>
  )
}
