import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

export function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('mentee@mentorwow.app')
  const [password, setPassword] = useState('mentorwow')
  const [error, setError] = useState('')

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError('')
    try {
      await login(email, password)
      navigate('/desk')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not sign in')
    }
  }

  return (
    <main className="page">
      <div className="auth-wrap card">
        <p className="eyebrow">Welcome back</p>
        <h1 className="serif" style={{ fontSize: 42, margin: '8px 0 18px' }}>
          Sign in to the desk
        </h1>
        {error && <div className="error">{error}</div>}
        <form className="form" onSubmit={onSubmit}>
          <label className="field">
            <span>Email</span>
            <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </label>
          <label className="field">
            <span>Password</span>
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
          </label>
          <button className="btn primary" type="submit">
            Enter
          </button>
        </form>
        <div className="demo">
          <button className="btn ghost" type="button" onClick={() => { setEmail('mentee@mentorwow.app'); setPassword('mentorwow') }}>
            Demo mentee
          </button>
          <button className="btn ghost" type="button" onClick={() => { setEmail('amara@mentorwow.app'); setPassword('mentorwow') }}>
            Demo mentor
          </button>
        </div>
        <p style={{ marginTop: 18 }}>
          New here? <Link to="/register">Join the atelier</Link>
        </p>
      </div>
    </main>
  )
}
