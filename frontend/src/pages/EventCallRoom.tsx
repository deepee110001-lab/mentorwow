import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getToken } from '../api'
import { useAuth } from '../auth'
import { clock } from '../lib'
import { startPeer, type SignalPayload } from '../webrtc'

export function EventCallRoom() {
  const { slug, callId } = useParams()
  const { user, ready } = useAuth()
  const [message, setMessage] = useState('Waiting for the other chair. P2P, not recorded.')
  const [remaining, setRemaining] = useState(300)
  const [error, setError] = useState('')
  const [live, setLive] = useState(false)
  const localRef = useRef<HTMLVideoElement>(null)
  const remoteRef = useRef<HTMLVideoElement>(null)
  const stopRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    if (!ready || !user || !callId) return
    const token = getToken()
    const roomId = `ec-${callId}`
    const socket = new WebSocket(`${location.origin.replace('http', 'ws')}/api/calls/ws/${roomId}?token=${token}`)
    let peer: Awaited<ReturnType<typeof startPeer>> | null = null
    let timer: number | null = null
    let mySide: 'give' | 'seek' = 'give'

    socket.onmessage = async (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'joined' && (data.side === 'give' || data.side === 'seek')) {
        mySide = data.side
      }
      if (data.type === 'observer') {
        setMessage(data.message)
        setLive(true)
      }
      if (data.type === 'ready' && localRef.current && remoteRef.current && !peer) {
        peer = await startPeer({
          local: localRef.current,
          remote: remoteRef.current,
          initiator: mySide === (data.initiator_side || 'give'),
          send: (payload) => socket.send(JSON.stringify({ type: 'signal', payload })),
          token,
        })
        const beat = window.setInterval(async () => {
          if (!peer) return
          const stats = await peer.stats()
          socket.send(JSON.stringify({ type: 'stats', ...stats }))
        }, 3000)
        stopRef.current = () => {
          window.clearInterval(beat)
          peer?.stop()
        }
        setRemaining(data.seconds ?? 300)
        timer = window.setInterval(() => {
          setRemaining((value) => {
            if (value <= 1) {
              socket.send(JSON.stringify({ type: 'hangup' }))
              return 0
            }
            return value - 1
          })
        }, 1000)
      }
      if (data.type === 'signal' && data.payload) {
        await peer?.handle(data.payload as SignalPayload)
      }
      if (data.type === 'ended' || data.type === 'peer-left') {
        stopRef.current?.()
        setMessage('Call ended. Five minutes, not recorded.')
        setLive(false)
      }
    }
    socket.onerror = () => setError('Could not reach the call room')
    return () => {
      socket.close()
      stopRef.current?.()
      if (timer) window.clearInterval(timer)
    }
  }, [ready, user, callId])

  if (!ready) return <main className="page">Loading…</main>
  if (!user) return <main className="page">Sign in to join this call.</main>

  return (
    <main className="page">
      <p className="eyebrow">5-minute P2P call</p>
      <h1 className="serif" style={{ fontSize: 44, margin: '4px 0 8px' }}>In the room</h1>
      <p className="lede">{message}</p>
      {error && <div className="error">{error}</div>}
      <section className="booth" style={{ marginTop: 24 }}>
        <div className="tile">
          <video ref={localRef} muted playsInline autoPlay />
          <span>You</span>
        </div>
        <div className="tile">
          <video ref={remoteRef} playsInline autoPlay />
          <span>Other chair</span>
        </div>
        <div className="tile observer">
          <div className="pulse" />
          <span>Not recorded</span>
          <b className="serif">{clock(remaining)}</b>
        </div>
      </section>
      {live && <p className="empty">STUN first. TURN only if both of you are behind hard NATs.</p>}
      <div className="row-actions">
        <Link className="btn ghost" to={`/e/${slug}/calls`}>Back to my calls</Link>
      </div>
    </main>
  )
}
