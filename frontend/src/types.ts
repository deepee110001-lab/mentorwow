export type User = {
  id: number
  email: string
  name: string
  role: 'mentee' | 'mentor'
  headline: string
  bio: string
  location: string
  availability: string
  years_experience: number
  accent: string
  skills: string[]
}

export type Mentor = {
  id: number
  name: string
  role: string
  headline: string
  bio: string
  location: string
  availability: string
  years_experience: number
  accent: string
  skills: string[]
  mentee_count: number
}

export type Person = {
  id: number
  name: string
  headline: string
  accent: string
}

export type MentorshipRequest = {
  id: number
  mentee: Person
  mentor: Person
  goal: string
  message: string
  status: 'pending' | 'accepted' | 'declined' | 'withdrawn'
  created_at: string
}

export type MentorshipSession = {
  id: number
  mentee: Person
  mentor: Person
  title: string
  scheduled_at: string
  duration_minutes: number
  status: 'scheduled' | 'completed' | 'cancelled'
  notes: string
}

export type Skill = {
  name: string
  category: string
}
