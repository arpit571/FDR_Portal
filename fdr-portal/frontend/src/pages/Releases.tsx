import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getReleases, getDeposits, createRelease,
  updateReleaseDoc, updateClearance, decideStep, recordNOC, closeRelease
} from '../api/client'
import { useAuth } from '../app/AuthContext'
import { StatusBadge, EmptyState, Spinner } from '../components/UI'
import { Unlock, Plus, CheckCircle, XCircle, Shield, FileCheck, ChevronRight } from 'lucide-react'

export default function Releases() {
  const [searchParams] = useSearchParams()
  const qc = useQueryClient()
  const { isFinance, isReviewer, isAICTE, isAdmin } = useAuth()
  const [selectedReq, setSelectedReq] = useState<any | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [msg, setMsg] = useState({ type: '', text: '' })

  // Form states
  const [createForm, setCreateForm] = useState({
    deposit_id: '',
    amount: 3500000,
    reason: 'Completion of 10-year term and full regulatory compliance',
    fdr_ids: [] as string[],
  })
  const [nocRef, setNocRef] = useState('')

  useEffect(() => {
    const isNew = searchParams.get('new') === 'true'
    const depId = searchParams.get('deposit')
    const fdrId = searchParams.get('fdr')
    if (isNew) {
      setShowCreateModal(true)
      if (depId) {
        setCreateForm(prev => ({
          ...prev,
          deposit_id: depId,
          fdr_ids: fdrId ? [fdrId] : []
        }))
      }
    }
  }, [searchParams])

  const { data: releases = [], isLoading } = useQuery({
    queryKey: ['releases'],
    queryFn: getReleases,
  })

  const { data: deposits = [] } = useQuery({
    queryKey: ['deposits'],
    queryFn: getDeposits,
    enabled: showCreateModal,
  })

  const createMut = useMutation({
    mutationFn: createRelease,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['releases'] })
      setShowCreateModal(false)
      setMsg({ type: 'success', text: 'Release request initiated with required document and clearance checklists.' })
      setTimeout(() => setMsg({ type: '', text: '' }), 4000)
    },
    onError: (err: any) => {
      setMsg({ type: 'error', text: err.response?.data?.detail || 'Failed to submit release request.' })
    }
  })

  const docMut = useMutation({
    mutationFn: ({ reqId, docType, present }: { reqId: string; docType: string; present: boolean }) =>
      updateReleaseDoc(reqId, { doc_type: docType, present }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['releases'] })
    }
  })

  const clearanceMut = useMutation({
    mutationFn: ({ reqId, cell, status, remarks }: { reqId: string; cell: string; status: string; remarks: string }) =>
      updateClearance(reqId, cell, { status, remarks }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['releases'] })
    }
  })

  const decideMut = useMutation({
    mutationFn: ({ reqId, stepNo, decision, comment }: { reqId: string; stepNo: number; decision: string; comment: string }) =>
      decideStep(reqId, stepNo, { decision, comment }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['releases'] })
      setMsg({ type: 'success', text: 'Approval decision recorded.' })
      setTimeout(() => setMsg({ type: '', text: '' }), 4000)
    }
  })

  const nocMut = useMutation({
    mutationFn: ({ reqId, noc_or_sanction, reference }: { reqId: string; noc_or_sanction: string; reference: string }) =>
      recordNOC(reqId, { noc_or_sanction, reference }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['releases'] })
      setMsg({ type: 'success', text: 'NOC / Sanction Order recorded.' })
      setTimeout(() => setMsg({ type: '', text: '' }), 4000)
    }
  })

  const closeMut = useMutation({
    mutationFn: (reqId: string) => closeRelease(reqId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['releases'] })
      setMsg({ type: 'success', text: 'FDR release executed and marked Closed.' })
      setSelectedReq(null)
      setTimeout(() => setMsg({ type: '', text: '' }), 4000)
    }
  })

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>Release & Refund Management</h2>
          <p>Multi-level regulatory clearances (PGRC, Vigilance) and maker-checker approval for FDR releases.</p>
        </div>
        {(isFinance || isAdmin) && (
          <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
            <Plus size={16} /> New Release Request
          </button>
        )}
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
          {msg.type === 'success' ? <CheckCircle size={16} /> : <XCircle size={16} />}
          {msg.text}
        </div>
      )}

      {isLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><Spinner size={32} /></div>
      ) : releases.length === 0 ? (
        <EmptyState icon="🔓" title="No release requests" desc="Submitted release requests and cell clearances will appear here." />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: selectedReq ? '1fr 1.2fr' : '1fr', gap: 20 }}>
          {/* List view */}
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Request ID</th>
                  <th>Amount (₹)</th>
                  <th>Reason</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {releases.map((r: any) => (
                  <tr
                    key={r.id}
                    style={{
                      background: selectedReq?.id === r.id ? 'rgba(99,102,241,0.08)' : undefined,
                      cursor: 'pointer'
                    }}
                    onClick={() => setSelectedReq(r)}
                  >
                    <td>
                      <span style={{ fontWeight: 600, color: '#f1f5f9' }}>REL-{r.id.slice(0, 8)}</span>
                    </td>
                    <td>₹{(r.amount / 100000).toFixed(1)}L</td>
                    <td>
                      <div className="truncate" style={{ maxWidth: 200, fontSize: 12, color: '#cbd5e1' }}>
                        {r.reason}
                      </div>
                    </td>
                    <td>
                      <StatusBadge status={r.status} />
                    </td>
                    <td>
                      <button className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: 12 }}>
                        Scrutiny <ChevronRight size={12} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Detailed scrutiny panel */}
          {selectedReq && (
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ fontSize: 17, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Shield size={18} color="#6366f1" /> Request REL-{selectedReq.id.slice(0, 8)}
                </h3>
                <StatusBadge status={selectedReq.status} />
              </div>

              <div style={{ fontSize: 13, color: '#94a3b8' }}>
                <strong>Reason:</strong> {selectedReq.reason}
                <br />
                <strong>Amount:</strong> ₹{(selectedReq.amount / 100000).toFixed(1)} Lakhs
              </div>

              {/* 1. Required Documents */}
              <div>
                <div style={{ fontSize: 13, fontWeight: 700, color: '#e2e8f0', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <FileCheck size={14} color="#38bdf8" /> 1. Prescribed Documentation Checklist (Clause 6.46)
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {selectedReq.documents?.map((d: any) => (
                    <label key={d.doc_type} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: d.present ? '#4ade80' : '#cbd5e1', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={d.present}
                        disabled={!isReviewer && !isAdmin}
                        onChange={(e) => docMut.mutate({ reqId: selectedReq.id, docType: d.doc_type, present: e.target.checked })}
                      />
                      <span>{d.doc_type}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* 2. Cell Clearances */}
              <div>
                <div style={{ fontSize: 13, fontWeight: 700, color: '#e2e8f0', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Shield size={14} color="#fbbf24" /> 2. Cell Clearances
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {selectedReq.clearances?.map((c: any) => (
                    <div key={c.cell} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.02)', padding: '6px 10px', borderRadius: 6 }}>
                      <span style={{ fontSize: 13, fontWeight: 600 }}>{c.cell} Cell</span>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                        <span className={`badge ${c.status === 'Cleared' ? 'active' : c.status === 'Rejected' ? 'high' : 'pending'}`}>
                          {c.status}
                        </span>
                        {(isAICTE || isAdmin) && c.status !== 'Cleared' && (
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '2px 8px', fontSize: 11 }}
                            onClick={() => clearanceMut.mutate({ reqId: selectedReq.id, cell: c.cell, status: 'Cleared', remarks: 'Clearance verified' })}
                          >
                            Clear
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 3. Approval Steps */}
              <div>
                <div style={{ fontSize: 13, fontWeight: 700, color: '#e2e8f0', marginBottom: 8 }}>
                  3. Two-Step Maker-Checker Approval
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {selectedReq.approval_steps?.map((s: any) => (
                    <div key={s.step_no} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 10px', background: 'rgba(255,255,255,0.02)', borderRadius: 6 }}>
                      <span style={{ fontSize: 13 }}>Step {s.step_no} ({s.role_required})</span>
                      <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        <span className={`badge ${s.status === 'Approved' ? 'active' : s.status === 'Rejected' ? 'high' : 'pending'}`}>
                          {s.status}
                        </span>
                        {s.status === 'Pending' && (isAICTE || isReviewer || isAdmin) && (
                          <button
                            className="btn btn-primary"
                            style={{ padding: '2px 8px', fontSize: 11 }}
                            onClick={() => decideMut.mutate({ reqId: selectedReq.id, stepNo: s.step_no, decision: 'approve', comment: 'Approved step' })}
                            disabled={decideMut.isPending}
                          >
                            Approve
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Action buttons */}
              {(isAICTE || isAdmin) && selectedReq.status === 'Approved' && !selectedReq.noc_reference && (
                <div style={{ background: 'rgba(99,102,241,0.08)', padding: 12, borderRadius: 8, display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <label className="label">Record Approval Bureau NOC / Sanction Order</label>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <input
                      type="text"
                      className="input"
                      placeholder="e.g. AICTE/NOC/2026/8912"
                      value={nocRef}
                      onChange={(e) => setNocRef(e.target.value)}
                    />
                    <button
                      className="btn btn-primary"
                      onClick={() => nocMut.mutate({ reqId: selectedReq.id, noc_or_sanction: 'NOC', reference: nocRef })}
                      disabled={!nocRef}
                    >
                      Record NOC
                    </button>
                  </div>
                </div>
              )}

              {(isAICTE || isAdmin) && selectedReq.status === 'Approved' && (
                <button
                  className="btn btn-primary"
                  style={{ width: '100%' }}
                  onClick={() => closeMut.mutate(selectedReq.id)}
                  disabled={closeMut.isPending}
                >
                  <Unlock size={16} /> Execute Final FDR Release & Close
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* Modal: New Release Request */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 520 }}>
            <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16 }}>Request Security Deposit Release</h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label className="label">Select Security Deposit</label>
                <select
                  className="input"
                  value={createForm.deposit_id}
                  onChange={(e) => setCreateForm({ ...createForm, deposit_id: e.target.value })}
                >
                  <option value="">Select Deposit...</option>
                  {deposits.map((d: any) => (
                    <option key={d.id} value={d.id}>
                      {d.institution_name} — {d.programme} (₹{(d.required_amount / 100000).toFixed(1)}L)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="label">Amount Requested for Release (₹)</label>
                <input
                  type="number"
                  className="input"
                  value={createForm.amount}
                  onChange={(e) => setCreateForm({ ...createForm, amount: Number(e.target.value) })}
                />
              </div>

              <div>
                <label className="label">Release Justification / Reason</label>
                <textarea
                  className="input"
                  rows={3}
                  value={createForm.reason}
                  onChange={(e) => setCreateForm({ ...createForm, reason: e.target.value })}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 10 }}>
                <button className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>Cancel</button>
                <button
                  className="btn btn-primary"
                  onClick={() => createMut.mutate(createForm)}
                  disabled={!createForm.deposit_id || createMut.isPending}
                >
                  {createMut.isPending ? 'Submitting...' : 'Submit Request'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
