import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { peopleApi } from '../api'
import { useAuth } from '../auth'
import { Avatar } from '../components/Avatar'
import type { PublicProfile } from '../types'

export function Profile() {
  const { handle } = useParams()
  const { user } = useAuth()
  const [profile, setProfile] = useState<PublicProfile | null>(null)
  const [error, setError] = useState('')
  const mine = user?.handle === handle

  useEffect(() => {
    if (!handle) return
    peopleApi.get(handle).then(setProfile).catch((err) => setError(err.message))
  }, [handle])

  async function toggleFollow() {
    if (!handle) return
    const result = await peopleApi.follow(handle)
    setProfile((current) => (current ? { ...current, following: result.following } : current))
  }

  if (!profile) return <main className="page">{error || 'Loading handle…'}</main>

  return (
    <main className="page">
      <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
        <Avatar handle={profile.handle} accent={profile.accent} size={64} />
        <div>
          <p className="eyebrow">anonymous handle</p>
          <h1 className="serif" style={{ fontSize: 52, margin: 0 }}>/{profile.handle}</h1>
        </div>
      </div>
      <p className="lede">Portfolio only. No jobs. No schools. Minutes and GURU stay private.</p>
      <div className="chips">
        {profile.topics.map((topic) => (
          <span className="chip" key={topic}>{topic}</span>
        ))}
      </div>
      <div className="row-actions">
        {mine ? (
          <Link className="btn primary" to="/studio">Edit portfolio</Link>
        ) : user ? (
          <button className="btn primary" onClick={toggleFollow}>
            {profile.following ? 'Unfollow' : 'Follow'}
          </button>
        ) : null}
      </div>
      <div className="list" style={{ marginTop: 28 }}>
        {profile.projects.map((project) => (
          <article className="card" key={project.id}>
            <p className="eyebrow">{project.topics.join(' · ')}</p>
            <h3 className="serif" style={{ margin: '6px 0', fontSize: 30 }}>{project.title}</h3>
            <p>{project.summary}</p>
            {project.url && (
              <a href={project.url} target="_blank" rel="noreferrer">
                {project.url}
              </a>
            )}
          </article>
        ))}
        {profile.projects.length === 0 && <p className="empty">No projects on this handle yet.</p>}
      </div>
    </main>
  )
}
