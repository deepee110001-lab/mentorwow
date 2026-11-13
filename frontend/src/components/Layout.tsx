import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth'

export function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className="shell">
      <header className="nav">
        <NavLink to="/" className="brand">
          <span className="brand-mark">MentorWow</span>
          <span className="brand-kicker">atelier</span>
        </NavLink>
        <nav className="nav-links">
          <NavLink to="/discover">Find a mentor</NavLink>
          {user ? (
            <>
              <NavLink to="/desk">The desk</NavLink>
              <NavLink to="/studio">Studio</NavLink>
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
        <span>MentorWow — a quiet room for serious matching.</span>
        <span>Local demo. Password for seeded accounts: mentorwow</span>
      </footer>
    </div>
  )
}
