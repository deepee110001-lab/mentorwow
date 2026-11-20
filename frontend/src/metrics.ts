import { getToken } from './api'

const SESSION_KEY = 'mentorwow.session'

export function sessionId() {
  let id = localStorage.getItem(SESSION_KEY)
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem(SESSION_KEY, id)
  }
  return id
}

export function track(name: string, properties: Record<string, string> = {}, eventId?: number) {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  fetch('/api/metrics/track', {
    method: 'POST',
    headers,
    body: JSON.stringify({
      name,
      session_id: sessionId(),
      path: window.location.pathname,
      event_id: eventId,
      properties: { ...properties, path: window.location.pathname },
    }),
    keepalive: true,
  }).catch(() => {})
}
