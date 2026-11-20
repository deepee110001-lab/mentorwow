import { Button, Page, Text } from '../ui'

export function Home() {
  return (
    <Page>
      <section className="hero">
        <div>
          <Text variant="eyebrow">Event-anchored networking</Text>
          <Text variant="display">Meet the room. Then keep the useful threads.</Text>
          <Text variant="lede">
            Organizers share a join link. Attendees bring a portable profile — LinkedIn subset or a resume they
            opted into. Chat lives 24 hours. The query feed lives 7 days. Calls are five minutes, never recorded.
          </Text>
          <div className="hero-actions">
            <Button to="/join/mentorwow-join">Join the MentorWow pilot</Button>
            <Button variant="ghost" to="/organizer">
              Create an event
            </Button>
          </div>
        </div>
        <aside className="hero-panel">
          <Text variant="eyebrow">What closes</Text>
          <Text variant="quote">Chat after a day. The feed after a week. Your profile walks with you.</Text>
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
    </Page>
  )
}
