import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { authApi, getToken, setToken } from './api'
import type { User } from './types'

type AuthState = {
  user: User | null
  ready: boolean
  login: (email: string, password: string) => Promise<void>
  register: (payload: { email: string; password: string; name: string; role: 'mentee' | 'mentor' }) => Promise<void>
  logout: () => void
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(false)

  async function refresh() {
    if (!getToken()) {
      setUser(null)
      setReady(true)
      return
    }
    try {
      setUser(await authApi.me())
    } catch {
      setToken(null)
      setUser(null)
    } finally {
      setReady(true)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  const value = useMemo<AuthState>(
    () => ({
      user,
      ready,
      async login(email, password) {
        const result = await authApi.login(email, password)
        setToken(result.access_token)
        setUser(result.user)
      },
      async register(payload) {
        const result = await authApi.register(payload)
        setToken(result.access_token)
        setUser(result.user)
      },
      logout() {
        setToken(null)
        setUser(null)
      },
      refresh,
    }),
    [user, ready],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('AuthProvider missing')
  return ctx
}
