import { useEffect, useMemo, useState } from 'react'
import { mentorApi } from '../api'
import { MentorCard } from '../components/MentorCard'
import type { Mentor, Skill } from '../types'

export function Discover() {
  const [mentors, setMentors] = useState<Mentor[]>([])
  const [skills, setSkills] = useState<Skill[]>([])
  const [q, setQ] = useState('')
  const [skill, setSkill] = useState('')
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    mentorApi.skills().then(setSkills)
  }, [])

  useEffect(() => {
    const handle = setTimeout(() => {
      mentorApi.list({ q: q || undefined, skill: skill || undefined }).then((items) => {
        setMentors(items)
        setLoaded(true)
      })
    }, 120)
    return () => clearTimeout(handle)
  }, [q, skill])

  const uniqueSkills = useMemo(
    () => [...new Set(skills.map((item) => item.name))],
    [skills],
  )

  return (
    <main className="page">
      <p className="eyebrow">The atelier</p>
      <h1 className="serif" style={{ fontSize: 56, marginTop: 8 }}>
        Mentors, by the work they still do
      </h1>
      <p className="lede">Search a craft, a city, or a name. Open a studio page. Ask with a goal, not a compliment.</p>

      <div className="filters" style={{ marginTop: 28 }}>
        <input
          value={q}
          onChange={(event) => setQ(event.target.value)}
          placeholder="Search people, crafts, cities"
        />
        <button className={`pill ${skill === '' ? 'on' : ''}`} onClick={() => setSkill('')}>
          All crafts
        </button>
        {uniqueSkills.map((name) => (
          <button key={name} className={`pill ${skill === name ? 'on' : ''}`} onClick={() => setSkill(name)}>
            {name}
          </button>
        ))}
      </div>

      <div className="grid">
        {mentors.map((mentor) => (
          <MentorCard key={mentor.id} mentor={mentor} />
        ))}
      </div>
      {loaded && mentors.length === 0 && <p className="empty">No mentors match that filter yet.</p>}
    </main>
  )
}
