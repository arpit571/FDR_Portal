"""Renewals router — list renewal chains."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.config.models import Renewal, FDR, Deposit
from src.auth.auth import get_current_user, has_role
from src.auth.auth import SUPER_ADMIN, AICTE_OFFICER, AUDITOR

router = APIRouter()


@router.get("")
def list_renewals(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    q = db.query(Renewal)
    if not has_role(current_user, SUPER_ADMIN, AICTE_OFFICER, AUDITOR):
        q = (q.join(FDR, Renewal.old_fdr_id == FDR.id)
               .join(Deposit, FDR.deposit_id == Deposit.id)
               .filter(Deposit.institution_id == current_user.institution_id))
    renewals = q.order_by(Renewal.renewed_on.desc()).all()
    result = []
    for r in renewals:
        result.append({
            "id": r.id, "kind": r.kind, "reason": r.reason,
            "renewed_on": str(r.renewed_on),
            "old_fdr": {
                "id": r.old_fdr.id, "fdr_number": r.old_fdr.fdr_number,
                "maturity_date": str(r.old_fdr.maturity_date), "status": r.old_fdr.status,
                "principal": r.old_fdr.principal,
            } if r.old_fdr else None,
            "new_fdr": {
                "id": r.new_fdr.id, "fdr_number": r.new_fdr.fdr_number,
                "maturity_date": str(r.new_fdr.maturity_date), "status": r.new_fdr.status,
                "principal": r.new_fdr.principal,
            } if r.new_fdr else None,
        })
    return {"data": result}
