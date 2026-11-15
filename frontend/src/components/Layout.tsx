import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { graphApi } from '../api'
import { useAuth } from '../auth'

export function Layout() {
  const { user, logout } = useAuth()
  const [notes, setNotes] = useState<{ id: number; title: string; body: string; link: string }[]>([])

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
          {user ? (
            <>
              <NavLink to="/organizer">Organize</NavLink>
              <NavLink to="/e/cedat-pilot/feed">Pilot event</NavLink>
              {notes.length > 0 && (
                <details className="notes">
                  <summary>{notes.length} notices</summary>
                  {notes.slice(0, 6).map((note) => (
                    <NavLink key={note.id} to={note.link || '/'}>
                      {note.title}
                    </NavLink>
                  ))}
                </details>
              )}
              <span className="empty">{user.name || user.handle}</span>
              <button className="text-btn" onClick={logout}>
                Sign out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login">Sign in</NavLink>
              <NavLink to="/register" className="btn primary">
                Join
              </NavLink>
            </>
          )}
        </nav>
      </header>
      <Outlet />
      <footer className="footer">
        <span>Event graph · 24h chat · 7-day feed · 5-min calls</span>
        <span>DPDP: consent is enforced on the server.</span>
      </footer>
    </div>
  )
}
