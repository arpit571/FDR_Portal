import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  setDemoClock, runScheduler, getUsers, createUser,
  getBanks, createBank, updateBank, getRegulatoryRules
} from '../api/client'
import { Clock, Users, Landmark, Scale, Plus, Check, RefreshCw, Zap } from 'lucide-react'

export default function Admin() {
  const qc = useQueryClient()
  const [activeTab, setActiveTab] = useState<'clock' | 'users' | 'banks' | 'rules'>('clock')
  const [customDate, setCustomDate] = useState('2026-11-15')
  const [msg, setMsg] = useState({ type: '', text: '' })

  // New bank form
  const [bankForm, setBankForm] = useState({ name: '', ifsc_prefix: '', bank_type: 'Public', approved: true })
  // New user form
  const [userForm, setUserForm] = useState({ name: '', email: '', password: 'Demo@123', roles: ['REVIEWER'] })

  const { data: users = [] } = useQuery({
    queryKey: ['admin-users'],
    queryFn: getUsers,
    enabled: activeTab === 'users',
  })

  const { data: banks = [] } = useQuery({
    queryKey: ['admin-banks'],
    queryFn: getBanks,
    enabled: activeTab === 'banks',
  })

  const { data: rules = [] } = useQuery({
    queryKey: ['admin-rules'],
    queryFn: () => getRegulatoryRules(),
    enabled: activeTab === 'rules',
  })

  const clockMut = useMutation({
    mutationFn: setDemoClock,
    onSuccess: (data: any) => {
      qc.invalidateQueries()
      setMsg({ type: 'success', text: `Demo clock set to ${data.demo_date}. Scheduler jobs re-evaluated!` })
      setTimeout(() => setMsg({ type: '', text: '' }), 4000)
    }
  })

  const schedMut = useMutation({
    mutationFn: runScheduler,
    onSuccess: () => {
      qc.invalidateQueries()
      setMsg({ type: 'success', text: 'All background scheduler jobs executed manually.' })
      setTimeout(() => setMsg({ type: '', text: '' }), 4000)
    }
  })

  const bankMut = useMutation({
    mutationFn: createBank,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-banks'] })
      setBankForm({ name: '', ifsc_prefix: '', bank_type: 'Public', approved: true })
      setMsg({ type: 'success', text: 'Bank added to registry.' })
      setTimeout(() => setMsg({ type: '', text: '' }), 4000)
    }
  })

  const toggleBankMut = useMutation({
    mutationFn: ({ id, approved }: { id: string; approved: boolean }) =>
      updateBank(id, { approved }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-banks'] })
    }
  })

  const userMut = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-users'] })
      setUserForm({ name: '', email: '', password: 'Demo@123', roles: ['REVIEWER'] })
      setMsg({ type: 'success', text: 'User created successfully.' })
      setTimeout(() => setMsg({ type: '', text: '' }), 4000)
    }
  })

  return (
    <div>
      <div className="page-header">
        <h2>System Administration & Governance</h2>
        <p>Configure demo simulation clock, approved bank whitelists, user RBAC, and APH regulatory thresholds.</p>
      </div>

      {msg.text && (
        <div style={{
          padding: '10px 16px',
          background: msg.type === 'success' ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
          border: `1px solid ${msg.type === 'success' ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)'}`,
          borderRadius: 8,
          color: msg.type === 'success' ? '#4ade80' : '#f87171',
          marginBottom: 16,
          fontSize: 13,
          display: 'flex',
          alignItems: 'center',
          gap: 8
        }}>
          <Check size={16} /> {msg.text}
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: 12 }}>
        <button
          className={`btn ${activeTab === 'clock' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('clock')}
        >
          <Clock size={15} /> Demo Time Machine
        </button>
        <button
          className={`btn ${activeTab === 'banks' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('banks')}
        >
          <Landmark size={15} /> Bank Whitelist
        </button>
        <button
          className={`btn ${activeTab === 'rules' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('rules')}
        >
          <Scale size={15} /> APH Regulatory Rules
        </button>
        <button
          className={`btn ${activeTab === 'users' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('users')}
        >
          <Users size={15} /> User Management
        </button>
      </div>

      {/* Tab: Clock */}
      {activeTab === 'clock' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 20 }}>
          <div className="card">
            <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Clock size={18} color="#eab308" /> Fast-Forward Simulation Clock
            </h3>
            <p style={{ fontSize: 13, color: '#94a3b8', marginBottom: 16 }}>
              Simulate time passing to test 90, 30, 15, and 7-day maturity alerts, escalation flags, and matured status transitions.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ display: 'flex', gap: 8 }}>
                {[7, 15, 30, 60, 90].map((d) => (
                  <button
                    key={d}
                    className="btn btn-secondary"
                    style={{ flex: 1, fontSize: 12 }}
                    onClick={() => clockMut.mutate({ advance_days: d })}
                    disabled={clockMut.isPending}
                  >
                    +{d}d
                  </button>
                ))}
              </div>

              <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                <input
                  type="date"
                  className="input"
                  value={customDate}
                  onChange={(e) => setCustomDate(e.target.value)}
                />
                <button
                  className="btn btn-primary"
                  onClick={() => clockMut.mutate({ set_date: customDate })}
                  disabled={clockMut.isPending}
                >
                  Set Date
                </button>
              </div>
            </div>
          </div>

          <div className="card">
            <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Zap size={18} color="#6366f1" /> Background Job Scheduler
            </h3>
            <p style={{ fontSize: 13, color: '#94a3b8', marginBottom: 16 }}>
              Manually trigger background scheduled tasks: maturity alert dispatcher, alert escalation engine, and compliance discrepancy rule evaluator.
            </p>
            <button
              className="btn btn-primary"
              style={{ width: '100%' }}
              onClick={() => schedMut.mutate()}
              disabled={schedMut.isPending}
            >
              <RefreshCw size={15} /> Run All Background Jobs Now
            </button>
          </div>
        </div>
      )}

      {/* Tab: Banks */}
      {activeTab === 'banks' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div className="card">
            <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 14 }}>Register Approved Scheduled Bank</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr auto', gap: 12, alignItems: 'flex-end' }}>
              <div>
                <label className="label">Bank Name</label>
                <input
                  type="text"
                  className="input"
                  placeholder="e.g. Bank of Maharashtra"
                  value={bankForm.name}
                  onChange={(e) => setBankForm({ ...bankForm, name: e.target.value })}
                />
              </div>
              <div>
                <label className="label">IFSC Prefix</label>
                <input
                  type="text"
                  className="input"
                  placeholder="e.g. MAHB"
                  value={bankForm.ifsc_prefix}
                  onChange={(e) => setBankForm({ ...bankForm, ifsc_prefix: e.target.value })}
                />
              </div>
              <div>
                <label className="label">Type</label>
                <select
                  className="input"
                  value={bankForm.bank_type}
                  onChange={(e) => setBankForm({ ...bankForm, bank_type: e.target.value })}
                >
                  <option value="Public">Public Sector</option>
                  <option value="Private">Private Sector</option>
                  <option value="Co-operative">Co-operative</option>
                </select>
              </div>
              <button
                className="btn btn-primary"
                onClick={() => bankMut.mutate(bankForm)}
                disabled={!bankForm.name || bankMut.isPending}
              >
                <Plus size={16} /> Add Bank
              </button>
            </div>
          </div>

          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Bank Name</th>
                  <th>IFSC Prefix</th>
                  <th>Classification</th>
                  <th>AICTE Whitelist Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {banks.map((b: any) => (
                  <tr key={b.id}>
                    <td>
                      <span style={{ fontWeight: 600, color: '#f1f5f9' }}>{b.name}</span>
                    </td>
                    <td><code>{b.ifsc_prefix || '—'}</code></td>
                    <td>{b.bank_type || 'Scheduled'}</td>
                    <td>
                      <span className={`badge ${b.approved ? 'active' : 'high'}`}>
                        {b.approved ? 'Approved Whitelist' : 'Unapproved / Prohibited'}
                      </span>
                    </td>
                    <td>
                      <button
                        className="btn btn-secondary"
                        style={{ padding: '4px 10px', fontSize: 12 }}
                        onClick={() => toggleBankMut.mutate({ id: b.id, approved: !b.approved })}
                      >
                        {b.approved ? 'Revoke Approval' : 'Approve'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab: Rules */}
      {activeTab === 'rules' && (
        <div>
          <div className="card" style={{ marginBottom: 16 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>AICTE Approval Process Handbook (APH) Table 1.4 Rules</h3>
            <p style={{ fontSize: 13, color: '#94a3b8' }}>
              Minimum security deposit amounts required by programme and academic level. Hardcoded amounts are avoided; rules are editable per academic year.
            </p>
          </div>
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Academic Year</th>
                  <th>Programme</th>
                  <th>Level</th>
                  <th>Required Amount</th>
                  <th>Min Tenure (Years)</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((r: any) => (
                  <tr key={r.id}>
                    <td>{r.academic_year}</td>
                    <td style={{ fontWeight: 600, color: '#f1f5f9' }}>{r.programme}</td>
                    <td>{r.level}</td>
                    <td style={{ color: '#4ade80', fontWeight: 600 }}>₹{(r.amount / 100000).toFixed(1)} Lakhs</td>
                    <td>{r.tenure_years || 10} Years</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab: Users */}
      {activeTab === 'users' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div className="card">
            <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 14 }}>Create System User</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1.5fr 1fr auto', gap: 12, alignItems: 'flex-end' }}>
              <div>
                <label className="label">Full Name</label>
                <input
                  type="text"
                  className="input"
                  value={userForm.name}
                  onChange={(e) => setUserForm({ ...userForm, name: e.target.value })}
                  placeholder="Officer name"
                />
              </div>
              <div>
                <label className="label">Email Address</label>
                <input
                  type="email"
                  className="input"
                  value={userForm.email}
                  onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
                  placeholder="officer@aicte.gov.in"
                />
              </div>
              <div>
                <label className="label">Role</label>
                <select
                  className="input"
                  value={userForm.roles[0]}
                  onChange={(e) => setUserForm({ ...userForm, roles: [e.target.value] })}
                >
                  <option value="AICTE_OFFICER">AICTE Officer</option>
                  <option value="REVIEWER">Reviewer</option>
                  <option value="FINANCE_OFFICER">Finance Officer</option>
                  <option value="AUDITOR">Auditor</option>
                  <option value="SUPER_ADMIN">Super Admin</option>
                </select>
              </div>
              <button
                className="btn btn-primary"
                onClick={() => userMut.mutate(userForm)}
                disabled={!userForm.name || !userForm.email || userMut.isPending}
              >
                <Plus size={16} /> Create User
              </button>
            </div>
          </div>

          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Roles</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u: any) => (
                  <tr key={u.id}>
                    <td>
                      <span style={{ fontWeight: 600, color: '#f1f5f9' }}>{u.name}</span>
                    </td>
                    <td>{u.email}</td>
                    <td>
                      <div style={{ display: 'flex', gap: 6 }}>
                        {u.roles?.map((r: string) => (
                          <span key={r} className="badge" style={{ background: 'rgba(99,102,241,0.15)', color: '#818cf8' }}>
                            {r.replace('_', ' ')}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td>
                      <span className={`badge ${u.active ? 'active' : 'high'}`}>
                        {u.active ? 'Active' : 'Disabled'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
