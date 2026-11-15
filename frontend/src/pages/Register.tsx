import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../auth'

export function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const next = params.get('next') || '/organizer'
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError('')
    try {
      await register({ email, password, name })
      navigate(next)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not register')
    }
  }

  return (
    <main className="page">
      <div className="auth-wrap card">
        <p className="eyebrow">Portable profile starts here</p>
        <h1 className="serif" style={{ fontSize: 42, margin: '8px 0 18px' }}>Join with email</h1>
        {error && <div className="error">{error}</div>}
        <form className="form" onSubmit={onSubmit}>
          <label className="field">
            <span>Name</span>
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label className="field">
            <span>Email</span>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <label className="field">
            <span>Password</span>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={6} />
          </label>
          <button className="btn primary" type="submit">Create account</button>
        </form>
        <p style={{ marginTop: 16 }}>
          Already in? <Link to={`/login?next=${encodeURIComponent(next)}`}>Sign in</Link>
        </p>
      </div>
    </main>
  )
}
