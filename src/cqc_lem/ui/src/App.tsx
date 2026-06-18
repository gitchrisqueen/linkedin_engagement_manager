import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Account from './pages/Account'
import ScheduleContent from './pages/ScheduleContent'
import ReviewSchedule from './pages/ReviewSchedule'

const queryClient = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="account" element={<Account />} />
            <Route path="schedule" element={<ScheduleContent />} />
            <Route path="review" element={<ReviewSchedule />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
