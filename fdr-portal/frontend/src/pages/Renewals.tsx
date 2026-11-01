import { useQuery } from '@tanstack/react-query'
import { getRenewals } from '../api/client'
import { StatusBadge, EmptyState, Spinner } from '../components/UI'
import { RotateCcw, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function Renewals() {
  const { data: renewals = [], isLoading } = useQuery({
    queryKey: ['renewals'],
    queryFn: getRenewals,
  })

  return (
    <div>
      <div className="page-header">
        <h2>FDR Renewals & Replacements</h2>
        <p>Traceable instrument replacement chains ensuring continuous regulatory financial security.</p>
      </div>

      {isLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><Spinner size={32} /></div>
      ) : renewals.length === 0 ? (
        <EmptyState
          icon="🔄"
          title="No renewal chains found"
          desc="When an FDR nears maturity and is renewed or replaced, the chain history will appear here."
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {renewals.map((r: any) => (
            <div key={r.id} className="card" style={{ padding: 18 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span className={`badge ${r.kind === 'RENEWAL' ? 'active' : 'medium'}`} style={{ textTransform: 'uppercase' }}>
                    <RotateCcw size={12} /> {r.kind}
                  </span>
                  <span style={{ fontSize: 13, color: '#94a3b8' }}>
                    Renewed on: {r.renewed_on}
                  </span>
                </div>
                {r.reason && (
                  <span style={{ fontSize: 12, color: '#cbd5e1', fontStyle: 'italic' }}>
                    "{r.reason}"
                  </span>
                )}
              </div>

              <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr auto 1fr',
                gap: 20,
                alignItems: 'center',
                background: 'rgba(255,255,255,0.02)',
                padding: '16px 20px',
                borderRadius: 10,
                border: '1px solid rgba(255,255,255,0.05)'
              }}>
                {/* Old FDR */}
                {r.old_fdr ? (
                  <div>
                    <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: 4 }}>
                      Previous Instrument
                    </div>
                    <Link
                      to={`/fdrs/${r.old_fdr.id}`}
                      style={{ fontSize: 16, fontWeight: 700, color: '#f1f5f9', textDecoration: 'none' }}
                    >
                      {r.old_fdr.fdr_number}
                    </Link>
                    <div style={{ display: 'flex', gap: 10, marginTop: 6, fontSize: 12, color: '#94a3b8' }}>
                      <span>Principal: ₹{(r.old_fdr.principal / 100000).toFixed(1)}L</span>
                      <span>Maturity: {r.old_fdr.maturity_date}</span>
                    </div>
                    <div style={{ marginTop: 8 }}>
                      <StatusBadge status={r.old_fdr.status} />
                    </div>
                  </div>
                ) : (
                  <span style={{ color: '#64748b' }}>No record</span>
                )}

                {/* Transition Arrow */}
                <div style={{
                  display: 'flex', flexDirection: 'column', alignItems: 'center',
                  color: '#6366f1', padding: '0 12px'
                }}>
                  <ArrowRight size={24} />
                  <span style={{ fontSize: 11, fontWeight: 600, marginTop: 4 }}>REPLACED BY</span>
                </div>

                {/* New FDR */}
                {r.new_fdr ? (
                  <div>
                    <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: 4 }}>
                      Active Replacement Instrument
                    </div>
                    <Link
                      to={`/fdrs/${r.new_fdr.id}`}
                      style={{ fontSize: 16, fontWeight: 700, color: '#4ade80', textDecoration: 'none' }}
                    >
                      {r.new_fdr.fdr_number}
                    </Link>
                    <div style={{ display: 'flex', gap: 10, marginTop: 6, fontSize: 12, color: '#94a3b8' }}>
                      <span>Principal: ₹{(r.new_fdr.principal / 100000).toFixed(1)}L</span>
                      <span>Maturity: {r.new_fdr.maturity_date}</span>
                    </div>
                    <div style={{ marginTop: 8 }}>
                      <StatusBadge status={r.new_fdr.status} />
                    </div>
                  </div>
                ) : (
                  <span style={{ color: '#64748b' }}>Pending creation</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
