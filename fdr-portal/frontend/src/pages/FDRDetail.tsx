import { useState, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getFDR, getDocumentOCR, getVerification, getDiscrepancies,
  getAlerts, getAuditLog, uploadDocument, transitionFDR, acknowledgeAlert,
  renewFDR
} from '../api/client'
import { useAuth } from '../app/AuthContext'
import { StatusBadge, SeverityBadge, ConfidenceChip, Currency, Spinner, EmptyState } from '../components/UI'
import { Upload, ShieldCheck, AlertTriangle, ChevronLeft, RotateCcw, X } from 'lucide-react'

export default function FDRDetail() {
  const { id } = useParams<{ id: string }>()
  const qc = useQueryClient()
  const { isFinance, isAICTE, isAdmin } = useAuth()
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [activeTab, setActiveTab] = useState<'ocr' | 'verification' | 'discrepancies' | 'alerts' | 'audit'>('ocr')
  const [showRenewModal, setShowRenewModal] = useState(false)
  const [renewForm, setRenewForm] = useState({
    kind: 'RENEWAL',
    fdr_number: '',
    bank_id: '',
    principal: 0,
    rate: 6.5,
    start_date: '',
    maturity_date: '',
    depositor_name: '',
    reason: 'Standard regulatory tenure renewal',
  })

  const { data: fdr, isLoading } = useQuery({
    queryKey: ['fdr', id], queryFn: () => getFDR(id!)
  })
  const { data: ocr } = useQuery({
    queryKey: ['ocr', fdr?.document_id],
    queryFn: () => getDocumentOCR(fdr!.document_id!),
    enabled: !!fdr?.document_id,
  })
  const { data: verification } = useQuery({
    queryKey: ['verification', id], queryFn: () => getVerification(id!)
  })
  const { data: discrepancies = [] } = useQuery({
    queryKey: ['discrepancies', id],
    queryFn: () => getDiscrepancies(),
  })
  const { data: alerts = [] } = useQuery({
    queryKey: ['alerts', id], queryFn: () => getAlerts({ fdr_id: id })
  })
  const { data: auditLog = [] } = useQuery({
    queryKey: ['audit', id], queryFn: () => getAuditLog({ entity_type: 'fdr', entity_id: id })
  })

  const fdrDiscrepancies = discrepancies.filter((d: any) => d.fdr_id === id)

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setUploadError('')
    try {
      await uploadDocument(id!, file)
      qc.invalidateQueries({ queryKey: ['fdr', id] })
      qc.invalidateQueries({ queryKey: ['ocr'] })
    } catch (err: any) {
      setUploadError(err.response?.data?.detail || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const transitionMutation = useMutation({
    mutationFn: ({ to, note }: { to: string; note?: string }) => transitionFDR(id!, to, note),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['fdr', id] }),
  })

  const renewMutation = useMutation({
    mutationFn: (data: any) => renewFDR(id!, data),
    onSuccess: () => {
      setShowRenewModal(false)
      qc.invalidateQueries({ queryKey: ['fdr', id] })
      qc.invalidateQueries({ queryKey: ['renewals'] })
    },
    onError: (err: any) => {
      setUploadError(err.response?.data?.detail || 'Renewal failed')
    }
  })

  const handleOpenRenew = () => {
    if (!fdr) return
    setRenewForm({
      kind: 'RENEWAL',
      fdr_number: `${fdr.fdr_number}-RN`,
      bank_id: fdr.bank_id,
      principal: fdr.principal,
      rate: fdr.rate || 6.5,
      start_date: fdr.maturity_date || new Date().toISOString().split('T')[0],
      maturity_date: new Date(Date.now() + 365 * 24 * 3600 * 1000 * 3).toISOString().split('T')[0],
      depositor_name: fdr.depositor_name || '',
      reason: 'Regulatory renewal upon maturity',
    })
    setShowRenewModal(true)
  }

  if (isLoading) return <div style={{ padding: 60, textAlign: 'center' }}><Spinner size={32} /></div>
  if (!fdr) return <div className="empty-state"><h3>FDR not found</h3></div>

  const criticalOpen = fdrDiscrepancies.filter((d: any) =>
    d.severity === 'Critical' && ['Open', 'Under Review'].includes(d.status)
  ).length

  const TABS = [
    { key: 'ocr', label: 'OCR Fields', count: ocr?.fields?.length },
    { key: 'verification', label: 'Bank Verification' },
    { key: 'discrepancies', label: 'Discrepancies', count: fdrDiscrepancies.length, alert: criticalOpen > 0 },
    { key: 'alerts', label: 'Alerts', count: alerts.length },
    { key: 'audit', label: 'Audit Trail', count: auditLog.length },
  ]

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 20 }}>
        <Link to="/fdrs" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: '#64748b', textDecoration: 'none', fontSize: 13 }}>
          <ChevronLeft size={15} /> Back to FDRs
        </Link>
      </div>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 20 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
            <h2 style={{ fontSize: 20, fontWeight: 800, color: '#f1f5f9' }}>
              {fdr.fdr_number}
            </h2>
            <StatusBadge status={fdr.status} />
            {criticalOpen > 0 && (
              <span className="badge critical pulse-red">
                {criticalOpen} Critical Issue{criticalOpen > 1 ? 's' : ''}
              </span>
            )}
          </div>
          <p style={{ fontSize: 13, color: '#64748b' }}>{fdr.bank_name} • <Currency amount={fdr.principal} /> • {fdr.kind}</p>
        </div>

        {/* Action buttons */}
        <div style={{ display: 'flex', gap: 8 }}>
          {(isFinance || isAdmin) && (
            <>
              <input ref={fileRef} type="file" accept=".pdf,.jpg,.jpeg,.png" style={{ display: 'none' }} onChange={handleUpload} />
              <button className="btn btn-secondary btn-sm" onClick={() => fileRef.current?.click()} disabled={uploading}>
                {uploading ? <Spinner size={13} /> : <Upload size={13} />}
                Upload FDR
              </button>
              <button className="btn btn-secondary btn-sm" onClick={handleOpenRenew}>
                ↩ Renew / Replace
              </button>
            </>
          )}
          {(isAICTE || isAdmin) && (
            <Link to={`/verification?fdr=${id}`} className="btn btn-secondary btn-sm">
              <ShieldCheck size={13} /> Verify
            </Link>
          )}
          <Link to={`/releases?new=true&deposit=${fdr.deposit_id}&fdr=${id}`} className="btn btn-secondary btn-sm">
            🔓 Request Release
          </Link>
        </div>
      </div>

      {uploadError && (
        <div className="alert-banner danger" style={{ marginBottom: 16 }}>
          <AlertTriangle size={15} />
          {uploadError}
        </div>
      )}

      {/* Main detail grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
        <div className="card">
          <div className="section-title">FDR Details</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {[
              ['FDR Number', fdr.fdr_number],
              ['Bank', fdr.bank_name],
              ['Principal', `₹${(fdr.principal / 100000).toFixed(2)}L`],
              ['Interest Rate', fdr.rate ? `${fdr.rate}%` : '—'],
              ['Start Date', fdr.start_date],
              ['Maturity Date', fdr.maturity_date],
              ['Days to Maturity', fdr.days_to_maturity !== null
                ? (fdr.days_to_maturity < 0
                  ? `${Math.abs(fdr.days_to_maturity)} days overdue`
                  : `${fdr.days_to_maturity} days`)
                : '—'],
              ['Depositor Name', fdr.depositor_name || '—'],
            ].map(([k, v]) => (
              <div key={k}>
                <div style={{ fontSize: 11, color: '#64748b', marginBottom: 3, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{k}</div>
                <div style={{ fontSize: 13.5, color: '#e2e8f0', fontWeight: 500 }}>{v}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="section-title">Status Actions</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {fdr.status === 'Pending Review' && (
              <div className="alert-banner warning">
                <AlertTriangle size={15} />
                This FDR has low-confidence OCR fields that need review.
              </div>
            )}
            {criticalOpen > 0 && (
              <div className="alert-banner danger">
                <AlertTriangle size={15} />
                {criticalOpen} Critical discrepancy must be resolved before activation.
              </div>
            )}

            {/* Allowed transitions */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {fdr.status === 'Pending Review' && criticalOpen === 0 && (isAICTE || isAdmin) && (
                <button
                  className="btn btn-success btn-sm"
                  onClick={() => transitionMutation.mutate({ to: 'Active' })}
                  disabled={transitionMutation.isPending}
                >
                  ✓ Mark Active
                </button>
              )}
              {['Active', 'Maturity Alert'].includes(fdr.status) && (
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => transitionMutation.mutate({ to: 'Matured - Action Pending' })}
                  disabled={transitionMutation.isPending}
                >
                  Mark Matured
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid rgba(255,255,255,0.06)', marginBottom: 20 }}>
        {TABS.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            style={{
              padding: '10px 18px',
              background: 'none', border: 'none', cursor: 'pointer',
              fontSize: 13.5, fontWeight: 600,
              color: activeTab === tab.key ? '#93c5fd' : '#64748b',
              borderBottom: activeTab === tab.key ? '2px solid #3b82f6' : '2px solid transparent',
              display: 'flex', alignItems: 'center', gap: 6,
              transition: 'color 0.15s',
            }}
          >
            {tab.label}
            {tab.count !== undefined && (
              <span style={{
                fontSize: 11, padding: '1px 6px', borderRadius: 10,
                background: tab.alert ? 'rgba(239,68,68,0.2)' : 'rgba(255,255,255,0.08)',
                color: tab.alert ? '#f87171' : '#64748b',
              }}>
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'ocr' && (
        <div className="card">
          {!fdr.document_id ? (
            <EmptyState icon="📄" title="No document uploaded" desc="Upload an FDR document to see OCR fields." />
          ) : !ocr ? (
            <div style={{ padding: 40, textAlign: 'center' }}><Spinner /> <p style={{ marginTop: 12, color: '#64748b' }}>OCR processing…</p></div>
          ) : (
            <table className="data-table">
              <thead>
                <tr><th>Field</th><th>Extracted Value</th><th>Confidence</th><th>Reviewed Value</th><th>Reviewed By</th></tr>
              </thead>
              <tbody>
                {ocr.fields?.map((f: any) => (
                  <tr key={f.id}>
                    <td style={{ fontWeight: 600, color: '#94a3b8' }}>{f.field_name}</td>
                    <td style={{ fontFamily: 'monospace', fontSize: 12.5 }}>{f.extracted_value || '—'}</td>
                    <td><ConfidenceChip confidence={f.confidence || 0} /></td>
                    <td style={{ color: f.reviewed_value ? '#4ade80' : '#475569' }}>
                      {f.reviewed_value || <span style={{ fontStyle: 'italic', color: '#334155' }}>not reviewed</span>}
                    </td>
                    <td style={{ fontSize: 12, color: '#64748b' }}>{f.reviewed_by || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {activeTab === 'verification' && (
        <div className="card">
          {!verification ? (
            <EmptyState icon="🏦" title="No verification record" desc="Bank verification has not been submitted yet." />
          ) : (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
                <StatusBadge status={verification.status?.toLowerCase() || 'pending'} />
                {verification.verified_at && (
                  <span style={{ fontSize: 12, color: '#64748b' }}>Verified: {verification.verified_at}</span>
                )}
              </div>
              <div className="compare-grid">
                <div className="compare-col">
                  <div className="compare-label">Submitted by Institution</div>
                  {[
                    ['FDR Number', fdr.fdr_number],
                    ['Principal', `₹${(fdr.principal / 100000).toFixed(2)}L`],
                    ['Maturity Date', fdr.maturity_date],
                  ].map(([k, v]) => (
                    <div className="compare-row" key={k}>
                      <span className="compare-field">{k}</span>
                      <span className="compare-value">{v}</span>
                    </div>
                  ))}
                </div>
                <div className="compare-col">
                  <div className="compare-label">Certified by Bank</div>
                  {[
                    ['FDR Number', verification.certified_fdr_number, fdr.fdr_number],
                    ['Amount', verification.certified_amount ? `₹${(verification.certified_amount / 100000).toFixed(2)}L` : '—', null],
                    ['Maturity Date', verification.certified_maturity_date, fdr.maturity_date],
                  ].map(([k, v, compare]) => (
                    <div className="compare-row" key={k as string}>
                      <span className="compare-field">{k as string}</span>
                      <span className={`compare-value ${compare && v !== compare ? 'mismatch' : 'match'}`}>
                        {(v as string) || '—'}
                        {compare && v !== compare && ' ⚠'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
              {verification.remarks && (
                <div style={{ marginTop: 12, padding: 12, background: 'rgba(255,255,255,0.03)', borderRadius: 8, fontSize: 13, color: '#94a3b8' }}>
                  <strong>Remarks:</strong> {verification.remarks}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {activeTab === 'discrepancies' && (
        <div className="card" style={{ padding: 0 }}>
          {fdrDiscrepancies.length === 0 ? (
            <EmptyState icon="✅" title="No discrepancies" desc="This FDR has no open discrepancy cases." />
          ) : (
            <table className="data-table">
              <thead>
                <tr><th>Rule</th><th>Severity</th><th>Status</th><th>Message</th><th>Opened</th></tr>
              </thead>
              <tbody>
                {fdrDiscrepancies.map((d: any) => (
                  <tr key={d.id}>
                    <td style={{ fontWeight: 700, color: '#93c5fd', fontFamily: 'monospace', fontSize: 12 }}>{d.rule_code}</td>
                    <td><SeverityBadge severity={d.severity} /></td>
                    <td><StatusBadge status={d.status} /></td>
                    <td style={{ fontSize: 12.5, maxWidth: 300 }}>{d.message}</td>
                    <td style={{ fontSize: 12, color: '#64748b' }}>{d.opened_at?.substring(0, 10)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {activeTab === 'alerts' && (
        <div className="card" style={{ padding: 0 }}>
          {alerts.length === 0 ? (
            <EmptyState icon="🔔" title="No alerts" />
          ) : (
            <table className="data-table">
              <thead>
                <tr><th>Alert Type</th><th>Scheduled</th><th>Escalated</th><th>Acknowledged</th><th></th></tr>
              </thead>
              <tbody>
                {alerts.map((a: any) => (
                  <tr key={a.id}>
                    <td style={{ fontWeight: 600 }}>{a.alert_type}</td>
                    <td>{a.scheduled_for}</td>
                    <td>{a.escalated ? <span style={{ color: '#f87171', fontWeight: 700 }}>YES</span> : 'No'}</td>
                    <td style={{ color: a.acknowledged_by ? '#4ade80' : '#64748b' }}>
                      {a.acknowledged_by ? '✓ Acked' : 'Pending'}
                    </td>
                    <td>
                      {!a.acknowledged_by && (
                        <button className="btn btn-success btn-sm" onClick={() => acknowledgeAlert(a.id).then(() => qc.invalidateQueries({ queryKey: ['alerts', id] }))}>
                          Acknowledge
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {activeTab === 'audit' && (
        <div>
          <div className="timeline">
            {auditLog.length === 0 ? (
              <EmptyState icon="📋" title="No audit entries yet" />
            ) : (
              auditLog.map((entry: any) => (
                <div className="timeline-item" key={entry.id}>
                  <div className="timeline-action">{entry.action}</div>
                  <div className="timeline-meta">
                    {entry.user_id ? `User ${entry.user_id.substring(0, 8)}…` : 'System'} •{' '}
                    {entry.created_at}
                  </div>
                  {entry.after_json && (
                    <div className="timeline-detail monospace">
                      {JSON.stringify(entry.after_json).substring(0, 120)}…
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
      {/* Renew / Replace Modal */}
      {showRenewModal && (
        <div className="modal-backdrop">
          <div className="modal-box" style={{ maxWidth: 500 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <RotateCcw size={18} color="#3b82f6" />
                <h3 style={{ fontSize: 16, fontWeight: 700, color: '#f1f5f9' }}>
                  Renew or Replace FDR
                </h3>
              </div>
              <button
                onClick={() => setShowRenewModal(false)}
                style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={e => {
              e.preventDefault()
              renewMutation.mutate({
                kind: renewForm.kind,
                new_fdr: {
                  deposit_id: fdr.deposit_id,
                  bank_id: renewForm.bank_id,
                  fdr_number: renewForm.fdr_number,
                  principal: Number(renewForm.principal),
                  rate: Number(renewForm.rate),
                  start_date: renewForm.start_date,
                  maturity_date: renewForm.maturity_date,
                  depositor_name: renewForm.depositor_name,
                  kind: renewForm.kind,
                },
                reason: renewForm.reason,
              })
            }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div>
                  <label className="form-label">Action Kind</label>
                  <select
                    className="form-control"
                    value={renewForm.kind}
                    onChange={e => setRenewForm({ ...renewForm, kind: e.target.value })}
                  >
                    <option value="RENEWAL">Renewal (Rollover existing instrument)</option>
                    <option value="REPLACEMENT">Replacement (Substitute new instrument)</option>
                  </select>
                </div>

                <div>
                  <label className="form-label">New FDR Number</label>
                  <input
                    type="text"
                    required
                    className="form-control"
                    value={renewForm.fdr_number}
                    onChange={e => setRenewForm({ ...renewForm, fdr_number: e.target.value })}
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div>
                    <label className="form-label">Principal Amount (₹)</label>
                    <input
                      type="number"
                      required
                      min={100000}
                      className="form-control"
                      value={renewForm.principal}
                      onChange={e => setRenewForm({ ...renewForm, principal: +e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="form-label">Interest Rate (%)</label>
                    <input
                      type="number"
                      step="0.01"
                      className="form-control"
                      value={renewForm.rate}
                      onChange={e => setRenewForm({ ...renewForm, rate: +e.target.value })}
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div>
                    <label className="form-label">Start Date</label>
                    <input
                      type="date"
                      required
                      className="form-control"
                      value={renewForm.start_date}
                      onChange={e => setRenewForm({ ...renewForm, start_date: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="form-label">Maturity Date</label>
                    <input
                      type="date"
                      required
                      className="form-control"
                      value={renewForm.maturity_date}
                      onChange={e => setRenewForm({ ...renewForm, maturity_date: e.target.value })}
                    />
                  </div>
                </div>

                <div>
                  <label className="form-label">Renewal / Replacement Reason</label>
                  <input
                    type="text"
                    required
                    className="form-control"
                    value={renewForm.reason}
                    onChange={e => setRenewForm({ ...renewForm, reason: e.target.value })}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 20 }}>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => setShowRenewModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary btn-sm"
                  disabled={renewMutation.isPending}
                >
                  {renewMutation.isPending ? <Spinner size={13} /> : 'Submit Renewal'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
