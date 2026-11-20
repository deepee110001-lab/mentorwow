import { useEffect, useRef, useState } from 'react'
import { Banner, Button } from './ui'

type AuthConfig = {
  google_client_id: string
  google_enabled: boolean
}

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (opts: {
            client_id: string
            callback: (res: { credential: string }) => void
            ux_mode?: string
          }) => void
          renderButton: (el: HTMLElement, opts: Record<string, string>) => void
        }
      }
    }
  }
}

let gisLoader: Promise<void> | null = null

function loadGis() {
  if (window.google?.accounts?.id) return Promise.resolve()
  if (gisLoader) return gisLoader
  gisLoader = new Promise((resolve, reject) => {
    const src = 'https://accounts.google.com/gsi/client'
    const existing = document.querySelector(`script[src="${src}"]`) as HTMLScriptElement | null
    const done = () => {
      if (window.google?.accounts?.id) resolve()
      else reject(new Error('Google sign-in failed to load'))
    }
    if (existing) {
      if (window.google?.accounts?.id) {
        resolve()
        return
      }
      existing.addEventListener('load', done)
      existing.addEventListener('error', () => reject(new Error('Google sign-in failed to load')))
      return
    }
    const script = document.createElement('script')
    script.src = src
    script.async = true
    script.onload = done
    script.onerror = () => reject(new Error('Google sign-in failed to load'))
    document.head.appendChild(script)
  })
  return gisLoader
}

function GoogleMark() {
  return (
    <svg className="oauth-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1Z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23Z" />
      <path fill="#FBBC05" d="M5.84 14.09A6.6 6.6 0 0 1 5.5 12c0-.72.12-1.43.34-2.09V7.07H2.18A11 11 0 0 0 1 12c0 1.77.42 3.45 1.18 4.93z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1A11 11 0 0 0 2.18 7.07l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38Z" />
    </svg>
  )
}

function LinkedInMark() {
  return (
    <svg className="oauth-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="currentColor"
        d="M20.45 20.45h-3.56v-5.57c0-1.33-.03-3.04-1.85-3.04-1.85 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.41v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46zM5.34 7.43a2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12M7.12 20.45H3.56V9h3.56z"
      />
    </svg>
  )
}

export function SocialAuth({ onGoogle }: { onGoogle: (credential: string) => void }) {
  const host = useRef<HTMLDivElement>(null)
  const onGoogleRef = useRef(onGoogle)
  onGoogleRef.current = onGoogle
  const [gisReady, setGisReady] = useState(false)
  const [googleEnabled, setGoogleEnabled] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    async function boot() {
      try {
        const response = await fetch('/api/auth/config')
        if (!response.ok) return
        const config = (await response.json()) as AuthConfig
        if (cancelled) return
        if (!config.google_enabled || !config.google_client_id) {
          setGoogleEnabled(false)
          return
        }
        setGoogleEnabled(true)
        await loadGis()
        if (cancelled || !host.current || !window.google) return
        window.google.accounts.id.initialize({
          client_id: config.google_client_id,
          ux_mode: 'popup',
          callback: (res) => onGoogleRef.current(res.credential),
        })
        host.current.innerHTML = ''
        window.google.accounts.id.renderButton(host.current, {
          theme: 'outline',
          size: 'large',
          text: 'continue_with',
          shape: 'pill',
          width: '400',
        })
        if (!cancelled) setGisReady(true)
      } catch {
        if (!cancelled) setGisReady(false)
      }
    }
    boot()
    return () => {
      cancelled = true
    }
  }, [])

  function googleFallback() {
    if (gisReady) return
    setError(
      googleEnabled
        ? 'Google sign-in is loading. Wait a moment and try again.'
        : 'Google sign-in is not configured for this site yet.',
    )
  }

  return (
    <div className="social-auth">
      <div className="oauth-google-wrap">
        <button type="button" className="btn oauth google" onClick={googleFallback}>
          <GoogleMark />
          Continue with Google
        </button>
        <div ref={host} className={`oauth-google-overlay${gisReady ? ' live' : ''}`} />
      </div>
      <Button className="oauth linkedin" href="/api/auth/linkedin">
        <LinkedInMark />
        Continue with LinkedIn
      </Button>
      {error && <Banner>{error}</Banner>}
    </div>
  )
}
