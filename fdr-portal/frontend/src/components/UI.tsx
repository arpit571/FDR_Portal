import React from 'react'
import clsx from 'clsx'

// ─── Status Badge ───────────────────────────────────────────────────────────

const STATUS_LABELS: Record<string, string> = {
  'Matured - Action Pending': 'Matured',
  'Pending Document': 'Pending Doc',
  'Pending Review': 'Pending Review',
  'Maturity Alert': 'Maturity Alert',
}

export function StatusBadge({ status }: { status: string }) {
  const slug = status.toLowerCase().replace(/[\s/]/g, '-').replace(/[^a-z0-9-]/g, '')
  const label = STATUS_LABELS[status] || status
  return (
    <span className={clsx('badge', slug)}>
      <span className="badge-dot" />
      {label}
    </span>
  )
}

// ─── Severity Badge ──────────────────────────────────────────────────────────

export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span className={clsx('badge', severity.toLowerCase())}>
      {severity}
    </span>
  )
}

// ─── Confidence Chip ─────────────────────────────────────────────────────────

export function ConfidenceChip({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100)
  const level = pct >= 90 ? 'high' : pct >= 80 ? 'medium' : 'low'
  return (
    <span className={clsx('conf-chip', level)}>
      {pct}%
    </span>
  )
}

// ─── Currency ───────────────────────────────────────────────────────────────

export function Currency({ amount }: { amount: number }) {
  const lakh = amount / 100000
  return <span>₹{lakh.toFixed(1)}L</span>
}

// ─── Spinner ────────────────────────────────────────────────────────────────

export function Spinner({ size = 20 }: { size?: number }) {
  return <span className="spinner" style={{ width: size, height: size }} />
}

// ─── Empty State ─────────────────────────────────────────────────────────────

export function EmptyState({ icon = '📋', title = 'No records', desc = '' }: {
  icon?: string; title?: string; desc?: string
}) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">{icon}</div>
      <h3>{title}</h3>
      {desc && <p>{desc}</p>}
    </div>
  )
}

// ─── KPI Card ────────────────────────────────────────────────────────────────

export function KpiCard({
  icon, label, value, sub, color = 'blue'
}: {
  icon: React.ReactNode
  label: string
  value: string | number
  sub?: string
  color?: 'blue' | 'green' | 'amber' | 'red' | 'purple'
}) {
  return (
    <div className={clsx('kpi-card', color)}>
      <div className={clsx('kpi-icon', color)}>{icon}</div>
      <div className="kpi-value">{value}</div>
      <div className="kpi-label">{label}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  )
}

// ─── Section title ───────────────────────────────────────────────────────────

export function SectionTitle({ children, icon }: { children: React.ReactNode; icon?: React.ReactNode }) {
  return (
    <div className="section-title">
      {icon}
      {children}
    </div>
  )
}
