import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { authApi } from '../api'
import { useAuth } from '../auth'

export function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const next = params.get('next') || '/organizer'
  const [email, setEmail] = useState('organizer@mentorwow.app')
  const [password, setPassword] = useState('mentorwow')
  const [error, setError] = useState(
    params.get('error') === 'linkedin_not_configured'
      ? 'LinkedIn OAuth is not configured. Use email for the pilot. TODO: set LINKEDIN_CLIENT_ID.'
      : '',
  )

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError('')
    try {
      await login(email, password)
      navigate(next)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not sign in')
    }
  }

  async function magic() {
    setError('')
    try {
      const result = await authApi.magic(email)
      if (result.dev_token) {
        localStorage.setItem('mentorwow.token', result.dev_token)
        window.location.href = next
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Magic link failed')
    }
  }

  return (
    <main className="page">
      <div className="auth-wrap card">
        <p className="eyebrow">Email or LinkedIn</p>
        <h1 className="serif" style={{ fontSize: 42, margin: '8px 0 18px' }}>Sign in</h1>
        {error && <div className="error">{error}</div>}
        <form className="form" onSubmit={onSubmit}>
          <label className="field">
            <span>Email</span>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <label className="field">
            <span>Password</span>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>
          <button className="btn primary" type="submit">Enter</button>
        </form>
        <div className="demo">
          <button className="btn ghost" type="button" onClick={magic}>Email magic link</button>
          <a className="btn ghost" href="/api/auth/linkedin">LinkedIn (OAuth subset)</a>
        </div>
        <p style={{ marginTop: 16 }}>
          New? <Link to={`/register?next=${encodeURIComponent(next)}`}>Create an account</Link>
        </p>
      </div>
    </main>
  )
}
