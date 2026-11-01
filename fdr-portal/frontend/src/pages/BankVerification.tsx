import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getFDRs, submitVerification, decideVerification } from '../api/client'
import { useAuth } from '../app/AuthContext'
import { EmptyState, Spinner } from '../components/UI'
import { ShieldCheck, CheckCircle2, XCircle, AlertTriangle, Search, FileText } from 'lucide-react'

export default function BankVerification() {
  const [searchParams] = useSearchParams()
  const qc = useQueryClient()
  const { isAICTE, isAdmin, isFinance } = useAuth()
  const [search, setSearch] = useState('')
  const [selectedFDR, setSelectedFDR] = useState<any | null>(null)
  const [remarks, setRemarks] = useState('')
  const [certForm, setCertForm] = useState({
    account_holder: '',
    account_number_masked: '',
    bank_name: '',
    bank_address: '',
    account_authentic: true,
    balance_confirmed: true,
    certified_fdr_number: '',
    certified_amount: 0,
    belongs_to_institution: true,
    is_authentic: true,
    loan_or_mortgage: false,
    remarks: '',
  })
  const [msg, setMsg] = useState({ type: '', text: '' })

  const { data: fdrs = [], isLoading } = useQuery({
    queryKey: ['fdrs'],
    queryFn: () => getFDRs(),
  })

  const decideMut = useMutation({
    mutationFn: ({ fdrId, decision, remarks }: { fdrId: string; decision: string; remarks: string }) =>
      decideVerification(fdrId, decision, remarks),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['fdrs'] })
      setMsg({ type: 'success', text: 'Verification decision recorded and audit log updated.' })
      setSelectedFDR(null)
      setTimeout(() => setMsg({ type: '', text: '' }), 4000)
    },
    onError: (err: any) => {
      setMsg({ type: 'error', text: err.response?.data?.detail || 'Failed to record decision.' })
    }
  })

  const submitCertMut = useMutation({
    mutationFn: ({ fdrId, data }: { fdrId: string; data: any }) =>
      submitVerification(fdrId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['fdrs'] })
      setMsg({ type: 'success', text: 'Certificate 3 details submitted for AICTE verification.' })
      setSelectedFDR(null)
      setTimeout(() => setMsg({ type: '', text: '' }), 4000)
    },
    onError: (err: any) => {
      setMsg({ type: 'error', text: err.response?.data?.detail || 'Failed to submit certificate.' })
    }
  })

  const filtered = fdrs.filter((f: any) =>
    !search ||
    f.fdr_number?.toLowerCase().includes(search.toLowerCase()) ||
    f.bank_name?.toLowerCase().includes(search.toLowerCase()) ||
    f.institution_name?.toLowerCase().includes(search.toLowerCase())
  )

  const handleOpenDetail = (f: any) => {
    setSelectedFDR(f)
    setRemarks('')
    const v = f.verification || {}
    setCertForm({
      account_holder: v.account_holder || f.depositor_name || '',
      account_number_masked: v.account_number_masked || 'XXXX-XXXX-1234',
      bank_name: v.bank_name || f.bank_name || '',
      bank_address: v.bank_address || 'Main Branch',
      account_authentic: v.account_authentic ?? true,
      balance_confirmed: v.balance_confirmed ?? true,
      certified_fdr_number: v.certified_fdr_number || f.fdr_number || '',
      certified_amount: v.certified_amount || f.principal || 0,
      belongs_to_institution: v.belongs_to_institution ?? true,
      is_authentic: v.is_authentic ?? true,
      loan_or_mortgage: v.loan_or_mortgage ?? false,
      remarks: v.remarks || '',
    })
  }

  const fdrParam = searchParams.get('fdr')
  useEffect(() => {
    if (fdrParam && fdrs.length > 0) {
      const match = fdrs.find((f: any) => f.id === fdrParam)
      if (match) handleOpenDetail(match)
    }
  }, [fdrParam, fdrs])

  return (
    <div>
      <div className="page-header">
        <h2>Bank Verification (Certificate 3)</h2>
        <p>Independent verification of Fixed Deposit Receipts directly against issuing bank records and Certificate 3 affidavits.</p>
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
          {msg.type === 'success' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
          {msg.text}
        </div>
      )}

      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ position: 'relative' }}>
          <Search size={16} style={{ position: 'absolute', left: 12, top: 12, color: '#64748b' }} />
          <input
            type="text"
            placeholder="Search by FDR number, issuing bank, or institution..."
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
        <EmptyState icon="🏛️" title="No verification records" desc="No FDRs found matching the filter." />
      ) : (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>FDR Number</th>
                <th>Institution</th>
                <th>Issuing Bank</th>
                <th>Principal (₹)</th>
                <th>Verification Status</th>
                <th>Lien / Loan Check</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((f: any) => {
                const ver = f.verification
                const status = ver?.status || 'PENDING'
                const hasLien = ver?.loan_or_mortgage

                return (
                  <tr key={f.id}>
                    <td>
                      <span style={{ fontWeight: 600, color: '#f1f5f9' }}>{f.fdr_number}</span>
                    </td>
                    <td>
                      <div style={{ fontWeight: 600, color: '#e2e8f0' }}>{f.institution_name}</div>
                    </td>
                    <td>{f.bank_name}</td>
                    <td>₹{(f.principal / 100000).toFixed(1)}L</td>
                    <td>
                      <span className={`badge ${status === 'VERIFIED' ? 'active' : status === 'REJECTED' || status === 'DISCREPANCY_DETECTED' ? 'high' : 'pending'}`}>
                        {status}
                      </span>
                    </td>
                    <td>
                      {ver ? (
                        hasLien ? (
                          <span className="badge high"><AlertTriangle size={12} /> Encumbered / Loan exists</span>
                        ) : (
                          <span className="badge active"><CheckCircle2 size={12} /> Clear (No Lien)</span>
                        )
                      ) : (
                        <span style={{ fontSize: 12, color: '#64748b' }}>Pending submission</span>
                      )}
                    </td>
                    <td>
                      <button
                        className="btn btn-secondary"
                        style={{ padding: '4px 10px', fontSize: 12 }}
                        onClick={() => handleOpenDetail(f)}
                      >
                        Inspect / Verify
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Verification Modal */}
      {selectedFDR && (
        <div className="modal-overlay" onClick={() => setSelectedFDR(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 640 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ fontSize: 18, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
                <ShieldCheck size={20} color="#3b82f6" />
                Certificate 3 Verification — {selectedFDR.fdr_number}
              </h3>
              <button className="btn btn-ghost" onClick={() => setSelectedFDR(null)}>✕</button>
            </div>

            <div style={{ background: 'rgba(255,255,255,0.03)', padding: 14, borderRadius: 8, marginBottom: 16 }}>
              <div style={{ fontSize: 13, color: '#94a3b8' }}>
                <strong>Institution:</strong> {selectedFDR.institution_name} | <strong>Bank:</strong> {selectedFDR.bank_name} | <strong>Amount:</strong> ₹{(selectedFDR.principal / 100000).toFixed(1)}L
              </div>
            </div>

            {/* Checklist */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 20 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label className="label">Account Holder Name</label>
                  <input
                    type="text"
                    className="input"
                    value={certForm.account_holder}
                    onChange={(e) => setCertForm({ ...certForm, account_holder: e.target.value })}
                  />
                </div>
                <div>
                  <label className="label">Account Number (Masked)</label>
                  <input
                    type="text"
                    className="input"
                    value={certForm.account_number_masked}
                    onChange={(e) => setCertForm({ ...certForm, account_number_masked: e.target.value })}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label className="label">Certified FDR Amount (₹)</label>
                  <input
                    type="number"
                    className="input"
                    value={certForm.certified_amount}
                    onChange={(e) => setCertForm({ ...certForm, certified_amount: Number(e.target.value) })}
                  />
                </div>
                <div>
                  <label className="label">Certified FDR Number</label>
                  <input
                    type="text"
                    className="input"
                    value={certForm.certified_fdr_number}
                    onChange={(e) => setCertForm({ ...certForm, certified_fdr_number: e.target.value })}
                  />
                </div>
              </div>

              {/* Boolean checks */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: 12, background: 'rgba(255,255,255,0.02)', borderRadius: 8, border: '1px solid rgba(255,255,255,0.06)' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: '#e2e8f0', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={certForm.balance_confirmed}
                    onChange={(e) => setCertForm({ ...certForm, balance_confirmed: e.target.checked })}
                  />
                  <span>1. Bank confirms account authenticity & balance is verified</span>
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: '#e2e8f0', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={certForm.belongs_to_institution}
                    onChange={(e) => setCertForm({ ...certForm, belongs_to_institution: e.target.checked })}
                  />
                  <span>2. FDR belongs legitimately to applicant institution / trust</span>
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: certForm.loan_or_mortgage ? '#f87171' : '#e2e8f0', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={certForm.loan_or_mortgage}
                    onChange={(e) => setCertForm({ ...certForm, loan_or_mortgage: e.target.checked })}
                  />
                  <span>3. Any Loan, Lien, or Mortgage exists against this FDR (Flag if YES)</span>
                </label>
              </div>

              <div>
                <label className="label">Verification Remarks</label>
                <textarea
                  className="input"
                  rows={2}
                  value={remarks || certForm.remarks}
                  onChange={(e) => {
                    setRemarks(e.target.value)
                    setCertForm({ ...certForm, remarks: e.target.value })
                  }}
                  placeholder="Record verification scrutiny observations..."
                />
              </div>
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: 14 }}>
              {(isFinance || isAdmin) && (
                <button
                  type="button"
                  className="btn btn-secondary"
                  disabled={submitCertMut.isPending}
                  onClick={() => submitCertMut.mutate({ fdrId: selectedFDR.id, data: certForm })}
                >
                  <FileText size={14} /> Update Certificate 3
                </button>
              )}

              <div style={{ display: 'flex', gap: 8, marginLeft: 'auto' }}>
                {(isAICTE || isAdmin) ? (
                  <>
                    <button
                      type="button"
                      className="btn"
                      style={{ background: 'rgba(239,68,68,0.2)', color: '#f87171', border: '1px solid rgba(239,68,68,0.4)' }}
                      disabled={decideMut.isPending}
                      onClick={() => decideMut.mutate({ fdrId: selectedFDR.id, decision: 'REJECTED', remarks })}
                    >
                      <XCircle size={14} /> Reject
                    </button>
                    <button
                      type="button"
                      className="btn"
                      style={{ background: 'rgba(245,158,11,0.2)', color: '#fbbf24', border: '1px solid rgba(245,158,11,0.4)' }}
                      disabled={decideMut.isPending}
                      onClick={() => decideMut.mutate({ fdrId: selectedFDR.id, decision: 'DISCREPANCY_DETECTED', remarks })}
                    >
                      <AlertTriangle size={14} /> Flag Discrepancy
                    </button>
                    <button
                      type="button"
                      className="btn btn-primary"
                      disabled={decideMut.isPending}
                      onClick={() => decideMut.mutate({ fdrId: selectedFDR.id, decision: 'VERIFIED', remarks })}
                    >
                      <CheckCircle2 size={14} /> Verify & Approve
                    </button>
                  </>
                ) : (
                  <button type="button" className="btn btn-secondary" onClick={() => setSelectedFDR(null)}>
                    Close
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
