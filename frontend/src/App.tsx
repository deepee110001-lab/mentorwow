import { useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { AuthProvider } from './auth'
import { track } from './metrics'
import { Layout } from './components/Layout'
import { Connected } from './pages/Connected'
import { EventCallRoom } from './pages/EventCallRoom'
import { EventCalls } from './pages/EventCalls'
import { EventChat } from './pages/EventChat'
import { EventFeed } from './pages/EventFeed'
import { EventPeople } from './pages/EventPeople'
import { EventProfile } from './pages/EventProfile'
import { EventShell } from './pages/EventShell'
import { Home } from './pages/Home'
import { Join } from './pages/Join'
import { Login } from './pages/Login'
import { OrganizerDashboard } from './pages/OrganizerDashboard'
import { OrganizerHome } from './pages/OrganizerHome'
import { OrganizerNew } from './pages/OrganizerNew'
import { PilotMetrics } from './pages/PilotMetrics'
import { Register } from './pages/Register'

function PageViews() {
  const location = useLocation()
  useEffect(() => {
    track('page_view', { path: location.pathname })
  }, [location.pathname])
  return null
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <PageViews />
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Home />} />
            <Route path="/connected" element={<Connected />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/join/:token" element={<Join />} />
            <Route path="/e/:slug/call/:callId" element={<EventCallRoom />} />
            <Route path="/e/:slug" element={<EventShell />}>
              <Route index element={<Navigate to="feed" replace />} />
              <Route path="feed" element={<EventFeed />} />
              <Route path="people" element={<EventPeople />} />
              <Route path="chat" element={<EventChat />} />
              <Route path="calls" element={<EventCalls />} />
              <Route path="profile" element={<EventProfile />} />
            </Route>
            <Route path="/organizer" element={<OrganizerHome />} />
            <Route path="/organizer/events/new" element={<OrganizerNew />} />
            <Route path="/organizer/events/:id" element={<OrganizerDashboard />} />
            <Route path="/pilot/metrics" element={<PilotMetrics />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
