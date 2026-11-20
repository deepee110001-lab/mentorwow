import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { authApi, getToken, setToken } from './api'
import type { User } from './types'

type AuthState = {
  user: User | null
  ready: boolean
  login: (email: string, password: string) => Promise<boolean>
  loginGoogle: (credential: string) => Promise<boolean>
  register: (payload: { email: string; password: string; name?: string; handle?: string }) => Promise<boolean>
  logout: () => void
  refresh: () => Promise<void>
  setUser: (user: User) => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(false)

  async function refresh() {
    const params = new URLSearchParams(window.location.search)
    const linkedin = params.get('linkedin_token')
    if (linkedin) {
      setToken(linkedin)
      params.delete('linkedin_token')
      window.history.replaceState({}, '', window.location.pathname)
    }
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
      setUser,
      async login(email, password) {
        const result = await authApi.login(email, password)
        setToken(result.access_token)
        setUser(result.user)
        return Boolean(result.is_new)
      },
      async loginGoogle(credential) {
        const result = await authApi.google(credential)
        setToken(result.access_token)
        setUser(result.user)
        return Boolean(result.is_new)
      },
      async register(payload) {
        const result = await authApi.register(payload)
        setToken(result.access_token)
        setUser(result.user)
        return Boolean(result.is_new)
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
