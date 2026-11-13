import { Link } from 'react-router-dom'
import type { Mentor } from '../types'

export function MentorCard({ mentor }: { mentor: Mentor }) {
  return (
    <Link to={`/mentors/${mentor.id}`} className="card mentor-card">
      <span style={{ background: mentor.accent }} />
      <div>
        <p className="eyebrow">{mentor.location}</p>
        <h3>{mentor.name}</h3>
        <p>{mentor.headline}</p>
        <div className="chips">
          {mentor.skills.map((skill) => (
            <span className="chip" key={skill}>
              {skill}
            </span>
          ))}
        </div>
        <div className="meta">
          <span>{mentor.years_experience} yrs in the work</span>
          <span>{mentor.availability}</span>
          <span>{mentor.mentee_count} active {mentor.mentee_count === 1 ? 'mentee' : 'mentees'}</span>
        </div>
      </div>
    </Link>
  )
}
