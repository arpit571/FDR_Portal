import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getAlerts, acknowledgeAlert, runScheduler } from '../api/client'
import { useAuth } from '../app/AuthContext'
import { EmptyState, Spinner } from '../components/UI'
import { CheckCircle, Clock, Zap, Search } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function Alerts() {
  const qc = useQueryClient()
  const { isAICTE, isAdmin } = useAuth()
  const [filter, setFilter] = useState<'all' | 'pending' | 'acknowledged'>('all')
  const [search, setSearch] = useState('')

  const { data: alerts = [], isLoading } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => getAlerts(),
  })

  const ackMut = useMutation({
    mutationFn: (id: string) => acknowledgeAlert(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alerts'] })
    }
  })

  const runSchedMut = useMutation({
    mutationFn: runScheduler,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alerts'] })
    }
  })

  const filtered = alerts.filter((a: any) => {
    if (filter === 'pending' && a.acknowledged) return false
    if (filter === 'acknowledged' && !a.acknowledged) return false
    if (search) {
      const q = search.toLowerCase()
      return (
        a.fdr_number?.toLowerCase().includes(q) ||
        a.institution_name?.toLowerCase().includes(q) ||
        a.alert_type?.toLowerCase().includes(q)
      )
    }
    return true
  })

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>Maturity Alert Notifications</h2>
          <p>Automated reminders scheduled at 90, 30, 15, and 7 days prior to FDR maturity.</p>
        </div>
        {(isAICTE || isAdmin) && (
          <button
            className="btn btn-secondary"
            onClick={() => runSchedMut.mutate()}
            disabled={runSchedMut.isPending}
          >
            <Zap size={15} color="#eab308" />
            {runSchedMut.isPending ? 'Running Engine...' : 'Run Maturity Evaluator'}
          </button>
        )}
      </div>

      {/* Filter bar */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ position: 'relative', flex: 1, minWidth: 240 }}>
            <Search size={16} style={{ position: 'absolute', left: 12, top: 12, color: '#64748b' }} />
            <input
              type="text"
              placeholder="Search alerts by FDR number, institution, or alert type..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input"
              style={{ paddingLeft: 38 }}
            />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {(['all', 'pending', 'acknowledged'] as const).map((t) => (
              <button
                key={t}
                className={`btn ${filter === t ? 'btn-primary' : 'btn-secondary'}`}
                style={{ textTransform: 'capitalize', padding: '6px 14px' }}
                onClick={() => setFilter(t)}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      </div>

      {isLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><Spinner size={32} /></div>
      ) : filtered.length === 0 ? (
        <EmptyState icon="🔔" title="No alerts found" desc="No maturity notifications match your current filter." />
      ) : (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Alert Stage</th>
                <th>FDR Number</th>
                <th>Institution</th>
                <th>Maturity Date</th>
                <th>Channel / Escalation</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((a: any) => (
                <tr key={a.id}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div
                        style={{
                          width: 8, height: 8, borderRadius: '50%',
                          background: a.escalated ? '#ef4444' : '#f59e0b'
                        }}
                        className={a.escalated ? 'pulse-red' : ''}
                      />
                      <span style={{ fontWeight: 600, color: '#f1f5f9' }}>
                        {a.alert_type?.replace(/_/g, ' ')}
                      </span>
                    </div>
                  </td>
                  <td>
                    <Link to={`/fdrs/${a.fdr_id}`} style={{ fontWeight: 600, color: '#6366f1', textDecoration: 'none' }}>
                      {a.fdr_number}
                    </Link>
                  </td>
                  <td>
                    <div style={{ fontWeight: 500, color: '#e2e8f0' }}>{a.institution_name}</div>
                  </td>
                  <td>
                    <span style={{ color: '#cbd5e1' }}>{a.maturity_date}</span>
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                      <span className="badge" style={{ background: 'rgba(255,255,255,0.06)', color: '#94a3b8' }}>
                        In-App
                      </span>
                      {a.escalated && (
                        <span className="badge high" style={{ fontSize: 11 }}>
                          ESCALATED
                        </span>
                      )}
                    </div>
                  </td>
                  <td>
                    {a.acknowledged ? (
                      <span className="badge active" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                        <CheckCircle size={12} /> Acknowledged
                      </span>
                    ) : (
                      <span className="badge high" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                        <Clock size={12} /> Action Required
                      </span>
                    )}
                  </td>
                  <td>
                    {!a.acknowledged ? (
                      <button
                        className="btn btn-primary"
                        style={{ padding: '4px 10px', fontSize: 12 }}
                        onClick={() => ackMut.mutate(a.id)}
                        disabled={ackMut.isPending}
                      >
                        Acknowledge
                      </button>
                    ) : (
                      <span style={{ fontSize: 12, color: '#64748b' }}>Done</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
