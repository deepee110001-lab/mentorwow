import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { graphApi } from '../api'
import { useAuth } from '../auth'
import { Button } from '../ui'

export function Layout() {
  const { user, logout } = useAuth()
  const [notes, setNotes] = useState<{ id: number; title: string; body: string; link: string }[]>([])
  const admin = Boolean(user?.is_admin)

  useEffect(() => {
    if (!user) return
    graphApi.notifications().then(setNotes).catch(() => setNotes([]))
  }, [user])

  return (
    <div className="shell">
      <header className="nav">
        <NavLink to="/" className="brand">
          <span className="brand-mark">MentorWow</span>
          <span className="brand-kicker">graph</span>
        </NavLink>
        <nav className="nav-links">
          {user && (
            <>
              <NavLink to="/connected">Connected</NavLink>
              {admin && (
                <>
                  <NavLink to="/organizer">Organize</NavLink>
                  <NavLink to="/e/mentorwow-pilot/feed">Pilot event</NavLink>
                  <NavLink to="/pilot/metrics">Metrics</NavLink>
                </>
              )}
              {admin && notes.length > 0 && (
                <details className="notes">
                  <summary>{notes.length} notices</summary>
                  {notes.slice(0, 6).map((note) => (
                    <NavLink key={note.id} to={note.link || '/'}>
                      {note.title}
                    </NavLink>
                  ))}
                </details>
              )}
              <span className="empty">/{user.handle}</span>
              <Button variant="text" onClick={logout}>
                Sign out
              </Button>
            </>
          )}
        </nav>
      </header>
      <Outlet />
      <footer className="footer">
        <span>Event graph · native connections stay · 24h chat · 5-min calls</span>
        <span>DPDP: consent is enforced on the server.</span>
      </footer>
    </div>
  )
}
