import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { mentorApi } from '../api'
import { MentorCard } from '../components/MentorCard'
import type { Mentor } from '../types'

export function Home() {
  const [mentors, setMentors] = useState<Mentor[]>([])

  useEffect(() => {
    mentorApi.list().then((all) => setMentors(all.slice(0, 4)))
  }, [])

  return (
    <main className="page">
      <section className="hero">
        <div>
          <p className="eyebrow">Mentorship without the marketplace noise</p>
          <h1>Find the person who already walked it.</h1>
          <p className="lede">
            MentorWow pairs you with practitioners who have done the work you are about to start —
            product, engineering, research, craft, and the career turns that never look clean on a résumé.
          </p>
          <div className="hero-actions">
            <Link className="btn primary" to="/discover">
              Browse the atelier
            </Link>
            <Link className="btn ghost" to="/register">
              Offer to mentor
            </Link>
          </div>
        </div>
        <aside className="hero-panel">
          <p className="eyebrow" style={{ color: '#e8b39f' }}>
            From a recent session
          </p>
          <p className="quote">“Your roadmap had eight bets and no killing criteria. Rewrite it as three.”</p>
          <div>
            <p>Amara Okonkwo · Product lead</p>
            <p className="quiet">with Riley Shah, after a 50-minute teardown</p>
          </div>
        </aside>
      </section>

      <section className="stats">
        <div className="stat">
          <b>8</b>
          <span>mentors in the opening studio</span>
        </div>
        <div className="stat">
          <b>45 min</b>
          <span>the default session, long enough to be honest</span>
        </div>
        <div className="stat">
          <b>1 ask</b>
          <span>send a goal, not a cold LinkedIn paragraph</span>
        </div>
      </section>

      <section>
        <div className="section-head">
          <div>
            <p className="eyebrow">In the room</p>
            <h2>A few people worth sitting with</h2>
          </div>
          <Link to="/discover">See everyone →</Link>
        </div>
        <div className="grid">
          {mentors.map((mentor) => (
            <MentorCard key={mentor.id} mentor={mentor} />
          ))}
        </div>
      </section>

      <section>
        <div className="section-head">
          <div>
            <p className="eyebrow">How it works</p>
            <h2>Three moves, then a calendar</h2>
          </div>
        </div>
        <div className="steps">
          <article className="card">
            <div className="step-num">01</div>
            <h3>Choose a craft</h3>
            <p>Filter by the work you actually need help with — staff engineering, founder sales, the IC-to-manager hinge.</p>
          </article>
          <article className="card">
            <div className="step-num">02</div>
            <h3>Send a real ask</h3>
            <p>Name the goal and why this person. Mentors accept, decline, or wait. No spraying requests into the void.</p>
          </article>
          <article className="card">
            <div className="step-num">03</div>
            <h3>Book the hour</h3>
            <p>Once you are matched, schedule a session from the desk. Notes live with the session so the next one starts warmer.</p>
          </article>
        </div>
      </section>
    </main>
  )
}
