import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getReviewQueue, reviewOCRField } from '../api/client'
import { useAuth } from '../app/AuthContext'
import { ConfidenceChip, EmptyState, Spinner } from '../components/UI'
import { Check } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function ReviewQueue() {
  const qc = useQueryClient()
  const { isReviewer, isAdmin } = useAuth()
  const [edits, setEdits] = useState<Record<string, string>>({})
  const [successMsg, setSuccessMsg] = useState('')

  const { data: queue = [], isLoading } = useQuery({
    queryKey: ['review-queue'],
    queryFn: getReviewQueue,
  })

  const reviewMut = useMutation({
    mutationFn: ({ fieldId, val }: { fieldId: string; val: string }) => reviewOCRField(fieldId, val),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['review-queue'] })
      setSuccessMsg('OCR field updated and confirmed successfully.')
      setTimeout(() => setSuccessMsg(''), 4000)
    }
  })

  const handleConfirm = (fieldId: string, fallbackVal: string) => {
    const val = edits[fieldId] !== undefined ? edits[fieldId] : fallbackVal
    reviewMut.mutate({ fieldId, val })
  }

  return (
    <div>
      <div className="page-header">
        <h2>OCR Human-in-the-Loop Review Queue</h2>
        <p>Review low-confidence fields extracted from scanned FDR documents before automated verification.</p>
      </div>

      {successMsg && (
        <div style={{ padding: '10px 16px', background: 'rgba(34,197,94,0.15)', border: '1px solid rgba(34,197,94,0.3)', borderRadius: 8, color: '#4ade80', marginBottom: 16, fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Check size={16} /> {successMsg}
        </div>
      )}

      {isLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><Spinner size={32} /></div>
      ) : queue.length === 0 ? (
        <EmptyState icon="✅" title="Review Queue is Clean" desc="No low-confidence OCR extractions pending human scrutiny." />
      ) : (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>FDR Reference</th>
                <th>Field Name</th>
                <th>Extracted Value</th>
                <th>Confidence</th>
                <th>Human Correction / Value</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {queue.map((item: any) => {
                const currentVal = edits[item.id] !== undefined ? edits[item.id] : item.extracted_value

                return (
                  <tr key={item.id}>
                    <td>
                      <Link to={`/fdrs/${item.fdr_id}`} style={{ fontWeight: 600, color: '#6366f1', textDecoration: 'none' }}>
                        {item.fdr_number || 'View FDR'}
                      </Link>
                    </td>
                    <td>
                      <span style={{ fontWeight: 600, color: '#e2e8f0', textTransform: 'capitalize' }}>
                        {item.field_name.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td>
                      <code style={{ background: 'rgba(255,255,255,0.06)', padding: '3px 6px', borderRadius: 4, color: '#cbd5e1' }}>
                        {item.extracted_value || '(blank)'}
                      </code>
                    </td>
                    <td>
                      <ConfidenceChip confidence={item.confidence} />
                    </td>
                    <td>
                      <input
                        type="text"
                        className="input"
                        value={currentVal}
                        onChange={(e) => setEdits({ ...edits, [item.id]: e.target.value })}
                        disabled={!isReviewer && !isAdmin}
                        style={{ maxWidth: 220, padding: '4px 8px', fontSize: 13 }}
                      />
                    </td>
                    <td>
                      {(isReviewer || isAdmin) ? (
                        <button
                          className="btn btn-primary"
                          style={{ padding: '4px 12px', fontSize: 12 }}
                          onClick={() => handleConfirm(item.id, item.extracted_value)}
                          disabled={reviewMut.isPending}
                        >
                          <Check size={14} /> Confirm
                        </button>
                      ) : (
                        <span style={{ fontSize: 12, color: '#64748b' }}>Reviewer required</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
