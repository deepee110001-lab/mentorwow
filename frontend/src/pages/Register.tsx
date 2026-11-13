import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

export function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<'mentee' | 'mentor'>('mentee')
  const [error, setError] = useState('')

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError('')
    try {
      await register({ name, email, password, role })
      navigate('/studio')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create account')
    }
  }

  return (
    <main className="page">
      <div className="auth-wrap card">
        <p className="eyebrow">Join</p>
        <h1 className="serif" style={{ fontSize: 42, margin: '8px 0 18px' }}>
          Pick a chair
        </h1>
        {error && <div className="error">{error}</div>}
        <form className="form" onSubmit={onSubmit}>
          <div className="role-pick">
            <button type="button" className={role === 'mentee' ? 'on' : ''} onClick={() => setRole('mentee')}>
              <b>Mentee</b>
              <div>I want someone who has already done this.</div>
            </button>
            <button type="button" className={role === 'mentor' ? 'on' : ''} onClick={() => setRole('mentor')}>
              <b>Mentor</b>
              <div>I can sit with people on the work I still do.</div>
            </button>
          </div>
          <label className="field">
            <span>Name</span>
            <input value={name} onChange={(event) => setName(event.target.value)} required minLength={2} />
          </label>
          <label className="field">
            <span>Email</span>
            <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </label>
          <label className="field">
            <span>Password</span>
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={6} />
          </label>
          <button className="btn primary" type="submit">
            Create studio
          </button>
        </form>
        <p style={{ marginTop: 18 }}>
          Already have a desk? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </main>
  )
}
