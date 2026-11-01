import React from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  getDashboardSummary, getMaturityCalendar, getCompliance,
  getAlerts, setDemoClock, runScheduler
} from '../api/client'
import { useAuth } from '../app/AuthContext'
import { KpiCard, StatusBadge, Spinner, EmptyState } from '../components/UI'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell
} from 'recharts'
import {
  Database, TrendingDown, Calendar, AlertTriangle, ShieldCheck,
  Clock, Bell, Zap, RefreshCw
} from 'lucide-react'

const fmtCurrency = (n: number) => `₹${(n / 100000).toFixed(1)}L`

export default function Dashboard() {
  const { isAICTE, isAdmin } = useAuth()

  const { data: summary, isLoading, refetch } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: getDashboardSummary,
    refetchInterval: 30000,
  })

  const { data: calendar } = useQuery({
    queryKey: ['maturity-calendar'],
    queryFn: () => getMaturityCalendar(90),
  })

  const { data: compliance } = useQuery({
    queryKey: ['compliance'],
    queryFn: getCompliance,
    enabled: isAICTE || isAdmin,
  })

  const { data: alerts } = useQuery({
    queryKey: ['alerts-unacked'],
    queryFn: () => getAlerts({ unacknowledged: true }),
  })

  const [clockLoading, setClockLoading] = React.useState(false)
  const [clockDays, setClockDays] = React.useState(30)

  const advanceClock = async () => {
    setClockLoading(true)
    try {
      await setDemoClock({ advance_days: clockDays })
      refetch()
    } finally {
      setClockLoading(false)
    }
  }

  if (isLoading) return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}>
      <Spinner size={32} />
    </div>
  )

  const s = summary || {}
  const discBySev = s.open_discrepancies_by_severity || {}
  const discChartData = ['Critical', 'High', 'Medium', 'Low'].map(sev => ({
    name: sev, count: discBySev[sev] || 0,
    color: sev === 'Critical' ? '#ef4444' : sev === 'High' ? '#f97316'
         : sev === 'Medium' ? '#eab308' : '#22c55e'
  })).filter(d => d.count > 0)

  const calendarEntries = Object.entries(calendar || {}).slice(0, 15)
  const statusData = Object.entries(s.status_breakdown || {}).map(([name, count]) => ({
    name, count
  }))

  return (
    <div className="fade-in">
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24 }}>
        <div className="page-header" style={{ marginBottom: 0 }}>
          <h2>Dashboard</h2>
          <p>FDR portfolio overview and pending actions</p>
        </div>

        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          {/* Demo date badge */}
          {s.demo_today && (
            <div className="demo-clock-pill">
              <Calendar size={13} />
              Demo: {s.demo_today}
            </div>
          )}

          {/* Demo clock controls (admin/aicte only) */}
          {isAdmin && (
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <select
                value={clockDays}
                onChange={e => setClockDays(+e.target.value)}
                className="form-control"
                style={{ width: 80, padding: '6px 8px', fontSize: 12 }}
              >
                {[7, 15, 30, 60, 90].map(d => (
                  <option key={d} value={d}>+{d}d</option>
                ))}
              </select>
              <button
                className="btn btn-secondary btn-sm"
                onClick={advanceClock}
                disabled={clockLoading}
                title="Advance demo clock"
              >
                {clockLoading ? <Spinner size={13} /> : <Zap size={13} />}
                Advance Clock
              </button>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => runScheduler().then(() => refetch())}
                title="Run scheduler now"
              >
                <RefreshCw size={13} />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="kpi-grid" style={{ marginBottom: 24 }}>
        <KpiCard
          icon={<Database size={20} />}
          label="Total FDR Principal"
          value={fmtCurrency(s.total_fdr_principal || 0)}
          sub={`${s.total_fdrs || 0} FDRs`}
          color="blue"
        />
        <KpiCard
          icon={<TrendingDown size={20} />}
          label="Total Shortfall"
          value={fmtCurrency(s.total_shortfall || 0)}
          sub={`Required: ${fmtCurrency(s.total_required || 0)}`}
          color={s.total_shortfall > 0 ? 'red' : 'green'}
        />
        <KpiCard
          icon={<Calendar size={20} />}
          label="Maturing in 30 Days"
          value={s.fdrs_maturing_in_30_days || 0}
          color={s.fdrs_maturing_in_30_days > 0 ? 'amber' : 'green'}
        />
        <KpiCard
          icon={<AlertTriangle size={20} />}
          label="Open Discrepancies"
          value={s.open_discrepancies || 0}
          sub={discBySev.Critical ? `${discBySev.Critical} Critical` : ''}
          color={discBySev.Critical > 0 ? 'red' : s.open_discrepancies > 0 ? 'amber' : 'green'}
        />
        <KpiCard
          icon={<ShieldCheck size={20} />}
          label="Pending Verifications"
          value={s.pending_verifications || 0}
          color={s.pending_verifications > 0 ? 'amber' : 'green'}
        />
        <KpiCard
          icon={<Bell size={20} />}
          label="Unacknowledged Alerts"
          value={s.unacknowledged_alerts || 0}
          sub={s.escalated_alerts > 0 ? `${s.escalated_alerts} Escalated` : ''}
          color={s.escalated_alerts > 0 ? 'red' : s.unacknowledged_alerts > 0 ? 'amber' : 'green'}
        />
        <KpiCard
          icon={<Clock size={20} />}
          label="Pending Approvals"
          value={s.pending_approvals || 0}
          color={s.pending_approvals > 0 ? 'amber' : 'green'}
        />
        <KpiCard
          icon={<Database size={20} />}
          label="Total Deposits"
          value={s.total_deposits || 0}
          color="purple"
        />
      </div>

      {/* Charts row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginBottom: 24 }}>
        {/* Status breakdown */}
        <div className="card">
          <div className="section-title">FDR Status Breakdown</div>
          {statusData.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {statusData.map(({ name, count }) => (
                <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <StatusBadge status={name} />
                  <div style={{
                    flex: 1, height: 6, background: 'rgba(255,255,255,0.06)',
                    borderRadius: 3, overflow: 'hidden'
                  }}>
                    <div style={{
                      height: '100%', borderRadius: 3,
                      background: '#3b82f6',
                      width: `${Math.min(100, ((count as number) / (s.total_fdrs || 1)) * 100)}%`
                    }} />
                  </div>
                  <span style={{ fontSize: 13, fontWeight: 600, color: '#94a3b8', minWidth: 24 }}>
                    {count as number}
                  </span>
                </div>
              ))}
            </div>
          ) : <EmptyState icon="📊" title="No FDRs yet" />}
        </div>

        {/* Discrepancy severity chart */}
        <div className="card">
          <div className="section-title">Open Discrepancies by Severity</div>
          {discChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={150}>
              <BarChart data={discChartData} barSize={28}>
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <YAxis hide />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }}
                  labelStyle={{ color: '#94a3b8' }}
                  itemStyle={{ color: '#e2e8f0' }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {discChartData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state" style={{ padding: '30px 0' }}>
              <div style={{ fontSize: 28 }}>✅</div>
              <p style={{ fontSize: 13, color: '#4ade80', marginTop: 8 }}>No open discrepancies</p>
            </div>
          )}
        </div>

        {/* Unacknowledged alerts */}
        <div className="card">
          <div className="section-title"><Bell size={14} /> Recent Alerts</div>
          {alerts && alerts.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {alerts.slice(0, 6).map((a: any) => (
                <div key={a.id} style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '8px 10px', background: 'rgba(255,255,255,0.03)',
                  borderRadius: 8, border: a.escalated ? '1px solid rgba(239,68,68,0.3)' : '1px solid transparent'
                }}>
                  <div style={{
                    width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                    background: a.escalated ? '#ef4444' : '#f59e0b',
                  }} className={a.escalated ? 'pulse-red' : ''} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="truncate" style={{ fontSize: 12, fontWeight: 600, color: '#e2e8f0' }}>
                      {a.alert_type.replace('_', ' ')} — {a.fdr_number}
                    </div>
                    <div style={{ fontSize: 11, color: '#475569' }}>
                      Maturity: {a.maturity_date}
                      {a.escalated && <span style={{ color: '#f87171', marginLeft: 6 }}>ESCALATED</span>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : <EmptyState icon="🔔" title="No pending alerts" />}
        </div>
      </div>

      {/* Maturity Calendar */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="section-title"><Calendar size={14} /> Maturity Calendar (Next 90 Days)</div>
        {calendarEntries.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {(calendarEntries as [string, any[]][]).map(([dateStr, fdrs]) => {
              const daysLeft = Math.round((new Date(dateStr).getTime() - Date.now()) / 86400000)
              return (
                <div key={dateStr} style={{
                  display: 'flex', alignItems: 'center', gap: 16,
                  padding: '10px 14px', background: 'rgba(255,255,255,0.02)',
                  borderRadius: 8, border: '1px solid rgba(255,255,255,0.04)'
                }}>
                  <div style={{ width: 80, flexShrink: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: daysLeft <= 7 ? '#f87171' : daysLeft <= 30 ? '#fbbf24' : '#e2e8f0' }}>
                      {dateStr}
                    </div>
                    <div style={{ fontSize: 11, color: '#475569' }}>
                      {daysLeft} days left
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {fdrs.map((f: any) => (
                      <div key={f.id} style={{
                        padding: '4px 10px', borderRadius: 6,
                        background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)',
                        fontSize: 12, color: '#93c5fd'
                      }}>
                        {f.fdr_number} — ₹{(f.principal / 100000).toFixed(1)}L
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        ) : <EmptyState icon="📅" title="No FDRs maturing in next 90 days" />}
      </div>

      {/* Compliance (AICTE/Admin only) */}
      {(isAICTE || isAdmin) && compliance && compliance.length > 0 && (
        <div className="card">
          <div className="section-title">Institution Compliance Scores</div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Institution</th>
                <th>Score</th>
                <th>Open Discrepancies</th>
                <th>Overdue Steps</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {compliance.map((c: any) => (
                <tr key={c.institution_id}>
                  <td>{c.institution_name}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{
                        width: 80, height: 8, background: 'rgba(255,255,255,0.06)',
                        borderRadius: 4, overflow: 'hidden'
                      }}>
                        <div style={{
                          height: '100%', borderRadius: 4,
                          background: c.score >= 80 ? '#22c55e' : c.score >= 60 ? '#f59e0b' : '#ef4444',
                          width: `${c.score}%`
                        }} />
                      </div>
                      <span style={{ fontWeight: 700, color: c.score >= 80 ? '#4ade80' : c.score >= 60 ? '#fbbf24' : '#f87171' }}>
                        {c.score}
                      </span>
                    </div>
                  </td>
                  <td>{c.open_discrepancies}</td>
                  <td>{c.overdue_steps}</td>
                  <td>
                    <span className={`badge ${c.score >= 80 ? 'active' : c.score >= 60 ? 'alert' : 'critical'}`}>
                      {c.score >= 80 ? 'Good' : c.score >= 60 ? 'Review' : 'Critical'}
                    </span>
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
