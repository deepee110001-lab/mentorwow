import type {
  Mentor,
  MentorshipRequest,
  MentorshipSession,
  Skill,
  User,
} from './types'

const TOKEN_KEY = 'mentorwow.token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

function detailMessage(detail: unknown) {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => (typeof item === 'object' && item && 'msg' in item ? String(item.msg) : String(item)))
      .join(' ')
  }
  return 'Request failed'
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers = new Headers(options.headers)
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json')
  }
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(path, { ...options, headers })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(detailMessage(body.detail) || response.statusText)
  }
  if (response.status === 204) return undefined as T
  return response.json()
}

export const authApi = {
  me: () => api<User>('/api/auth/me'),
  login: (email: string, password: string) =>
    api<{ access_token: string; user: User }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  register: (payload: { email: string; password: string; name: string; role: 'mentee' | 'mentor' }) =>
    api<{ access_token: string; user: User }>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
}

export const mentorApi = {
  list: (params?: { q?: string; skill?: string }) => {
    const search = new URLSearchParams()
    if (params?.q) search.set('q', params.q)
    if (params?.skill) search.set('skill', params.skill)
    const suffix = search.toString() ? `?${search}` : ''
    return api<Mentor[]>(`/api/mentors${suffix}`)
  },
  skills: () => api<Skill[]>('/api/mentors/skills'),
  get: (id: number) => api<Mentor>(`/api/mentors/${id}`),
}

export const profileApi = {
  update: (payload: Partial<User> & { skills?: string[] }) =>
    api<User>('/api/profile', { method: 'PUT', body: JSON.stringify(payload) }),
}

export const requestApi = {
  list: () => api<MentorshipRequest[]>('/api/requests'),
  create: (payload: { mentor_id: number; goal: string; message: string }) =>
    api<MentorshipRequest>('/api/requests', { method: 'POST', body: JSON.stringify(payload) }),
  update: (id: number, status: MentorshipRequest['status']) =>
    api<MentorshipRequest>(`/api/requests/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),
}

export const sessionApi = {
  list: () => api<MentorshipSession[]>('/api/sessions'),
  create: (payload: {
    peer_id: number
    title: string
    scheduled_at: string
    duration_minutes: number
    request_id?: number
  }) => api<MentorshipSession>('/api/sessions', { method: 'POST', body: JSON.stringify(payload) }),
  update: (id: number, payload: Partial<Pick<MentorshipSession, 'status' | 'notes' | 'title'>>) =>
    api<MentorshipSession>(`/api/sessions/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
}
