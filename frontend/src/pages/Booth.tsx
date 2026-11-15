import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Navigate } from 'react-router-dom'
import { callApi, getToken } from '../api'
import { useAuth } from '../auth'
import { clock } from '../lib'
import { startPeer, type SignalPayload } from '../webrtc'

type EndState = {
  quality_score: number
  notes: string
  duration_seconds: number
  give_delta: number
  receive_delta: number
}

export function Booth() {
  const { user, ready, refresh } = useAuth()
  const [topic, setTopic] = useState('system design')
  const [side, setSide] = useState<'give' | 'seek'>('give')
  const [phase, setPhase] = useState<'idle' | 'waiting' | 'live' | 'ended'>('idle')
  const [message, setMessage] = useState('Quality room is empty until two chairs sit.')
  const [remaining, setRemaining] = useState(300)
  const [error, setError] = useState('')
  const [end, setEnd] = useState<EndState | null>(null)
  const localRef = useRef<HTMLVideoElement>(null)
  const remoteRef = useRef<HTMLVideoElement>(null)
  const socketRef = useRef<WebSocket | null>(null)
  const stopRef = useRef<(() => void) | null>(null)
  const timerRef = useRef<number | null>(null)

  useEffect(() => () => {
    socketRef.current?.close()
    stopRef.current?.()
    if (timerRef.current) window.clearInterval(timerRef.current)
  }, [])

  if (!ready) return <main className="page">Loading…</main>
  if (!user) return <Navigate to="/login" replace />

  async function enter(event: FormEvent) {
    event.preventDefault()
    setError('')
    try {
      const result = await callApi.enter(topic, side)
      await refresh()
      if (result.status === 'waiting') {
        setPhase('waiting')
        setMessage(`Waiting for a ${side === 'give' ? 'seeker' : 'giver'} on ${topic}. No names.`)
        poll()
      }
      if (result.status === 'matched' && result.room_id) {
        await joinRoom(result.room_id, result.side as 'give' | 'seek')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not enter')
    }
  }

  async function poll() {
    const handle = window.setInterval(async () => {
      const status = await callApi.status()
      if (status.status === 'matched' && status.room_id) {
        window.clearInterval(handle)
        await joinRoom(status.room_id, (status.side as 'give' | 'seek') || side)
      }
    }, 1200)
  }

  async function joinRoom(roomId: string, mySide: 'give' | 'seek') {
    const token = getToken()
    const socket = new WebSocket(`${location.origin.replace('http', 'ws')}/api/calls/ws/${roomId}?token=${token}`)
    socketRef.current = socket
    let peer: Awaited<ReturnType<typeof startPeer>> | null = null

    socket.onmessage = async (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'observer') {
        setMessage(data.message)
        setPhase('live')
      }
      if (data.type === 'ready' && localRef.current && remoteRef.current && !peer) {
        peer = await startPeer({
          local: localRef.current,
          remote: remoteRef.current,
          initiator: mySide === data.initiator_side,
          send: (payload) => socket.send(JSON.stringify({ type: 'signal', payload })),
        })
        stopRef.current = peer.stop
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
        timerRef.current = window.setInterval(() => {
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
      if (data.type === 'ended') {
        setEnd(data)
        setPhase('ended')
        stopRef.current?.()
        await refresh()
      }
    }
  }

  async function leave() {
    await callApi.leave()
    setPhase('idle')
  }

  return (
    <main className="page">
      <p className="eyebrow">Anonymous booth</p>
      <h1 className="serif" style={{ fontSize: 52, marginTop: 6 }}>Five minutes</h1>
      <p className="lede">P2P WebRTC. The third seat is our quality room. Handles stay outside.</p>
      {error && <div className="error">{error}</div>}

      {phase === 'idle' && (
        <form className="card form" onSubmit={enter} style={{ maxWidth: 560, marginTop: 24 }}>
          <label className="field">
            <span>Topic</span>
            <input value={topic} onChange={(event) => setTopic(event.target.value)} required />
          </label>
          <div className="role-pick">
            <button type="button" className={side === 'give' ? 'on' : ''} onClick={() => setSide('give')}>
              <b>Give</b>
              <div>Earn GURU. Sit on a topic you have shipped.</div>
            </button>
            <button type="button" className={side === 'seek' ? 'on' : ''} onClick={() => setSide('seek')}>
              <b>Seek</b>
              <div>Spend 5 GURU. Ask for five honest minutes.</div>
            </button>
          </div>
          <button className="btn primary" type="submit">Sit down</button>
        </form>
      )}

      {phase === 'waiting' && (
        <div className="card" style={{ marginTop: 24 }}>
          <p>{message}</p>
          <button className="btn ghost" onClick={leave}>Stand up</button>
        </div>
      )}

      {(phase === 'live' || phase === 'waiting') && (
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
            <span>Quality room</span>
            <b className="serif">{clock(remaining)}</b>
          </div>
        </section>
      )}
      {phase === 'live' && <p className="empty">{message}</p>}

      {phase === 'ended' && end && (
        <div className="card" style={{ marginTop: 24 }}>
          <p className="eyebrow">Quality room report</p>
          <h3 className="serif" style={{ fontSize: 36, margin: '6px 0' }}>{Math.round(end.quality_score)} / 100</h3>
          <p>{end.notes}</p>
          <p>Duration {clock(end.duration_seconds)}. GURU {end.give_delta ? `giver +${end.give_delta}` : ''} {end.receive_delta ? `seeker +${end.receive_delta}` : ''}</p>
          <button className="btn primary" onClick={() => { setPhase('idle'); setEnd(null) }}>Back to the booth</button>
        </div>
      )}
    </main>
  )
}
