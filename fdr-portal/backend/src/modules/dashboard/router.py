"""Dashboard router — KPIs, maturity calendar, compliance scores."""
from fastapi import APIRouter, Depends
from typing import Optional
from datetime import timedelta
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.config.models import (
    FDR, Deposit, DiscrepancyCase, Alert, BankVerification,
    ReleaseRequest, ApprovalStep, Institution
)
from src.auth.auth import get_current_user, has_role
from src.auth.auth import SUPER_ADMIN, AICTE_OFFICER, AUDITOR
from src.config.dates import today as get_today

router = APIRouter()


def get_institution_filter(current_user, db):
    """Return institution_id filter or None for admins."""
    if has_role(current_user, SUPER_ADMIN, AICTE_OFFICER, AUDITOR):
        return None
    return current_user.institution_id


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    today = get_today()
    inst_filter = get_institution_filter(current_user, db)
    in_30 = today + timedelta(days=30)

    # Base FDR query
    fdr_q = db.query(FDR).join(Deposit)
    dep_q = db.query(Deposit)
    if inst_filter:
        fdr_q = fdr_q.filter(Deposit.institution_id == inst_filter)
        dep_q = dep_q.filter(Deposit.institution_id == inst_filter)

    fdrs = fdr_q.all()
    deposits = dep_q.all()

    total_principal = sum(
        f.principal for f in fdrs if f.status in ("Active", "Maturity Alert")
    )
    total_required = sum(d.required_amount for d in deposits)
    total_shortfall = max(0, total_required - total_principal)

    maturing_30 = sum(
        1 for f in fdrs
        if f.maturity_date and today <= f.maturity_date <= in_30
        and f.status in ("Active", "Maturity Alert")
    )

    # Discrepancy counts by severity
    disc_q = db.query(DiscrepancyCase).filter(DiscrepancyCase.status.in_(["Open", "Under Review"]))
    if inst_filter:
        disc_q = (disc_q.join(FDR, DiscrepancyCase.fdr_id == FDR.id)
                       .join(Deposit, FDR.deposit_id == Deposit.id)
                       .filter(Deposit.institution_id == inst_filter))
    open_discs = disc_q.all()
    disc_by_severity = {}
    for d in open_discs:
        disc_by_severity[d.severity] = disc_by_severity.get(d.severity, 0) + 1

    # Pending verifications
    ver_q = db.query(BankVerification).filter(
        BankVerification.status.in_(["SUBMITTED", "CERTIFICATE_UPLOADED", "PENDING"])
    )
    if inst_filter:
        ver_q = (ver_q.join(FDR, BankVerification.fdr_id == FDR.id)
                      .join(Deposit, FDR.deposit_id == Deposit.id)
                      .filter(Deposit.institution_id == inst_filter))
    pending_verifications = ver_q.count()

    # Pending approvals (overdue steps)
    approvals_q = db.query(ApprovalStep).filter(
        ApprovalStep.decision == None,
    )
    pending_approvals = approvals_q.count()

    # Status buckets
    status_counts = {}
    for f in fdrs:
        status_counts[f.status] = status_counts.get(f.status, 0) + 1

    # Unacknowledged alerts
    alert_q = db.query(Alert).filter(Alert.acknowledged_by == None)
    if inst_filter:
        alert_q = (alert_q.join(FDR, Alert.fdr_id == FDR.id)
                          .join(Deposit, FDR.deposit_id == Deposit.id)
                          .filter(Deposit.institution_id == inst_filter))
    unacked_alerts = alert_q.count()
    escalated_alerts = alert_q.filter(Alert.escalated == True).count()

    return {"data": {
        "total_deposits": len(deposits),
        "total_fdrs": len(fdrs),
        "total_fdr_principal": total_principal,
        "total_required": total_required,
        "total_shortfall": total_shortfall,
        "fdrs_maturing_in_30_days": maturing_30,
        "open_discrepancies": len(open_discs),
        "open_discrepancies_by_severity": disc_by_severity,
        "pending_verifications": pending_verifications,
        "pending_approvals": pending_approvals,
        "unacknowledged_alerts": unacked_alerts,
        "escalated_alerts": escalated_alerts,
        "status_breakdown": status_counts,
        "demo_today": str(today),
    }}


@router.get("/maturity-calendar")
def maturity_calendar(
    days: int = 90,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    today = get_today()
    end = today + timedelta(days=days)
    inst_filter = get_institution_filter(current_user, db)

    q = db.query(FDR).join(Deposit).filter(
        FDR.maturity_date >= today, FDR.maturity_date <= end,
        FDR.status.in_(["Active", "Maturity Alert", "Pending Review"])
    )
    if inst_filter:
        q = q.filter(Deposit.institution_id == inst_filter)

    fdrs = q.order_by(FDR.maturity_date).all()
    # Group by date
    calendar = {}
    for f in fdrs:
        key = str(f.maturity_date)
        if key not in calendar:
            calendar[key] = []
        calendar[key].append({
            "id": f.id, "fdr_number": f.fdr_number,
            "principal": f.principal, "status": f.status,
            "days_left": (f.maturity_date - today).days,
        })
    return {"data": calendar}


@router.get("/compliance")
def compliance_scores(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Per-institution compliance score (AICTE/Admin view only)."""
    if not has_role(current_user, SUPER_ADMIN, AICTE_OFFICER, AUDITOR):
        return {"data": []}

    institutions = db.query(Institution).filter(Institution.approved == True).all()
    scores = []
    today = get_today()

    for inst in institutions:
        penalty = 0
        fdrs = (db.query(FDR).join(Deposit)
                .filter(Deposit.institution_id == inst.id).all())

        # Discrepancy penalties
        open_cases = (
            db.query(DiscrepancyCase)
            .join(FDR, DiscrepancyCase.fdr_id == FDR.id)
            .join(Deposit, FDR.deposit_id == Deposit.id)
            .filter(Deposit.institution_id == inst.id, DiscrepancyCase.status.in_(["Open", "Under Review"]))
            .all()
        )
        for c in open_cases:
            penalty += {"Critical": 20, "High": 10, "Medium": 5, "Low": 2}.get(c.severity, 0)

        # Overdue approval steps
        overdue = (
            db.query(ApprovalStep)
            .join(ReleaseRequest, ApprovalStep.request_id == ReleaseRequest.id)
            .join(Deposit, ReleaseRequest.deposit_id == Deposit.id)
            .filter(Deposit.institution_id == inst.id, ApprovalStep.decision == None)
            .all()
        )
        for s in overdue:
            if s.due_at and s.due_at.date() < today:
                penalty += 5

        score = max(0, 100 - penalty)
        scores.append({
            "institution_id": inst.id,
            "institution_name": inst.name,
            "score": score,
            "penalty": penalty,
            "open_discrepancies": len(open_cases),
            "overdue_steps": sum(1 for s in overdue if s.due_at and s.due_at.date() < today),
        })

    scores.sort(key=lambda x: x["score"])
    return {"data": scores}
