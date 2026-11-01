"""Alerts router."""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.config.models import Alert, FDR, Deposit
from src.auth.auth import get_current_user, has_role
from src.auth.auth import SUPER_ADMIN, AICTE_OFFICER, AUDITOR

router = APIRouter()


def alert_dict(a: Alert):
    fdr = a.fdr
    return {
        "id": a.id, "fdr_id": a.fdr_id,
        "fdr_number": fdr.fdr_number if fdr else None,
        "maturity_date": str(fdr.maturity_date) if fdr else None,
        "alert_type": a.alert_type, "scheduled_for": str(a.scheduled_for),
        "channel": a.channel, "sent_at": str(a.sent_at) if a.sent_at else None,
        "acknowledged_by": a.acknowledged_by,
        "acknowledged_at": str(a.acknowledged_at) if a.acknowledged_at else None,
        "escalated": a.escalated,
    }


@router.get("")
def list_alerts(
    fdr_id: Optional[str] = None,
    unacknowledged: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(Alert)
    if not has_role(current_user, SUPER_ADMIN, AICTE_OFFICER, AUDITOR):
        q = (q.join(FDR, Alert.fdr_id == FDR.id)
               .join(Deposit, FDR.deposit_id == Deposit.id)
               .filter(Deposit.institution_id == current_user.institution_id))
    if fdr_id:
        q = q.filter(Alert.fdr_id == fdr_id)
    if unacknowledged:
        q = q.filter(Alert.acknowledged_by == None)
    return {"data": [alert_dict(a) for a in q.order_by(Alert.scheduled_for.desc()).all()]}


@router.post("/{id}/acknowledge")
def acknowledge_alert(id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    alert = db.query(Alert).filter(Alert.id == id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.acknowledged_by = current_user.id
    alert.acknowledged_at = datetime.utcnow()
    db.commit()
    return {"data": alert_dict(alert)}
