import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { feedApi } from '../api'
import { useAuth } from '../auth'
import { Avatar } from '../components/Avatar'
import { formatWhen } from '../lib'
import type { Post } from '../types'

export function Feed() {
  const { user } = useAuth()
  const [posts, setPosts] = useState<Post[]>([])
  const [topics, setTopics] = useState<string[]>([])
  const [topic, setTopic] = useState('')
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [postTopic, setPostTopic] = useState('product strategy')
  const [error, setError] = useState('')

  async function load(next = topic) {
    const [feed, catalog] = await Promise.all([feedApi.list(next || undefined), feedApi.topics()])
    setPosts(feed)
    setTopics(catalog)
  }

  useEffect(() => {
    load().catch((err) => setError(err.message))
  }, [])

  async function publish(event: FormEvent) {
    event.preventDefault()
    setError('')
    try {
      await feedApi.create({ title, body, topic: postTopic })
      setTitle('')
      setBody('')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not post')
    }
  }

  async function pickTopic(name: string) {
    setTopic(name)
    const feed = await feedApi.list(name || undefined)
    setPosts(feed)
  }

  return (
    <main className="page feed-layout">
      <aside className="list">
        <p className="eyebrow">Topics</p>
        <button className={`pill ${topic === '' ? 'on' : ''}`} onClick={() => pickTopic('')}>
          Network
        </button>
        {topics.map((name) => (
          <button key={name} className={`pill ${topic === name ? 'on' : ''}`} onClick={() => pickTopic(name)}>
            {name}
          </button>
        ))}
      </aside>
      <section className="list">
        <p className="eyebrow">{topic || 'Network feed'}</p>
        <h1 className="serif" style={{ fontSize: 44, margin: '6px 0 18px' }}>
          Chairs, not people
        </h1>
        {error && <div className="error">{error}</div>}
        {user && (
          <form className="card form" onSubmit={publish}>
            <h3 className="serif" style={{ margin: 0, fontSize: 26 }}>
              Post to the network
            </h3>
            <label className="field">
              <span>Title</span>
              <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Optional" />
            </label>
            <label className="field">
              <span>Body</span>
              <textarea rows={4} value={body} onChange={(event) => setBody(event.target.value)} required />
            </label>
            <label className="field">
              <span>Topic</span>
              <input value={postTopic} onChange={(event) => setPostTopic(event.target.value)} required />
            </label>
            <button className="btn primary" type="submit">
              Publish
            </button>
          </form>
        )}
        {posts.map((post) => (
          <article className="card post-card" key={post.id}>
            <div className="post-meta">
              <Avatar handle={post.handle} accent={post.accent} size={36} />
              <Link to={`/u/${post.handle}`}>/{post.handle}</Link>
              <span className="chip">{post.topic}</span>
              <span className="empty">{formatWhen(post.created_at)}</span>
              {post.kind === 'update' && <span className="status completed">update</span>}
            </div>
            {post.title && <h3 className="serif" style={{ margin: '8px 0 4px', fontSize: 28 }}>{post.title}</h3>}
            <p>{post.body}</p>
            <button className={`pill ${post.my_vote ? 'on' : ''}`} onClick={() => feedApi.vote(post.id).then((item) => setPosts((current) => current.map((row) => (row.id === item.id ? item : row))))}>
              ▲ {post.score}
            </button>
          </article>
        ))}
      </section>
    </main>
  )
}
