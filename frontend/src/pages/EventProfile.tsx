import { useEffect, useState, type FormEvent } from 'react'
import { useOutletContext } from 'react-router-dom'
import { graphApi } from '../api'
import { useAuth } from '../auth'

export function EventProfile() {
  const { slug } = useOutletContext<{ slug: string }>()
  const { user, setUser, refresh } = useAuth()
  const [handle, setHandle] = useState(user?.handle || '')
  const [headline, setHeadline] = useState('')
  const [skills, setSkills] = useState('')
  const [advise, setAdvise] = useState('')
  const [collab, setCollab] = useState('')
  const [resumeVis, setResumeVis] = useState(false)
  const [saved, setSaved] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    graphApi.profile().then((p) => {
      setHandle(String(p.handle || user?.handle || ''))
      setHeadline(String(p.headline || ''))
      setSkills((p.skill_tags as string[]).join(', '))
      setAdvise((p.can_advise_on as string[]).join(', '))
      setCollab((p.open_to_collaborate_on as string[]).join(', '))
    })
    graphApi.event(slug).then((data) => {
      const member = data.member as { resume_visible_this_event?: boolean }
      setResumeVis(Boolean(member.resume_visible_this_event))
    })
  }, [slug, user?.handle])

  async function save(ev: FormEvent) {
    ev.preventDefault()
    setError('')
    setSaved('')
    try {
      await graphApi.saveProfile({
        handle,
        headline,
        skill_tags: skills.split(',').map((s) => s.trim()).filter(Boolean),
        can_advise_on: advise.split(',').map((s) => s.trim()).filter(Boolean),
        open_to_collaborate_on: collab.split(',').map((s) => s.trim()).filter(Boolean),
      })
      await graphApi.consent({ slug, resume_visible_this_event: resumeVis })
      await refresh()
      if (user) setUser({ ...user, handle: handle.trim().toLowerCase() })
      setSaved('Saved. Handle is the only name people see.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save')
    }
  }

  return (
    <form className="form" style={{ marginTop: 18, maxWidth: 640 }} onSubmit={save}>
      <p className="lede">One handle, assigned automatically. You can change it. No legal name.</p>
      {saved && <div className="success">{saved}</div>}
      {error && <div className="error">{error}</div>}
      <label className="field">
        <span>Handle</span>
        <input
          value={handle}
          onChange={(e) => setHandle(e.target.value.toLowerCase())}
          required
          minLength={3}
          maxLength={24}
          pattern="[a-z][a-z0-9-]{2,23}"
        />
      </label>
      <label className="field"><span>Headline</span><input value={headline} onChange={(e) => setHeadline(e.target.value)} /></label>
      <label className="field"><span>Skills</span><input value={skills} onChange={(e) => setSkills(e.target.value)} /></label>
      <label className="field"><span>Can advise on</span><input value={advise} onChange={(e) => setAdvise(e.target.value)} /></label>
      <label className="field"><span>Open to collaborate on</span><input value={collab} onChange={(e) => setCollab(e.target.value)} /></label>
      <label className="consent">
        <input type="checkbox" checked={resumeVis} onChange={(e) => setResumeVis(e.target.checked)} />
        Show my resume to attendees of this event
      </label>
      <label className="field">
        <span>Replace resume PDF</span>
        <input type="file" accept="application/pdf" onChange={(e) => e.target.files?.[0] && graphApi.uploadResume(e.target.files[0])} />
      </label>
      <button className="btn primary" type="submit">Save profile</button>
    </form>
  )
}
