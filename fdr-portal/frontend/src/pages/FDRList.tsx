import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getFDRs } from '../api/client'
import { StatusBadge, Currency, EmptyState, Spinner } from '../components/UI'
import { Plus, Search, RefreshCw } from 'lucide-react'

export default function FDRList() {
  const qc = useQueryClient()
  const [statusFilter, setStatusFilter] = useState('')
  const [search, setSearch] = useState('')

  const { data: fdrs = [], isLoading } = useQuery({
    queryKey: ['fdrs', statusFilter],
    queryFn: () => getFDRs(statusFilter ? { status: statusFilter } : {}),
    refetchInterval: 30000,
  })

  const filtered = fdrs.filter((f: any) =>
    !search || f.fdr_number?.toLowerCase().includes(search.toLowerCase()) ||
    f.bank_name?.toLowerCase().includes(search.toLowerCase())
  )

  const daysLeft = (d: string) => {
    const diff = Math.round((new Date(d).getTime() - Date.now()) / 86400000)
    return diff
  }

  const daysColor = (d: number) =>
    d < 0 ? '#f87171' : d <= 7 ? '#f87171' : d <= 30 ? '#fbbf24' : '#4ade80'

  return (
    <div className="fade-in">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div className="page-header" style={{ marginBottom: 0 }}>
          <h2>FDR Records</h2>
          <p>{filtered.length} instruments</p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <Link to="/fdrs/new" className="btn btn-primary btn-sm">
            <Plus size={15} /> New FDR
          </Link>
        </div>
      </div>

      {/* Filters */}
      <div className="card" style={{ padding: '14px 16px', marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ position: 'relative', flex: 1, minWidth: 200 }}>
            <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: '#475569' }} />
            <input
              className="form-control"
              style={{ paddingLeft: 32 }}
              placeholder="Search FDR number or bank…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>

          <select
            className="form-control"
            style={{ width: 180 }}
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
          >
            <option value="">All Statuses</option>
            {['Draft', 'Pending Document', 'Pending Review', 'Active', 'Maturity Alert',
              'Matured - Action Pending', 'Renewed', 'Replaced', 'Released', 'Closed'].map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          <button className="btn btn-secondary btn-sm" onClick={() => qc.invalidateQueries({ queryKey: ['fdrs'] })}>
            <RefreshCw size={13} />
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="card" style={{ padding: 0 }}>
        {isLoading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
            <Spinner size={28} />
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState icon="🗂" title="No FDRs found" desc="Add a new FDR or adjust your filters." />
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>FDR Number</th>
                  <th>Bank</th>
                  <th>Principal</th>
                  <th>Rate</th>
                  <th>Maturity Date</th>
                  <th>Days Left</th>
                  <th>Status</th>
                  <th>Kind</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((f: any) => {
                  const dl = daysLeft(f.maturity_date)
                  return (
                    <tr key={f.id}>
                      <td>
                        <span style={{ fontFamily: 'monospace', fontSize: 12.5, color: '#93c5fd' }}>
                          {f.fdr_number}
                        </span>
                      </td>
                      <td>{f.bank_name}</td>
                      <td><Currency amount={f.principal} /></td>
                      <td>{f.rate ? `${f.rate}%` : '—'}</td>
                      <td style={{ fontVariantNumeric: 'tabular-nums' }}>{f.maturity_date}</td>
                      <td>
                        <span style={{ fontWeight: 700, color: daysColor(dl), fontSize: 13 }}>
                          {dl < 0 ? `${Math.abs(dl)}d overdue` : `${dl}d`}
                        </span>
                      </td>
                      <td><StatusBadge status={f.status} /></td>
                      <td>
                        <span style={{ fontSize: 11, color: '#64748b', background: 'rgba(255,255,255,0.05)', borderRadius: 4, padding: '2px 6px' }}>
                          {f.kind}
                        </span>
                      </td>
                      <td>
                        <Link
                          to={`/fdrs/${f.id}`}
                          className="btn btn-secondary btn-sm"
                        >
                          View →
                        </Link>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
