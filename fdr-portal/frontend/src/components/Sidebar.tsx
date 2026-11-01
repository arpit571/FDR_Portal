import React from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../app/AuthContext'
import {
  LayoutDashboard, CreditCard, AlertTriangle,
  ShieldCheck, RotateCcw, Unlock, BarChart3, ClipboardList,
  Settings, LogOut, Landmark, Bell, Eye
} from 'lucide-react'

interface NavItem {
  to: string
  icon: React.ReactNode
  label: string
  roles?: string[]
}

const NAV_ITEMS: NavItem[] = [
  { to: '/', icon: <LayoutDashboard size={17} />, label: 'Dashboard' },
  { to: '/deposits', icon: <Landmark size={17} />, label: 'Deposits' },
  { to: '/fdrs', icon: <CreditCard size={17} />, label: 'FDR Records' },
  { to: '/review', icon: <Eye size={17} />, label: 'Review Queue' },
  { to: '/verification', icon: <ShieldCheck size={17} />, label: 'Bank Verification' },
  { to: '/discrepancies', icon: <AlertTriangle size={17} />, label: 'Discrepancies' },
  { to: '/alerts', icon: <Bell size={17} />, label: 'Alerts' },
  { to: '/renewals', icon: <RotateCcw size={17} />, label: 'Renewals' },
  { to: '/releases', icon: <Unlock size={17} />, label: 'Releases' },
  { to: '/reports', icon: <BarChart3 size={17} />, label: 'Reports' },
  { to: '/audit', icon: <ClipboardList size={17} />, label: 'Audit Trail' },
  { to: '/admin', icon: <Settings size={17} />, label: 'Admin', roles: ['SUPER_ADMIN'] },
]

export default function Sidebar() {
  const { user, logout, hasRole } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const initials = user?.name?.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() || 'U'
  const roleLabel = user?.roles?.[0]?.replace('_', ' ') || 'User'

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <h1>🏛 FDR SmartTrack</h1>
        <p>AICTE Regulation Bureau</p>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section-label">Navigation</div>
        {NAV_ITEMS.map(item => {
          if (item.roles && !hasRole(...item.roles)) return null
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          )
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="user-pill">
          <div className="user-avatar">{initials}</div>
          <div className="user-info">
            <div className="user-name truncate">{user?.name}</div>
            <div className="user-role">{roleLabel}</div>
          </div>
          <button
            onClick={handleLogout}
            title="Sign out"
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: '#475569', padding: 4, borderRadius: 4
            }}
            onMouseEnter={e => (e.currentTarget.style.color = '#f87171')}
            onMouseLeave={e => (e.currentTarget.style.color = '#475569')}
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </aside>
  )
}
