export type Project = {
  id: number
  title: string
  summary: string
  url: string
  topics: string[]
}

export type User = {
  id: number
  email: string
  handle: string
  name: string
  headline: string
  photo_url: string
  accent: string
  guru_balance: number
  projects: Project[]
}

export type Post = {
  id: number
  kind: string
  title: string
  body: string
  topic: string
  score: number
  created_at: string
  handle: string
  accent: string
  my_vote: number
}

export type PublicProfile = {
  handle: string
  accent: string
  projects: Project[]
  topics: string[]
  following: boolean
}

export type PrivateStats = {
  guru_balance: number
  given_minutes: number
  received_minutes: number
  topics: { topic: string; given_minutes: number; received_minutes: number }[]
}

export type GuruEvent = {
  amount: number
  reason: string
  note: string
  created_at: string
}

export type EventInfo = {
  id: number
  name: string
  slug: string
  join_link_token: string
  starts_at: string
  ends_at: string
  chat_closes_at: string
  feed_closes_at: string
  status: string
  organizer_id: number
  chat_open: boolean
  feed_open: boolean
  join_url?: string
  metrics?: Metrics
}

export type Metrics = {
  profiles_completed: number
  profiles_completed_pct: number
  chat_messages: number
  unique_posters?: number
  queries_posted: number
  queries_matched: number
  calls_accepted: number
  calls_completed: number
  repeat_attendees: number
  member_count?: number
  group_strengths?: {
    skill_tags: [string, number][]
    can_advise_on: [string, number][]
    open_to_collaborate_on: [string, number][]
  }
}

export type VisiblePerson = {
  user_id: number
  name: string
  headline: string
  photo_url: string
  skill_tags: string[]
  can_advise_on: string[]
  open_to_collaborate_on: string[]
  resume_visible: boolean
  resume_url: string | null
  email: string | null
  attendance_visibility: string
  is_self: boolean
}

export type QueryItem = {
  id: number
  type: 'skill' | 'collaboration'
  body: string
  available_slots: { start: string; end?: string }[]
  status: string
  created_at: string
  author: { user_id: number; name: string; headline: string }
  matched: boolean
  my_response: string | null
  match_reason: string | null
  match_count: number
}

export type ChatMsg = {
  id: number
  body: string
  is_pinned: boolean
  is_system: boolean
  flagged: boolean
  parent_id: number | null
  created_at: string
  author: { name: string; user_id: number | null }
}

export type EventCallRow = {
  id: number
  status: string
  scheduled_at: string
  duration_minutes: number
  meeting_url: string | null
  role: string
  other: { user_id: number; name: string; headline: string; email: string | null }
}
