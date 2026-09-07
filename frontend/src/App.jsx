import { AuthProvider, useAuth } from './AuthContext'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import './App.css'

function AppRoutes() {
  const { user, loading } = useAuth()
  if (loading) return <div className="center-screen">Loading…</div>
  return user ? <Dashboard /> : <Login />
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}
