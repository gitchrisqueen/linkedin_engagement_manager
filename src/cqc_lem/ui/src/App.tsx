import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import LoginModal from './components/LoginModal'
import Dashboard from './pages/Dashboard'
import Account from './pages/Account'
import ScheduleContent from './pages/ScheduleContent'
import ReviewSchedule from './pages/ReviewSchedule'
import Landing from './pages/Landing'

const queryClient = new QueryClient()

function AppRoutes() {
  const { user, isLoginModalOpen } = useAuth()

  return (
    <>
      {isLoginModalOpen && <LoginModal />}
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={user ? <Dashboard /> : <Landing />} />
          <Route
            path="account"
            element={<ProtectedRoute><Account /></ProtectedRoute>}
          />
          <Route
            path="schedule"
            element={<ProtectedRoute><ScheduleContent /></ProtectedRoute>}
          />
          <Route
            path="review"
            element={<ProtectedRoute><ReviewSchedule /></ProtectedRoute>}
          />
        </Route>
      </Routes>
    </>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
