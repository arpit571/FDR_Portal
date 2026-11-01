import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getDeposits, getInstitutions, createDeposit } from '../api/client'
import { useAuth } from '../app/AuthContext'
import { StatusBadge, EmptyState, Spinner } from '../components/UI'
import { Landmark, Plus, Search, CheckCircle, AlertTriangle, X } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function Deposits() {
  const qc = useQueryClient()
  const { isFinance, isAdmin } = useAuth()
  const [search, setSearch] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState({
    institution_id: '',
    programme: 'Engineering & Technology',
    education_level: 'UG',
    required_amount: 3500000,
    academic_year: '2024-2027',
  })
  const [error, setError] = useState('')

  const { data: deposits = [], isLoading } = useQuery({
    queryKey: ['deposits'],
    queryFn: getDeposits,
  })

  const { data: institutions = [] } = useQuery({
    queryKey: ['institutions'],
    queryFn: getInstitutions,
    enabled: showModal,
  })

  const createMut = useMutation({
    mutationFn: createDeposit,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['deposits'] })
      setShowModal(false)
      setError('')
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to create deposit.')
    }
  })

  const filtered = deposits.filter((d: any) =>
    !search ||
    d.institution_name?.toLowerCase().includes(search.toLowerCase()) ||
    d.programme?.toLowerCase().includes(search.toLowerCase()) ||
    d.deposit_ref?.toLowerCase().includes(search.toLowerCase())
  )

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.institution_id) {
      setError('Please select an institution')
      return
    }
    createMut.mutate(form)
  }

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>AICTE Security Deposits</h2>
          <p>Institutional security deposit compliance, FDR coverage, and regulatory shortfall tracking.</p>
        </div>
        {(isFinance || isAdmin) && (
          <button className="btn btn-primary" onClick={() => setShowModal(true)}>
            <Plus size={16} /> New Security Deposit
          </button>
        )}
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search size={16} style={{ position: 'absolute', left: 12, top: 12, color: '#64748b' }} />
            <input
              type="text"
              placeholder="Search deposits by institution, programme, or reference..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input"
              style={{ paddingLeft: 38 }}
            />
          </div>
        </div>
      </div>

      {isLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><Spinner size={32} /></div>
      ) : filtered.length === 0 ? (
        <EmptyState icon="🏛️" title="No deposits found" desc="Create a deposit record or adjust search criteria." />
      ) : (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Reference</th>
                <th>Institution</th>
                <th>Programme / Level</th>
                <th>Required (₹)</th>
                <th>FDR Covered (₹)</th>
                <th>Shortfall Status</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((d: any) => {
                const totalFdr = d.total_fdr_principal || 0
                const required = d.required_amount || 0
                const shortfall = Math.max(0, required - totalFdr)
                const isFullyCovered = shortfall === 0

                return (
                  <tr key={d.id}>
                    <td>
                      <span style={{ fontWeight: 600, color: '#e2e8f0' }}>{d.deposit_ref || `DEP-${d.id.slice(0, 8)}`}</span>
                    </td>
                    <td>
                      <div style={{ fontWeight: 600, color: '#f1f5f9' }}>{d.institution_name}</div>
                      <div style={{ fontSize: 11, color: '#64748b' }}>{d.institution_code}</div>
                    </td>
                    <td>
                      <div>{d.programme}</div>
                      <div style={{ fontSize: 11, color: '#64748b' }}>Level: {d.education_level}</div>
                    </td>
                    <td>
                      <span style={{ fontWeight: 600 }}>₹{(required / 100000).toFixed(1)}L</span>
                    </td>
                    <td>
                      <span style={{ fontWeight: 600, color: isFullyCovered ? '#4ade80' : '#f59e0b' }}>
                        ₹{(totalFdr / 100000).toFixed(1)}L
                      </span>
                    </td>
                    <td>
                      {isFullyCovered ? (
                        <span className="badge active" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                          <CheckCircle size={12} /> Compliant
                        </span>
                      ) : (
                        <span className="badge high" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                          <AlertTriangle size={12} /> Shortfall: ₹{(shortfall / 100000).toFixed(1)}L
                        </span>
                      )}
                    </td>
                    <td>
                      <StatusBadge status={d.status || 'Active'} />
                    </td>
                    <td>
                      <Link to="/fdrs" className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: 12 }}>
                        View FDRs
                      </Link>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal: New Deposit */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 520 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ fontSize: 18, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
                <Landmark size={20} color="#6366f1" /> Create AICTE Security Deposit
              </h3>
              <button className="btn btn-ghost" onClick={() => setShowModal(false)}><X size={18} /></button>
            </div>

            {error && (
              <div style={{ padding: '10px 14px', background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 8, color: '#f87171', marginBottom: 16, fontSize: 13 }}>
                {error}
              </div>
            )}

            <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label className="label">Institution</label>
                <select
                  className="input"
                  value={form.institution_id}
                  onChange={(e) => setForm({ ...form, institution_id: e.target.value })}
                  required
                >
                  <option value="">Select Institution...</option>
                  {institutions.map((inst: any) => (
                    <option key={inst.id} value={inst.id}>
                      {inst.name} ({inst.code})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="label">Programme</label>
                <select
                  className="input"
                  value={form.programme}
                  onChange={(e) => {
                    const prog = e.target.value
                    let req = 3500000
                    if (form.education_level === 'Diploma') req = 1500000
                    else if (prog === 'Management' || prog === 'Computer Applications') req = 500000
                    setForm({ ...form, programme: prog, required_amount: req })
                  }}
                >
                  <option value="Engineering & Technology">Engineering & Technology</option>
                  <option value="Management">Management</option>
                  <option value="Computer Applications">Computer Applications</option>
                  <option value="Planning">Planning</option>
                  <option value="Applied Arts & Crafts">Applied Arts & Crafts</option>
                  <option value="Design">Design</option>
                  <option value="Hotel Management & Catering">Hotel Management & Catering</option>
                </select>
              </div>

              <div>
                <label className="label">Education Level</label>
                <select
                  className="input"
                  value={form.education_level}
                  onChange={(e) => {
                    const lvl = e.target.value
                    let req = 3500000
                    if (lvl === 'Diploma') req = 1500000
                    else if (lvl === 'PG') req = 1500000
                    else if (form.programme === 'Management' || form.programme === 'Computer Applications') req = 500000
                    setForm({ ...form, education_level: lvl, required_amount: req })
                  }}
                >
                  <option value="UG">UG (Undergraduate)</option>
                  <option value="PG">PG (Postgraduate)</option>
                  <option value="Diploma">Diploma</option>
                </select>
              </div>

              <div>
                <label className="label">Required Amount (₹)</label>
                <input
                  type="number"
                  className="input"
                  value={form.required_amount}
                  onChange={(e) => setForm({ ...form, required_amount: Number(e.target.value) })}
                  required
                />
                <span style={{ fontSize: 11, color: '#64748b' }}>
                  Per AICTE APH 2024–2027 Table 1.4: ₹{(form.required_amount / 100000).toFixed(1)} Lakhs
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 10 }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={createMut.isPending}>
                  {createMut.isPending ? 'Creating...' : 'Create Deposit'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

