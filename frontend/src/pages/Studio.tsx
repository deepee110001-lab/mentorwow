import { useEffect, useState, type FormEvent } from 'react'
import { Navigate } from 'react-router-dom'
import { meApi } from '../api'
import { useAuth } from '../auth'
import type { Project } from '../types'

export function Studio() {
  const { user, ready, setUser } = useAuth()
  const [handle, setHandle] = useState(user?.handle ?? '')
  const [title, setTitle] = useState('')
  const [summary, setSummary] = useState('')
  const [url, setUrl] = useState('')
  const [topics, setTopics] = useState('')
  const [editing, setEditing] = useState<Project | null>(null)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState('')

  useEffect(() => {
    if (user) setHandle(user.handle)
  }, [user])

  if (!ready) return <main className="page">Loading…</main>
  if (!user) return <Navigate to="/login" replace />

  async function saveHandle(event: FormEvent) {
    event.preventDefault()
    setError('')
    try {
      setUser(await meApi.update({ handle }))
      setSaved('Handle saved.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save')
    }
  }

  async function saveProject(event: FormEvent) {
    event.preventDefault()
    setError('')
    const payload = {
      title,
      summary,
      url,
      topics: topics.split(',').map((part) => part.trim()).filter(Boolean),
    }
    try {
      const next = editing ? await meApi.editProject(editing.id, payload) : await meApi.addProject(payload)
      setUser(next)
      setTitle('')
      setSummary('')
      setUrl('')
      setTopics('')
      setEditing(null)
      setSaved('Project saved.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save project')
    }
  }

  function startEdit(project: Project) {
    setEditing(project)
    setTitle(project.title)
    setSummary(project.summary)
    setUrl(project.url)
    setTopics(project.topics.join(', '))
  }

  return (
    <main className="page">
      <p className="eyebrow">Portfolio, not a résumé</p>
      <h1 className="serif" style={{ fontSize: 52, marginTop: 6 }}>How the network sees you</h1>
      <p className="lede">Projects only. No education. No jobs. Email stays off the profile.</p>
      {error && <div className="error">{error}</div>}
      {saved && <div className="success">{saved}</div>}
      <form className="form" onSubmit={saveHandle} style={{ maxWidth: 720, marginTop: 24 }}>
        <label className="field">
          <span>Handle</span>
          <input value={handle} onChange={(event) => setHandle(event.target.value)} required />
        </label>
        <button className="btn ghost" type="submit">Save handle</button>
      </form>
      <div className="split" style={{ marginTop: 32 }}>
        <form className="card form" onSubmit={saveProject}>
          <h3 className="serif" style={{ margin: 0, fontSize: 28 }}>
            {editing ? 'Edit project' : 'Add a project'}
          </h3>
          <label className="field">
            <span>Title</span>
            <input value={title} onChange={(event) => setTitle(event.target.value)} required />
          </label>
          <label className="field">
            <span>What the work did</span>
            <textarea rows={4} value={summary} onChange={(event) => setSummary(event.target.value)} />
          </label>
          <label className="field">
            <span>Link</span>
            <input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://" />
          </label>
          <label className="field">
            <span>Topics, comma separated</span>
            <input value={topics} onChange={(event) => setTopics(event.target.value)} placeholder="system design, privacy" />
          </label>
          <div className="row-actions">
            <button className="btn primary" type="submit">{editing ? 'Update' : 'Add to portfolio'}</button>
            {editing && (
              <button className="btn ghost" type="button" onClick={() => { setEditing(null); setTitle(''); setSummary(''); setUrl(''); setTopics('') }}>
                Cancel
              </button>
            )}
          </div>
        </form>
        <div className="list">
          {user.projects.map((project) => (
            <article className="card" key={project.id}>
              <h3 className="serif" style={{ margin: '0 0 6px', fontSize: 24 }}>{project.title}</h3>
              <p>{project.summary}</p>
              <div className="chips">{project.topics.map((topic) => <span className="chip" key={topic}>{topic}</span>)}</div>
              <div className="row-actions">
                <button className="btn ghost" onClick={() => startEdit(project)}>Edit</button>
                <button className="btn ghost" onClick={() => meApi.deleteProject(project.id).then(setUser)}>Remove</button>
              </div>
            </article>
          ))}
        </div>
      </div>
    </main>
  )
}
