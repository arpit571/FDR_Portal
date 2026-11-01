import { useState } from 'react'
import { downloadReport } from '../api/client'
import { BarChart3, FileSpreadsheet, FileText, Download, CheckCircle, ShieldAlert, Calendar } from 'lucide-react'

export default function Reports() {
  const [downloading, setDownloading] = useState<string | null>(null)
  const [success, setSuccess] = useState('')

  const handleDownload = async (key: string, path: string, params: any) => {
    setDownloading(key)
    try {
      await downloadReport(path, params)
      setSuccess(`Report generated and downloaded successfully.`)
      setTimeout(() => setSuccess(''), 4000)
    } catch (err: any) {
      alert('Failed to generate report. Make sure backend is running.')
    } finally {
      setDownloading(null)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h2>Regulatory Reports & Analytics</h2>
        <p>Export official AICTE compliance documents, maturity forecasts, and full discrepancy summaries.</p>
      </div>

      {success && (
        <div style={{
          padding: '10px 16px', background: 'rgba(34,197,94,0.15)',
          border: '1px solid rgba(34,197,94,0.3)', borderRadius: 8,
          color: '#4ade80', marginBottom: 20, fontSize: 13, display: 'flex', alignItems: 'center', gap: 8
        }}>
          <CheckCircle size={16} /> {success}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 20 }}>
        {/* Card 1: FDR Register */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: 'rgba(59,130,246,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#60a5fa' }}>
              <BarChart3 size={20} />
            </div>
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 700 }}>Official FDR Register</h3>
              <p style={{ fontSize: 12, color: '#94a3b8' }}>Comprehensive institutional FDR master record</p>
            </div>
          </div>
          <p style={{ fontSize: 13, color: '#cbd5e1', lineHeight: 1.5 }}>
            Master regulatory ledger listing all security deposits, issuing banks, principal amounts, interest rates, issue/maturity dates, and validity states.
          </p>
          <div style={{ display: 'flex', gap: 10, marginTop: 'auto', paddingTop: 10 }}>
            <button
              className="btn btn-secondary"
              style={{ flex: 1 }}
              onClick={() => handleDownload('fdr-csv', 'fdr-register', { format: 'csv' })}
              disabled={downloading === 'fdr-csv'}
            >
              <FileSpreadsheet size={15} color="#22c55e" />
              {downloading === 'fdr-csv' ? 'Exporting...' : 'Export CSV'}
            </button>
            <button
              className="btn btn-primary"
              style={{ flex: 1 }}
              onClick={() => handleDownload('fdr-pdf', 'fdr-register', { format: 'pdf' })}
              disabled={downloading === 'fdr-pdf'}
            >
              <FileText size={15} />
              {downloading === 'fdr-pdf' ? 'Generating...' : 'Export PDF'}
            </button>
          </div>
        </div>

        {/* Card 2: Maturity Forecast */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: 'rgba(16,185,129,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#34d399' }}>
              <Calendar size={20} />
            </div>
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 700 }}>6-Month Maturity Forecast</h3>
              <p style={{ fontSize: 12, color: '#94a3b8' }}>Timeline & risk of impending maturities</p>
            </div>
          </div>
          <p style={{ fontSize: 13, color: '#cbd5e1', lineHeight: 1.5 }}>
            Executive forecast highlighting all FDRs maturing within the upcoming 180-day window, grouped by institution and days remaining to preempt security lapses.
          </p>
          <div style={{ marginTop: 'auto', paddingTop: 10 }}>
            <button
              className="btn btn-primary"
              style={{ width: '100%' }}
              onClick={() => handleDownload('forecast-pdf', 'maturity-forecast', { format: 'pdf' })}
              disabled={downloading === 'forecast-pdf'}
            >
              <Download size={15} />
              {downloading === 'forecast-pdf' ? 'Generating Report...' : 'Download Forecast (PDF)'}
            </button>
          </div>
        </div>

        {/* Card 3: Discrepancy Summary */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: 'rgba(239,68,68,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#f87171' }}>
              <ShieldAlert size={20} />
            </div>
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 700 }}>Discrepancies & Violations</h3>
              <p style={{ fontSize: 12, color: '#94a3b8' }}>Audit report of compliance non-conformities</p>
            </div>
          </div>
          <p style={{ fontSize: 13, color: '#cbd5e1', lineHeight: 1.5 }}>
            Detailed breakdown of flagged discrepancies across all 15 compliance rules, including critical tenure violations, unapproved banks, and encumbrances.
          </p>
          <div style={{ marginTop: 'auto', paddingTop: 10 }}>
            <button
              className="btn btn-secondary"
              style={{ width: '100%' }}
              onClick={() => handleDownload('disc-csv', 'discrepancies', { format: 'csv' })}
              disabled={downloading === 'disc-csv'}
            >
              <FileSpreadsheet size={15} color="#22c55e" />
              {downloading === 'disc-csv' ? 'Exporting...' : 'Export Discrepancies (CSV)'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

