import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from './app/AuthContext'
import Sidebar from './components/Sidebar'

// Pages
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Deposits from './pages/Deposits'
import FDRList from './pages/FDRList'
import FDRDetail from './pages/FDRDetail'
import ReviewQueue from './pages/ReviewQueue'
import BankVerification from './pages/BankVerification'
import Discrepancies from './pages/Discrepancies'
import Alerts from './pages/Alerts'
import Renewals from './pages/Renewals'
import Releases from './pages/Releases'
import Reports from './pages/Reports'
import AuditTrail from './pages/AuditTrail'
import Admin from './pages/Admin'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

function ProtectedLayout() {
  const { user } = useAuth()

  if (!user && !localStorage.getItem('token')) {
    return <Navigate to="/login" replace />
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#0f172a' }}>
      <Sidebar />
      <div className="main-content" style={{ flex: 1 }}>
        <main className="page-body">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/deposits" element={<Deposits />} />
            <Route path="/fdrs" element={<FDRList />} />
            <Route path="/fdrs/:id" element={<FDRDetail />} />
            <Route path="/review" element={<ReviewQueue />} />
            <Route path="/verification" element={<BankVerification />} />
            <Route path="/discrepancies" element={<Discrepancies />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/renewals" element={<Renewals />} />
            <Route path="/releases" element={<Releases />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/audit" element={<AuditTrail />} />
            <Route path="/admin" element={<Admin />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/*" element={<ProtectedLayout />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}
