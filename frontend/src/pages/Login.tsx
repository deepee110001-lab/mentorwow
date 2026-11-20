import { useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../auth'
import { SocialAuth } from '../SocialAuth'
import { track } from '../metrics'
import { Banner, Button, Card, Field, Page, Text } from '../ui'

const AUTH_ERRORS: Record<string, string> = {
  linkedin_not_configured: 'LinkedIn sign-in is not configured yet. Use Google or email.',
  google_not_configured: 'Google sign-in is not configured yet. Use LinkedIn or email.',
}

export function Login() {
  const { login, loginGoogle } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const next = params.get('next') || '/'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(AUTH_ERRORS[params.get('error') || ''] || '')
  const [emailOpen, setEmailOpen] = useState(Boolean(params.get('error')))

  function afterAuth(isNew: boolean, method: string) {
    track(isNew ? 'register_email' : 'login_email', { method, is_new: String(isNew) })
    navigate(next)
  }

  async function onGoogle(credential: string) {
    setError('')
    try {
      const isNew = await loginGoogle(credential)
      track(isNew ? 'register_google' : 'login_google', { method: 'google', is_new: String(isNew) })
      navigate(next)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Google sign-in failed')
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError('')
    try {
      const isNew = await login(email, password)
      afterAuth(isNew, 'email')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not continue')
    }
  }

  return (
    <Page>
      <Card className="auth-wrap" as="div">
        <Text variant="eyebrow">Anonymous</Text>
        <Text variant="title">Continue</Text>
        <Text variant="lede">
          New or returning — same door. You get a handle automatically. You can change it later.
        </Text>
        {error && <Banner>{error}</Banner>}
        <SocialAuth onGoogle={onGoogle} />
        {emailOpen ? (
          <form className="form" onSubmit={onSubmit}>
            <Field label="Email">
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
            </Field>
            <Field label="Password">
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                autoComplete="current-password"
              />
            </Field>
            <Button type="submit">Continue with email</Button>
          </form>
        ) : (
          <Button variant="text" className="email-fallback" onClick={() => setEmailOpen(true)}>
            Use email instead
          </Button>
        )}
      </Card>
    </Page>
  )
}
