import type {
  ChatMsg,
  EventCallRow,
  EventInfo,
  GuruEvent,
  Metrics,
  Post,
  PrivateStats,
  PublicProfile,
  QueryItem,
  User,
  VisiblePerson,
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
    return detail.map((item) => (typeof item === 'object' && item && 'msg' in item ? String(item.msg) : String(item))).join(' ')
  }
  return 'Request failed'
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers = new Headers(options.headers)
  if (!headers.has('Content-Type') && options.body && !(options.body instanceof FormData)) {
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

export const feedApi = {
  list: (topic?: string) => api<Post[]>(`/api/feed${topic ? `?topic=${encodeURIComponent(topic)}` : ''}`),
  topics: () => api<string[]>('/api/topics'),
  create: (payload: { title: string; body: string; topic: string }) =>
    api<Post>('/api/posts', { method: 'POST', body: JSON.stringify(payload) }),
  vote: (id: number) => api<Post>(`/api/posts/${id}/vote`, { method: 'POST', body: '{}' }),
}

export const meApi = {
  update: (payload: { handle?: string; accent?: string }) =>
    api<User>('/api/me', { method: 'PUT', body: JSON.stringify(payload) }),
  private: () => api<PrivateStats>('/api/me/private'),
  addProject: (payload: object) => api<User>('/api/me/projects', { method: 'POST', body: JSON.stringify(payload) }),
  editProject: (id: number, payload: object) =>
    api<User>(`/api/me/projects/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteProject: (id: number) => api<User>(`/api/me/projects/${id}`, { method: 'DELETE' }),
}

export const peopleApi = {
  get: (handle: string) => api<PublicProfile>(`/api/u/${handle}`),
  follow: (handle: string) => api<{ following: boolean }>(`/api/u/${handle}/follow`, { method: 'POST', body: '{}' }),
}

export const guruApi = {
  ledger: () => api<GuruEvent[]>('/api/guru/ledger'),
  packs: () => api<{ id: string; guru: number }[]>('/api/guru/packs'),
  buy: (pack: string) => api<{ guru_balance: number; added: number }>('/api/guru/buy', { method: 'POST', body: JSON.stringify({ pack }) }),
}

export const callApi = {
  enter: (topic: string, side: 'give' | 'seek') =>
    api<{ status: string; room_id?: string; side?: string }>('/api/calls/enter', {
      method: 'POST',
      body: JSON.stringify({ topic, side }),
    }),
  status: () => api<{ status: string; room_id?: string | null; side?: string | null; topic?: string | null; seconds?: number }>('/api/calls/status'),
  leave: () => api('/api/calls/leave', { method: 'POST', body: '{}' }),
}

export const authApi = {
  me: () => api<User>('/api/auth/me'),
  login: (email: string, password: string) =>
    api<{ access_token: string; user: User }>('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  register: (payload: { email: string; password: string; name?: string; handle?: string }) =>
    api<{ access_token: string; user: User }>('/api/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
  magic: (email: string) => api<{ ok: boolean; dev_token?: string | null }>('/api/auth/magic-link', { method: 'POST', body: JSON.stringify({ email }) }),
}

export const graphApi = {
  resolveJoin: (token: string) => api<{ event: EventInfo; joined: boolean; authenticated: boolean }>(`/api/join/${token}`),
  join: (token: string, payload: object) => api<{ ok: boolean; slug: string; event: EventInfo }>(`/api/join/${token}`, { method: 'POST', body: JSON.stringify(payload) }),
  event: (slug: string) => api<{ event: EventInfo; member: object; is_organizer: boolean }>(`/api/events/${slug}`),
  people: (slug: string) => api<VisiblePerson[]>(`/api/events/${slug}/people`),
  queries: (slug: string) => api<QueryItem[]>(`/api/events/${slug}/queries`),
  createQuery: (slug: string, payload: object) =>
    api<QueryItem>(`/api/events/${slug}/queries`, { method: 'POST', body: JSON.stringify(payload) }),
  respond: (id: number, payload: object) => api(`/api/queries/${id}/respond`, { method: 'POST', body: JSON.stringify(payload) }),
  chat: (slug: string) => api<{ open: boolean; closes_at: string; messages: ChatMsg[] }>(`/api/events/${slug}/chat`),
  postChat: (slug: string, body: string, parent_id?: number) =>
    api<ChatMsg>(`/api/events/${slug}/chat`, { method: 'POST', body: JSON.stringify({ body, parent_id }) }),
  recap: (slug: string) => api<ChatMsg>(`/api/events/${slug}/chat/recap`, { method: 'POST', body: JSON.stringify({}) }),
  report: (slug: string, id: number, reason: string) =>
    api(`/api/events/${slug}/chat/${id}/report`, { method: 'POST', body: JSON.stringify({ reason }) }),
  pin: (slug: string, id: number) => api(`/api/events/${slug}/chat/${id}/pin`, { method: 'POST', body: JSON.stringify({}) }),
  calls: (slug: string) => api<EventCallRow[]>(`/api/events/${slug}/calls`),
  completeCall: (id: number, payload: object) => api(`/api/calls/${id}/complete`, { method: 'POST', body: JSON.stringify(payload) }),
  consent: (payload: object) => api('/api/consent', { method: 'POST', body: JSON.stringify(payload) }),
  profile: () => api<Record<string, unknown>>('/api/me/profile'),
  saveProfile: (payload: object) => api('/api/me/profile', { method: 'PUT', body: JSON.stringify(payload) }),
  uploadResume: (file: File) => {
    const data = new FormData()
    data.append('file', file)
    return api<{ skill_tags: string[]; can_advise_on: string[]; open_to_collaborate_on: string[] }>('/api/me/resume', { method: 'POST', body: data })
  },
  organizerEvents: () => api<EventInfo[]>('/api/organizer/events'),
  createEvent: (payload: object) => api<EventInfo>('/api/organizer/events', { method: 'POST', body: JSON.stringify(payload) }),
  dashboard: (id: number) => api<EventInfo>(`/api/organizer/events/${id}`),
  closeChat: (id: number) => api(`/api/organizer/events/${id}/close-chat`, { method: 'POST', body: '{}' }),
  closeFeed: (id: number) => api(`/api/organizer/events/${id}/close-feed`, { method: 'POST', body: '{}' }),
  askEvent2: (id: number) => api(`/api/organizer/events/${id}/ask-event-2`, { method: 'POST', body: '{}' }),
  notifications: () => api<{ id: number; title: string; body: string; link: string }[]>('/api/notifications'),
  pilot: (gate: string) => api<Metrics & { events: unknown[] }>(`/api/pilot/metrics?gate=${encodeURIComponent(gate)}`),
}
