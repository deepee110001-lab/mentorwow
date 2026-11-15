import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { guruApi } from '../api'
import { useAuth } from '../auth'
import { formatWhen } from '../lib'
import type { GuruEvent } from '../types'

export function Wallet() {
  const { user, ready, refresh } = useAuth()
  const [ledger, setLedger] = useState<GuruEvent[]>([])
  const [packs, setPacks] = useState<{ id: string; guru: number }[]>([])
  const [error, setError] = useState('')
  const [flash, setFlash] = useState('')

  async function load() {
    const [nextLedger, nextPacks] = await Promise.all([guruApi.ledger(), guruApi.packs()])
    setLedger(nextLedger)
    setPacks(nextPacks)
  }

  useEffect(() => {
    if (user) load().catch((err) => setError(err.message))
  }, [user])

  if (!ready) return <main className="page">Loading…</main>
  if (!user) return <Navigate to="/login" replace />

  async function buy(pack: string) {
    setError('')
    try {
      const result = await guruApi.buy(pack)
      setFlash(`+${result.added} GURU`)
      await refresh()
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Purchase failed')
    }
  }

  return (
    <main className="page">
      <p className="eyebrow">Karma, as a coin</p>
      <h1 className="serif" style={{ fontSize: 52, marginTop: 6 }}>{user.guru_balance} GURU</h1>
      <p className="lede">Earned when you give five minutes. Spent to seek. Bought if you need a stack.</p>
      {error && <div className="error">{error}</div>}
      {flash && <div className="success">{flash}</div>}
      <div className="grid three" style={{ marginTop: 24 }}>
        {packs.map((pack) => (
          <article className="card" key={pack.id}>
            <p className="eyebrow">{pack.id}</p>
            <h3 className="serif" style={{ fontSize: 36, margin: '4px 0' }}>{pack.guru}</h3>
            <button className="btn primary" onClick={() => buy(pack.id)}>Buy</button>
          </article>
        ))}
      </div>
      <div className="list" style={{ marginTop: 28 }}>
        {ledger.map((item, index) => (
          <article className="card" key={`${item.created_at}-${index}`}>
            <strong>{item.amount > 0 ? '+' : ''}{item.amount} GURU</strong>
            <span> · {item.reason}</span>
            <p className="empty">{item.note} · {formatWhen(item.created_at)}</p>
          </article>
        ))}
      </div>
    </main>
  )
}
