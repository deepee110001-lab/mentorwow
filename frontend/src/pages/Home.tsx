import { Link } from 'react-router-dom'

export function Home() {
  return (
    <main className="page">
      <section className="hero">
        <div>
          <p className="eyebrow">Event-anchored networking</p>
          <h1>Meet the room. Then keep the useful threads.</h1>
          <p className="lede">
            Organizers share a join link. Attendees bring a portable profile — LinkedIn subset or a resume they
            opted into. Chat lives 24 hours. The query feed lives 7 days. Calls are five minutes, never recorded.
          </p>
          <div className="hero-actions">
            <Link className="btn primary" to="/join/cedat-join-demo">
              Join the CEDAT pilot
            </Link>
            <Link className="btn ghost" to="/organizer">
              Create an event
            </Link>
          </div>
        </div>
        <aside className="hero-panel">
          <p className="eyebrow" style={{ color: '#e8b39f' }}>
            What closes
          </p>
          <p className="quote">Chat after a day. The feed after a week. Your profile walks with you.</p>
          <p className="quiet">AI routes queries. AI does not listen to calls.</p>
        </aside>
      </section>
      <section className="stats">
        <div className="stat">
          <b>24h</b>
          <span>public takeaways chat, then archive</span>
        </div>
        <div className="stat">
          <b>7d</b>
          <span>skill + collab queries, matched to 3–5 people</span>
        </div>
        <div className="stat">
          <b>5:00</b>
          <span>request-based calls, rate-limited</span>
        </div>
      </section>
    </main>
  )
}
