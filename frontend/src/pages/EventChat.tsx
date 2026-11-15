import { useEffect, useState, type FormEvent } from 'react'
import { useOutletContext } from 'react-router-dom'
import { graphApi } from '../api'
import { useAuth } from '../auth'
import type { ChatMsg, EventInfo } from '../types'

export function EventChat() {
  const { slug, event } = useOutletContext<{ slug: string; event: EventInfo }>()
  const { user } = useAuth()
  const [messages, setMessages] = useState<ChatMsg[]>([])
  const [open, setOpen] = useState(true)
  const [body, setBody] = useState('')
  const [error, setError] = useState('')
  const organizer = user?.id === event.organizer_id

  async function load() {
    const data = await graphApi.chat(slug)
    setMessages(data.messages)
    setOpen(data.open)
  }

  useEffect(() => {
    load().catch((err) => setError(err.message))
  }, [slug])

  async function send(ev: FormEvent) {
    ev.preventDefault()
    try {
      await graphApi.postChat(slug, body)
      setBody('')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chat closed')
    }
  }

  return (
    <section className="list" style={{ marginTop: 18 }}>
      {error && <div className="error">{error}</div>}
      {!open && <div className="error">Chat closed. Read-only archive.</div>}
      {open && (
        <div className="row-actions">
          <button className="btn ghost" onClick={() => graphApi.recap(slug).then(load)}>AI recap</button>
        </div>
      )}
      {messages.map((msg) => (
        <article className={`card ${msg.is_pinned ? 'pinned' : ''}`} key={msg.id}>
          <p className="eyebrow">{msg.is_system ? 'System recap' : msg.author.name} {msg.flagged ? '· flagged' : ''}</p>
          <p>{msg.body}</p>
          {open && (
            <div className="row-actions">
              <button className="text-btn" onClick={() => graphApi.report(slug, msg.id, 'reported').then(load)}>Report</button>
              {organizer && <button className="text-btn" onClick={() => graphApi.pin(slug, msg.id).then(load)}>Pin</button>}
            </div>
          )}
        </article>
      ))}
      {open && (
        <form className="form" onSubmit={send}>
          <textarea rows={3} value={body} onChange={(e) => setBody(e.target.value)} required placeholder="Public takeaway…" />
          <button className="btn primary" type="submit">Post</button>
        </form>
      )}
    </section>
  )
}
