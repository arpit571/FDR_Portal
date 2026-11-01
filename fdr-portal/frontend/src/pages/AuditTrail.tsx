import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getAuditLog, verifyAuditChain, simulateTamper, restoreTamper } from '../api/client'
import { useAuth } from '../app/AuthContext'
import { EmptyState, Spinner } from '../components/UI'
import { ShieldCheck, AlertTriangle, RefreshCw, Search } from 'lucide-react'

export default function AuditTrail() {
  const qc = useQueryClient()
  const { isAuditor, isAdmin } = useAuth()
  const [search, setSearch] = useState('')
  const [tamperedData, setTamperedData] = useState<{ id: string; original: string } | null>(null)
  const [msg, setMsg] = useState({ type: '', text: '' })

  const { data: logs = [], isLoading } = useQuery({
    queryKey: ['audit-log'],
    queryFn: () => getAuditLog({ limit: 100 }),
  })

  const { data: chainVerification, refetch: recheckChain, isFetching: isVerifying } = useQuery({
    queryKey: ['audit-verify'],
    queryFn: verifyAuditChain,
  })

  const tamperMut = useMutation({
    mutationFn: simulateTamper,
    onSuccess: (data: any) => {
      setTamperedData({ id: data.tampered_entry_id, original: data.original_action })
      qc.invalidateQueries({ queryKey: ['audit-log'] })
      qc.invalidateQueries({ queryKey: ['audit-verify'] })
      setMsg({ type: 'warning', text: 'Simulated tamper executed: An entry was altered. Verification will now fail!' })
    }
  })

  const restoreMut = useMutation({
    mutationFn: () => restoreTamper(tamperedData!.id, tamperedData!.original),
    onSuccess: () => {
      setTamperedData(null)
      qc.invalidateQueries({ queryKey: ['audit-log'] })
      qc.invalidateQueries({ queryKey: ['audit-verify'] })
      setMsg({ type: 'success', text: 'Tampered entry restored to original value. Cryptographic chain is healthy.' })
    }
  })

  const isChainValid = chainVerification?.valid ?? true
  const totalEntries = chainVerification?.total_entries ?? logs.length

  const filtered = logs.filter((l: any) =>
    !search ||
    l.action?.toLowerCase().includes(search.toLowerCase()) ||
    l.entity_type?.toLowerCase().includes(search.toLowerCase()) ||
    l.entity_id?.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>Tamper-Evident Cryptographic Audit Trail</h2>
          <p>Immutable append-only ledger secured by SHA-256 block-hash chaining for full regulatory traceability.</p>
        </div>
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
          {msg.type === 'success' ? <ShieldCheck size={16} /> : <AlertTriangle size={16} />}
          {msg.text}
        </div>
      )}

      {/* Cryptographic Chain Status Banner */}
      <div className="card" style={{
        marginBottom: 20,
        background: isChainValid ? 'rgba(34,197,94,0.06)' : 'rgba(239,68,68,0.1)',
        borderColor: isChainValid ? 'rgba(34,197,94,0.25)' : 'rgba(239,68,68,0.4)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '16px 20px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          {isChainValid ? (
            <div style={{ width: 44, height: 44, borderRadius: 12, background: 'rgba(34,197,94,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <ShieldCheck size={24} color="#4ade80" />
            </div>
          ) : (
            <div style={{ width: 44, height: 44, borderRadius: 12, background: 'rgba(239,68,68,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <AlertTriangle size={24} color="#f87171" />
            </div>
          )}
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, color: isChainValid ? '#4ade80' : '#f87171', display: 'flex', alignItems: 'center', gap: 8 }}>
              {isChainValid ? 'Hash Chain Integrity: VERIFIED VALID' : 'TAMPER DETECTED: Hash Chain Broken!'}
            </div>
            <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>
              Verified {totalEntries} chained records against cryptographic SHA-256 genesis.
              {!isChainValid && ` Discrepancy found at entry index: ${chainVerification?.broken_at_index}`}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10 }}>
          <button
            className="btn btn-secondary"
            onClick={() => recheckChain()}
            disabled={isVerifying}
          >
            <RefreshCw size={14} className={isVerifying ? 'animate-spin' : ''} />
            {isVerifying ? 'Verifying...' : 'Re-verify Chain'}
          </button>

          {(isAuditor || isAdmin) && (
            !tamperedData ? (
              <button
                className="btn btn-ghost"
                style={{ border: '1px dashed #64748b', fontSize: 12 }}
                onClick={() => tamperMut.mutate()}
                disabled={tamperMut.isPending}
                title="Demo demonstration of cryptographic tampering detection"
              >
                Simulate Tamper
              </button>
            ) : (
              <button
                className="btn btn-primary"
                style={{ fontSize: 12 }}
                onClick={() => restoreMut.mutate()}
                disabled={restoreMut.isPending}
              >
                Restore Entry
              </button>
            )
          )}
        </div>
      </div>

      {/* Filter */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ position: 'relative' }}>
          <Search size={16} style={{ position: 'absolute', left: 12, top: 12, color: '#64748b' }} />
          <input
            type="text"
            placeholder="Search audit trail by action, entity type, or record ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input"
            style={{ paddingLeft: 38 }}
          />
        </div>
      </div>

      {isLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><Spinner size={32} /></div>
      ) : filtered.length === 0 ? (
        <EmptyState icon="📋" title="No audit entries found" desc="Every system action, state change, and decision is logged here." />
      ) : (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Timestamp (UTC)</th>
                <th>Action</th>
                <th>Entity</th>
                <th>Cryptographic Hash</th>
                <th>IP / Origin</th>
                <th>State Delta</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((l: any) => (
                <tr key={l.id}>
                  <td>
                    <span style={{ fontSize: 12, color: '#94a3b8' }}>{l.created_at}</span>
                  </td>
                  <td>
                    <span style={{ fontWeight: 600, color: '#e2e8f0' }}>{l.action}</span>
                  </td>
                  <td>
                    <span className="badge" style={{ background: 'rgba(255,255,255,0.06)', textTransform: 'uppercase', fontSize: 11 }}>
                      {l.entity_type}
                    </span>
                  </td>
                  <td>
                    <code style={{ fontSize: 11, background: 'rgba(99,102,241,0.1)', color: '#a5b4fc', padding: '2px 6px', borderRadius: 4 }}>
                      {l.hash}
                    </code>
                  </td>
                  <td>
                    <span style={{ fontSize: 12, color: '#64748b' }}>{l.ip || '127.0.0.1'}</span>
                  </td>
                  <td>
                    {l.after_json ? (
                      <span style={{ fontSize: 11, color: '#cbd5e1', maxWidth: 160, display: 'inline-block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {JSON.stringify(l.after_json)}
                      </span>
                    ) : (
                      <span style={{ fontSize: 11, color: '#64748b' }}>—</span>
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
