import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getDiscrepancies, resolveCase, waiveCase, getRules, updateRule } from '../api/client'
import { useAuth } from '../app/AuthContext'
import { StatusBadge, SeverityBadge, EmptyState, Spinner } from '../components/UI'
import { AlertTriangle, CheckCircle, Settings } from 'lucide-react'

export default function Discrepancies() {
  const qc = useQueryClient()
  const { isAICTE, isAdmin } = useAuth()
  const [statusFilter, setStatusFilter] = useState('Open')
  const [sevFilter, setSevFilter] = useState('')
  const [resolveNote, setResolveNote] = useState<Record<string, string>>({})
  const [activeTab, setActiveTab] = useState<'cases' | 'rules'>('cases')

  const { data: cases = [], isLoading } = useQuery({
    queryKey: ['discrepancies', statusFilter, sevFilter],
    queryFn: () => getDiscrepancies({ status: statusFilter || undefined, severity: sevFilter || undefined }),
  })

  const { data: rules = [] } = useQuery({
    queryKey: ['rules'], queryFn: getRules,
  })

  const resolveMutation = useMutation({
    mutationFn: ({ id, note }: { id: string; note: string }) => resolveCase(id, note),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['discrepancies'] }),
  })

  const waiveMutation = useMutation({
    mutationFn: ({ id, note }: { id: string; note: string }) => waiveCase(id, note),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['discrepancies'] }),
  })

  const toggleRuleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => updateRule(id, { enabled }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rules'] }),
  })

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Discrepancies</h2>
        <p>Rule-based discrepancy cases — R01 through R15</p>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid rgba(255,255,255,0.06)', marginBottom: 20 }}>
        {[
          { key: 'cases', label: 'Cases', icon: <AlertTriangle size={14} /> },
          { key: 'rules', label: 'Rule Registry', icon: <Settings size={14} /> },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            style={{
              padding: '10px 18px', background: 'none', border: 'none', cursor: 'pointer',
              fontSize: 13.5, fontWeight: 600,
              color: activeTab === tab.key ? '#93c5fd' : '#64748b',
              borderBottom: activeTab === tab.key ? '2px solid #3b82f6' : '2px solid transparent',
              display: 'flex', alignItems: 'center', gap: 6,
            }}
          >
            {tab.icon}{tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'cases' && (
        <>
          {/* Filters */}
          <div className="card" style={{ padding: '12px 16px', marginBottom: 16 }}>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <select className="form-control" style={{ width: 160 }} value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
                <option value="">All Statuses</option>
                {['Open', 'Under Review', 'Resolved', 'Waived'].map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
              <select className="form-control" style={{ width: 160 }} value={sevFilter} onChange={e => setSevFilter(e.target.value)}>
                <option value="">All Severities</option>
                {['Critical', 'High', 'Medium', 'Low'].map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="card" style={{ padding: 0 }}>
            {isLoading ? (
              <div style={{ padding: 60, textAlign: 'center' }}><Spinner size={28} /></div>
            ) : cases.length === 0 ? (
              <EmptyState icon="✅" title="No cases found" desc="All clear for selected filters." />
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Rule</th>
                    <th>FDR</th>
                    <th>Severity</th>
                    <th>Status</th>
                    <th>Message</th>
                    <th>Opened</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {cases.map((c: any) => (
                    <tr key={c.id}>
                      <td>
                        <span style={{ fontFamily: 'monospace', fontWeight: 700, color: '#93c5fd', fontSize: 12 }}>
                          {c.rule_code}
                        </span>
                        {c.rule_source && (
                          <div style={{ fontSize: 10.5, color: '#475569', marginTop: 2 }}>
                            {c.rule_source}
                          </div>
                        )}
                      </td>
                      <td>
                        <a href={`/fdrs/${c.fdr_id}`} style={{ color: '#93c5fd', fontSize: 12, fontFamily: 'monospace' }}>
                          {c.fdr_id.substring(0, 8)}…
                        </a>
                      </td>
                      <td><SeverityBadge severity={c.severity} /></td>
                      <td><StatusBadge status={c.status} /></td>
                      <td style={{ fontSize: 12.5, maxWidth: 280, color: '#cbd5e1' }}>{c.message}</td>
                      <td style={{ fontSize: 12, color: '#64748b' }}>{c.opened_at?.substring(0, 10)}</td>
                      <td>
                        {['Open', 'Under Review'].includes(c.status) && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                            <input
                              className="form-control"
                              style={{ fontSize: 11, padding: '4px 8px' }}
                              placeholder="Resolution note…"
                              value={resolveNote[c.id] || ''}
                              onChange={e => setResolveNote(n => ({ ...n, [c.id]: e.target.value }))}
                            />
                            <div style={{ display: 'flex', gap: 6 }}>
                              <button
                                className="btn btn-success btn-sm"
                                onClick={() => resolveMutation.mutate({ id: c.id, note: resolveNote[c.id] || 'Resolved' })}
                                disabled={resolveMutation.isPending}
                              >
                                <CheckCircle size={12} /> Resolve
                              </button>
                              {(isAICTE || isAdmin) && (
                                <button
                                  className="btn btn-secondary btn-sm"
                                  onClick={() => waiveMutation.mutate({ id: c.id, note: resolveNote[c.id] || 'Waived by AICTE' })}
                                  disabled={waiveMutation.isPending}
                                >
                                  Waive
                                </button>
                              )}
                            </div>
                          </div>
                        )}
                        {c.status === 'Resolved' && (
                          <span style={{ fontSize: 12, color: '#4ade80' }}>✓ {c.resolution_note?.substring(0, 40)}</span>
                        )}
                        {c.status === 'Waived' && (
                          <span style={{ fontSize: 12, color: '#94a3b8' }}>Waived: {c.resolution_note?.substring(0, 30)}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}

      {activeTab === 'rules' && (
        <div className="card" style={{ padding: 0 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Code</th>
                <th>Description</th>
                <th>Severity</th>
                <th>Owner</th>
                <th>Source</th>
                <th>Enabled</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((r: any) => (
                <tr key={r.id}>
                  <td>
                    <span style={{ fontFamily: 'monospace', fontWeight: 800, color: '#93c5fd', fontSize: 13 }}>
                      {r.code}
                    </span>
                  </td>
                  <td style={{ fontSize: 12.5, color: '#cbd5e1', maxWidth: 280 }}>{r.description}</td>
                  <td><SeverityBadge severity={r.severity} /></td>
                  <td style={{ fontSize: 12, color: '#64748b' }}>{r.owner_role}</td>
                  <td style={{ fontSize: 11, color: '#475569', maxWidth: 180 }}>{r.source_ref}</td>
                  <td>
                    {isAdmin ? (
                      <button
                        className={`btn btn-sm ${r.enabled ? 'btn-success' : 'btn-danger'}`}
                        onClick={() => toggleRuleMutation.mutate({ id: r.id, enabled: !r.enabled })}
                        disabled={toggleRuleMutation.isPending}
                      >
                        {r.enabled ? '● ON' : '○ OFF'}
                      </button>
                    ) : (
                      <span style={{ color: r.enabled ? '#4ade80' : '#64748b', fontWeight: 700 }}>
                        {r.enabled ? '● ON' : '○ OFF'}
                      </span>
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
