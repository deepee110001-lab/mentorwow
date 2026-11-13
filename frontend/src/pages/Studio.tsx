import { useEffect, useState, type FormEvent } from 'react'
import { Navigate } from 'react-router-dom'
import { mentorApi, profileApi } from '../api'
import { useAuth } from '../auth'
import type { Skill } from '../types'

export function Studio() {
  const { user, ready, refresh } = useAuth()
  const [catalog, setCatalog] = useState<Skill[]>([])
  const [name, setName] = useState('')
  const [headline, setHeadline] = useState('')
  const [bio, setBio] = useState('')
  const [location, setLocation] = useState('')
  const [availability, setAvailability] = useState('')
  const [years, setYears] = useState(0)
  const [skills, setSkills] = useState<string[]>([])
  const [customSkill, setCustomSkill] = useState('')
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    mentorApi.skills().then(setCatalog)
  }, [])

  useEffect(() => {
    if (!user) return
    setName(user.name)
    setHeadline(user.headline)
    setBio(user.bio)
    setLocation(user.location)
    setAvailability(user.availability)
    setYears(user.years_experience)
    setSkills(user.skills)
  }, [user])

  if (!ready) return <main className="page">Loading…</main>
  if (!user) return <Navigate to="/login" replace />

  function toggleSkill(skill: string) {
    setSkills((current) => (current.includes(skill) ? current.filter((item) => item !== skill) : [...current, skill]))
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError('')
    setSaved(false)
    try {
      await profileApi.update({
        name,
        headline,
        bio,
        location,
        availability,
        years_experience: years,
        skills,
      })
      await refresh()
      setSaved(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save')
    }
  }

  return (
    <main className="page">
      <p className="eyebrow">{user.role === 'mentor' ? 'Mentor studio' : 'Mentee studio'}</p>
      <h1 className="serif" style={{ fontSize: 52, marginTop: 6 }}>
        How you show up
      </h1>
      <form className="form" onSubmit={onSubmit} style={{ maxWidth: 720, marginTop: 24 }}>
        {error && <div className="error">{error}</div>}
        {saved && <div className="success">Saved. {user.role === 'mentor' ? 'You are visible in the atelier.' : 'Mentors will see this with your ask.'}</div>}
        <label className="field">
          <span>Name</span>
          <input value={name} onChange={(event) => setName(event.target.value)} required />
        </label>
        <label className="field">
          <span>Headline</span>
          <input value={headline} onChange={(event) => setHeadline(event.target.value)} placeholder="One line of the work you do" />
        </label>
        <label className="field">
          <span>Bio</span>
          <textarea rows={5} value={bio} onChange={(event) => setBio(event.target.value)} />
        </label>
        <div className="grid">
          <label className="field">
            <span>Location</span>
            <input value={location} onChange={(event) => setLocation(event.target.value)} />
          </label>
          <label className="field">
            <span>Availability</span>
            <input value={availability} onChange={(event) => setAvailability(event.target.value)} />
          </label>
        </div>
        <label className="field">
          <span>Years in the work</span>
          <input type="number" min={0} value={years} onChange={(event) => setYears(Number(event.target.value))} />
        </label>
        <div>
          <p className="field">
            <span>{user.role === 'mentor' ? 'Crafts you teach' : 'Crafts you want'}</span>
          </p>
          <div className="filters">
            {catalog.map((item) => (
              <button type="button" key={item.name} className={`pill ${skills.includes(item.name) ? 'on' : ''}`} onClick={() => toggleSkill(item.name)}>
                {item.name}
              </button>
            ))}
          </div>
          <div className="filters">
            <input value={customSkill} onChange={(event) => setCustomSkill(event.target.value)} placeholder="Add a craft" />
            <button
              type="button"
              className="btn ghost"
              onClick={() => {
                const value = customSkill.trim()
                if (value) {
                  toggleSkill(value)
                  setCustomSkill('')
                }
              }}
            >
              Add
            </button>
          </div>
        </div>
        <button className="btn primary" type="submit">
          Save studio
        </button>
      </form>
    </main>
  )
}
