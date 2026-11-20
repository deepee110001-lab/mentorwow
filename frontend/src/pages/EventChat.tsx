import { useEffect, useLayoutEffect, useRef, useState, type CSSProperties, type FormEvent, type KeyboardEvent } from 'react'
import { createPortal } from 'react-dom'
import { useOutletContext } from 'react-router-dom'
import { graphApi } from '../api'
import { useAuth } from '../auth'
import type { ChatMsg, EventInfo } from '../types'
import { Banner, Button } from '../ui'

function stamp(iso: string) {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function fullStamp(iso: string) {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
}

function menuStyle(btn: HTMLElement): CSSProperties {
  const rect = btn.getBoundingClientRect()
  const width = 200
  const height = 168
  const gap = 6
  let left = rect.right - width
  if (left < 8) left = 8
  if (left + width > window.innerWidth - 8) left = Math.max(8, window.innerWidth - width - 8)
  const openUp = window.innerHeight - rect.bottom < height + gap
  if (openUp) return { bottom: window.innerHeight - rect.top + gap, left }
  return { top: rect.bottom + gap, left }
}

function MoreMenu({
  open,
  onToggle,
  onDelete,
  onPin,
  info,
}: {
  open: boolean
  onToggle: () => void
  onDelete?: () => void
  onPin?: () => void
  info: { sent: string; from: string; kind: string; poll?: { yay: number; nay: number; total: number } | null }
}) {
  const [page, setPage] = useState<'menu' | 'info'>('menu')
  const btnRef = useRef<HTMLButtonElement>(null)
  const [style, setStyle] = useState<CSSProperties>({})

  useEffect(() => {
    if (!open) setPage('menu')
  }, [open])

  useLayoutEffect(() => {
    if (!open || !btnRef.current) return
    setStyle(menuStyle(btnRef.current))
  }, [open, page])

  const sheet = open ? (
    <div className={`wa-menu ${page === 'info' ? 'wa-info' : ''}`} role="menu" style={style} onClick={(ev) => ev.stopPropagation()}>
      {page === 'menu' ? (
        <>
          <button type="button" role="menuitem" onClick={() => setPage('info')}>
            Info
          </button>
          {onPin && (
            <button type="button" role="menuitem" onClick={onPin}>
              Pin
            </button>
          )}
          {onDelete && (
            <button type="button" role="menuitem" onClick={onDelete}>
              Delete
            </button>
          )}
        </>
      ) : (
        <>
          <p className="wa-info-kicker">Message info</p>
          <p>Sent {fullStamp(info.sent)}</p>
          <p>From /{info.from}</p>
          <p>{info.kind === 'poll' ? 'Poll' : 'Message'}</p>
          {info.poll && (
            <p>
              Yay {info.poll.yay} · Nay {info.poll.nay} · {info.poll.total} vote{info.poll.total === 1 ? '' : 's'}
            </p>
          )}
        </>
      )}
    </div>
  ) : null

  return (
    <div className="wa-more" onClick={(ev) => ev.stopPropagation()}>
      <button
        ref={btnRef}
        type="button"
        className="wa-dots"
        aria-label="More"
        aria-expanded={open}
        onClick={() => onToggle()}
      >
        ⋮
      </button>
      {sheet ? createPortal(sheet, document.body) : null}
    </div>
  )
}

export function EventChat() {
  const { slug, event } = useOutletContext<{ slug: string; event: EventInfo }>()
  const { user } = useAuth()
  const [messages, setMessages] = useState<ChatMsg[]>([])
  const [open, setOpen] = useState(true)
  const [body, setBody] = useState('')
  const [asPoll, setAsPoll] = useState(false)
  const [attachOpen, setAttachOpen] = useState(false)
  const [menuId, setMenuId] = useState<number | null>(null)
  const [tab, setTab] = useState<'thread' | 'polls'>('thread')
  const [myPolls, setMyPolls] = useState<ChatMsg[]>([])
  const [error, setError] = useState('')
  const threadRef = useRef<HTMLDivElement>(null)
  const organizer = user?.id === event.organizer_id

  async function load() {
    const [data, mine] = await Promise.all([graphApi.chat(slug), graphApi.myPolls()])
    setMessages(data.messages)
    setOpen(data.open)
    setMyPolls(mine)
  }

  useEffect(() => {
    load().catch((err) => setError(err.message))
  }, [slug])

  useEffect(() => {
    const node = threadRef.current
    if (node) node.scrollTop = node.scrollHeight
  }, [messages, tab])

  useEffect(() => {
    if (menuId == null) return
    function close() {
      setMenuId(null)
    }
    window.addEventListener('click', close)
    threadRef.current?.addEventListener('scroll', close)
    return () => {
      window.removeEventListener('click', close)
      threadRef.current?.removeEventListener('scroll', close)
    }
  }, [menuId])

  async function send(ev?: FormEvent) {
    ev?.preventDefault()
    const text = body.trim()
    if (!text) return
    try {
      await graphApi.postChat(slug, text, undefined, asPoll ? 'poll' : 'message')
      setBody('')
      setAsPoll(false)
      setAttachOpen(false)
      setMenuId(null)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chat closed')
    }
  }

  function onKey(ev: KeyboardEvent<HTMLTextAreaElement>) {
    if (ev.key === 'Enter' && !ev.shiftKey) {
      ev.preventDefault()
      void send()
    }
  }

  async function vote(id: number, choice: 'yay' | 'nay') {
    await graphApi.voteChat(slug, id, choice)
    await load()
  }

  async function remove(id: number) {
    setError('')
    setMenuId(null)
    try {
      await graphApi.deleteChat(slug, id)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not delete')
    }
  }

  const roomPolls = myPolls.filter((msg) => msg.event?.slug === slug && !msg.deleted)

  return (
    <div className="wa">
      <div className="wa-toolbar">
        <button className={tab === 'thread' ? 'on' : ''} type="button" onClick={() => setTab('thread')}>
          Chat
        </button>
        <button className={tab === 'polls' ? 'on' : ''} type="button" onClick={() => setTab('polls')}>
          My polls
        </button>
        {open && tab === 'thread' && (
          <Button variant="text" onClick={() => graphApi.recap(slug).then(load)}>
            Recap
          </Button>
        )}
      </div>
      {error && <Banner>{error}</Banner>}
      {!open && <p className="wa-closed">Chat closed. Read-only archive.</p>}

      {tab === 'polls' ? (
        <div className="wa-thread" ref={threadRef}>
          {roomPolls.length === 0 && <p className="wa-empty">Attach a poll from + in the composer.</p>}
          {roomPolls.map((msg) => (
            <article className="wa-bubble mine poll" key={msg.id}>
              <p className="wa-meta">
                Yay or Nay
                <MoreMenu
                  open={menuId === msg.id}
                  onToggle={() => setMenuId((current) => (current === msg.id ? null : msg.id))}
                  onDelete={() => remove(msg.id)}
                  info={{ sent: msg.created_at, from: user?.handle || 'you', kind: 'poll', poll: msg.poll }}
                />
              </p>
              <p>{msg.body}</p>
              {msg.poll && (
                <div className="poll-row">
                  <span>Yay {msg.poll.yay}</span>
                  <span>Nay {msg.poll.nay}</span>
                  <span className="empty">{msg.poll.total} vote{msg.poll.total === 1 ? '' : 's'}</span>
                </div>
              )}
            </article>
          ))}
        </div>
      ) : (
        <div className="wa-thread" ref={threadRef}>
          {messages.map((msg) => {
            const mine = Boolean(user && msg.author.user_id === user.id)
            if (msg.is_system) {
              return (
                <div className="wa-system" key={msg.id}>
                  {msg.body}
                </div>
              )
            }
            const canDelete = mine || organizer
            return (
              <article
                className={`wa-bubble ${mine ? 'mine' : 'theirs'} ${msg.kind === 'poll' ? 'poll' : ''} ${msg.is_pinned ? 'pinned' : ''} ${msg.deleted ? 'deleted' : ''}`}
                key={msg.id}
              >
                <p className="wa-meta">
                  {msg.deleted ? 'Deleted' : msg.kind === 'poll' ? 'Poll' : `/${msg.author.handle || msg.author.name}`}
                  {msg.is_pinned ? ' · pinned' : ''}
                  <span>{stamp(msg.created_at)}</span>
                  {!msg.deleted && (
                    <MoreMenu
                      open={menuId === msg.id}
                      onToggle={() => {
                        setAttachOpen(false)
                        setMenuId((current) => (current === msg.id ? null : msg.id))
                      }}
                      onDelete={canDelete ? () => remove(msg.id) : undefined}
                      onPin={open && organizer ? () => graphApi.pin(slug, msg.id).then(() => { setMenuId(null); return load() }) : undefined}
                      info={{
                        sent: msg.created_at,
                        from: msg.author.handle || msg.author.name,
                        kind: msg.kind || 'message',
                        poll: msg.poll,
                      }}
                    />
                  )}
                </p>
                <p>{msg.body}</p>
                {!msg.deleted && msg.kind === 'poll' && msg.poll && (
                  <div className="poll-row">
                    <button
                      className={`btn poll-btn yay ${msg.poll.my_vote === 'yay' ? 'on' : ''}`}
                      type="button"
                      disabled={!open}
                      onClick={() => vote(msg.id, 'yay')}
                    >
                      Yay {msg.poll.yay}
                    </button>
                    <button
                      className={`btn poll-btn nay ${msg.poll.my_vote === 'nay' ? 'on' : ''}`}
                      type="button"
                      disabled={!open}
                      onClick={() => vote(msg.id, 'nay')}
                    >
                      Nay {msg.poll.nay}
                    </button>
                  </div>
                )}
              </article>
            )
          })}
        </div>
      )}

      {open && tab === 'thread' && (
        <form className="wa-composer" onSubmit={send}>
          <div className="wa-attach-wrap">
            <button
              className="wa-plus"
              type="button"
              aria-label="Attach"
              onClick={() => {
                setMenuId(null)
                setAttachOpen((value) => !value)
              }}
            >
              +
            </button>
            {attachOpen && (
              <div className="wa-attach-menu">
                <button
                  type="button"
                  onClick={() => {
                    setAsPoll(true)
                    setAttachOpen(false)
                  }}
                >
                  Poll
                </button>
              </div>
            )}
          </div>
          <textarea
            rows={1}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            onKeyDown={onKey}
            required
            placeholder={asPoll ? 'Ask a Yay or Nay question…' : 'Message'}
          />
          {asPoll && (
            <button className="text-btn" type="button" onClick={() => setAsPoll(false)}>
              Cancel
            </button>
          )}
          <button className="wa-send" type="submit">
            {asPoll ? 'Ask' : 'Send'}
          </button>
        </form>
      )}
    </div>
  )
}
