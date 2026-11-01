import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../app/AuthContext'
import { login as apiLogin } from '../api/client'
import { Shield, FileText, Lock, Zap } from 'lucide-react'

const DEMO_ACCOUNTS = [
  { label: 'Super Admin', email: 'superadmin@demo.in', role: 'SUPER_ADMIN', color: '#8b5cf6' },
  { label: 'Finance Officer', email: 'finance@inst001.demo.in', role: 'FINANCE_OFFICER', color: '#3b82f6' },
  { label: 'Institution Reviewer', email: 'reviewer@inst001.demo.in', role: 'REVIEWER', color: '#0ea5e9' },
  { label: 'AICTE Officer', email: 'aicte@demo.in', role: 'AICTE_OFFICER', color: '#f59e0b' },
  { label: 'Auditor', email: 'auditor@demo.in', role: 'AUDITOR', color: '#22c55e' },
]

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleLogin = async (e?: React.FormEvent, demoEmail?: string) => {
    e?.preventDefault()
    const em = demoEmail || email
    const pw = demoEmail ? 'Demo@123' : password
    setLoading(true)
    setError('')
    try {
      const data = await apiLogin(em, pw)
      login(data.access_token, data.user)
      navigate('/')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed. Check credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div style={{ width: '100%', maxWidth: 900, display: 'flex', gap: 48, alignItems: 'center', padding: '0 24px' }}>
        {/* Left hero */}
        <div style={{ flex: 1, display: 'none' }}>
          {/* hidden on small */}
        </div>

        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 24 }}>
          {/* Header */}
          <div style={{ textAlign: 'center', marginBottom: 8 }}>
            <div style={{
              width: 56, height: 56, borderRadius: 14,
              background: 'linear-gradient(135deg, #1e40af, #6366f1)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 16px',
              boxShadow: '0 8px 24px rgba(99,102,241,0.35)'
            }}>
              <Shield size={28} color="white" />
            </div>
            <h1 style={{ fontSize: 24, fontWeight: 800, color: '#f1f5f9', marginBottom: 6 }}>
              FDR SmartTrack Portal
            </h1>
            <p style={{ fontSize: 13, color: '#64748b' }}>
              AICTE Security Deposit / FDR Management — SIH 26265
            </p>
          </div>

          {/* Login card */}
          <div className="login-card">
            <form onSubmit={handleLogin}>
              {error && (
                <div className="alert-banner danger" style={{ marginBottom: 20 }}>
                  <Lock size={16} style={{ flexShrink: 0 }} />
                  <span>{error}</span>
                </div>
              )}

              <div className="form-group">
                <label className="form-label">Email Address</label>
                <input
                  className="form-control"
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="you@institution.in"
                  autoComplete="email"
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Password</label>
                <input
                  className="form-control"
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  required
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                style={{ width: '100%', justifyContent: 'center', marginBottom: 16 }}
                disabled={loading}
              >
                {loading ? <span className="spinner" style={{ width: 16, height: 16 }} /> : null}
                {loading ? 'Signing in…' : 'Sign In'}
              </button>
            </form>

            {/* Demo accounts */}
            <div>
              <div style={{
                display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14,
              }}>
                <div style={{ flex: 1, height: 1, background: 'rgba(255,255,255,0.06)' }} />
                <span style={{ fontSize: 11, color: '#475569', fontWeight: 600 }}>
                  DEMO ACCOUNTS
                </span>
                <div style={{ flex: 1, height: 1, background: 'rgba(255,255,255,0.06)' }} />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {DEMO_ACCOUNTS.map(acc => (
                  <button
                    key={acc.email}
                    onClick={() => handleLogin(undefined, acc.email)}
                    disabled={loading}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 10,
                      background: 'rgba(255,255,255,0.03)',
                      border: '1px solid rgba(255,255,255,0.07)',
                      borderRadius: 8, padding: '9px 12px',
                      cursor: 'pointer', transition: 'all 0.15s',
                      color: '#cbd5e1', fontSize: 13,
                    }}
                    onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.07)')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.03)')}
                  >
                    <Zap size={14} color={acc.color} />
                    <span style={{ flex: 1, textAlign: 'left' }}>
                      <strong style={{ color: '#e2e8f0' }}>{acc.label}</strong>
                    </span>
                    <span style={{ fontSize: 11, color: '#475569' }}>{acc.email}</span>
                  </button>
                ))}
              </div>

              <p style={{ textAlign: 'center', fontSize: 11, color: '#334155', marginTop: 12 }}>
                Password for all demo accounts: <span style={{ color: '#60a5fa', fontWeight: 700 }}>Demo@123</span>
              </p>
            </div>
          </div>

          <p style={{ textAlign: 'center', fontSize: 11, color: '#334155' }}>
            <FileText size={12} style={{ display: 'inline', marginRight: 4 }} />
            All data is fictional DEMO DATA. Not for production use.
          </p>
        </div>
      </div>
    </div>
  )
}
