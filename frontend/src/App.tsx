import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth'
import { Layout } from './components/Layout'
import { Desk } from './pages/Desk'
import { Discover } from './pages/Discover'
import { Home } from './pages/Home'
import { Login } from './pages/Login'
import { MentorDetail } from './pages/MentorDetail'
import { Register } from './pages/Register'
import { Studio } from './pages/Studio'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Home />} />
            <Route path="/discover" element={<Discover />} />
            <Route path="/mentors/:id" element={<MentorDetail />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/studio" element={<Studio />} />
            <Route path="/desk" element={<Desk />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
