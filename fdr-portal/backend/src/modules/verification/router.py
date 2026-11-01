"""Bank verification router — Certificate 3 fields, statuses, and AICTE decision."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.config.models import BankVerification, FDR, Deposit
from src.auth.auth import (get_current_user, has_role, require_institution_scope,
                           SUPER_ADMIN, FINANCE_OFFICER, AICTE_OFFICER, REVIEWER, AUDITOR)
from src.audit.audit import write_audit

router = APIRouter()


class VerificationCreate(BaseModel):
    account_holder: Optional[str] = None
    account_number_masked: Optional[str] = None
    bank_name: Optional[str] = None
    bank_address: Optional[str] = None
    account_authentic: Optional[bool] = None
    balance_confirmed: Optional[bool] = None
    certified_fdr_number: Optional[str] = None
    certified_deposit_date: Optional[date] = None
    certified_maturity_date: Optional[date] = None
    certified_amount: Optional[float] = None
    belongs_to_institution: Optional[bool] = None
    is_authentic: Optional[bool] = None
    loan_or_mortgage: Optional[bool] = None
    remarks: Optional[str] = None


class DecideBody(BaseModel):
    decision: str   # VERIFIED | DISCREPANCY_DETECTED | REJECTED
    remarks: Optional[str] = None


def ver_dict(v: BankVerification):
    return {
        "id": v.id, "fdr_id": v.fdr_id, "status": v.status,
        "account_holder": v.account_holder,
        "account_number_masked": v.account_number_masked,
        "bank_name": v.bank_name, "bank_address": v.bank_address,
        "account_authentic": v.account_authentic,
        "balance_confirmed": v.balance_confirmed,
        "certified_fdr_number": v.certified_fdr_number,
        "certified_deposit_date": str(v.certified_deposit_date) if v.certified_deposit_date else None,
        "certified_maturity_date": str(v.certified_maturity_date) if v.certified_maturity_date else None,
        "certified_amount": v.certified_amount,
        "belongs_to_institution": v.belongs_to_institution,
        "is_authentic": v.is_authentic,
        "loan_or_mortgage": v.loan_or_mortgage,
        "verified_by": v.verified_by,
        "verified_at": str(v.verified_at) if v.verified_at else None,
        "remarks": v.remarks, "created_at": str(v.created_at),
    }


@router.get("/fdrs/{fdr_id}/verification")
def get_verification(fdr_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR not found")
    require_institution_scope(current_user, fdr.deposit.institution_id)
    if not fdr.verification:
        return {"data": None}
    return {"data": ver_dict(fdr.verification)}


@router.post("/fdrs/{fdr_id}/verification")
def create_or_update_verification(
    fdr_id: str, body: VerificationCreate,
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
):
    if not has_role(current_user, SUPER_ADMIN, FINANCE_OFFICER, REVIEWER, AICTE_OFFICER):
        raise HTTPException(status_code=403, detail="Not authorized")
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR not found")
    require_institution_scope(current_user, fdr.deposit.institution_id)

    v = fdr.verification
    if not v:
        v = BankVerification(fdr_id=fdr_id, status="SUBMITTED", submitted_by=current_user.id)
        db.add(v)

    before = ver_dict(v) if v.id else None
    for k, val in body.model_dump(exclude_none=True).items():
        setattr(v, k, val)
    # If bank cert details submitted, move to CERTIFICATE_UPLOADED
    if body.certified_fdr_number and v.status == "SUBMITTED":
        v.status = "CERTIFICATE_UPLOADED"

    write_audit(db, user_id=current_user.id, entity_type="bank_verification", entity_id=fdr_id,
                action="SUBMIT_CERTIFICATE", before=before, after=ver_dict(v))
    db.commit()
    db.refresh(v)
    return {"data": ver_dict(v)}


@router.post("/fdrs/{fdr_id}/verification/decide")
def decide_verification(
    fdr_id: str, body: DecideBody,
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
):
    """Only AICTE Officer can set VERIFIED / DISCREPANCY_DETECTED / REJECTED."""
    if not has_role(current_user, SUPER_ADMIN, AICTE_OFFICER):
        raise HTTPException(status_code=403, detail="Only AICTE Officer can verify bank certificates")
    if body.decision not in ("VERIFIED", "DISCREPANCY_DETECTED", "REJECTED"):
        raise HTTPException(status_code=422, detail="Decision must be VERIFIED, DISCREPANCY_DETECTED, or REJECTED")

    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR not found")
    v = fdr.verification
    if not v:
        raise HTTPException(status_code=404, detail="No verification record found")

    before = ver_dict(v)
    v.status = body.decision
    if body.remarks:
        v.remarks = body.remarks
    v.verified_by = current_user.id
    v.verified_at = datetime.utcnow()

    # Run R13 if DISCREPANCY_DETECTED
    if body.decision == "DISCREPANCY_DETECTED":
        from src.modules.rules.engine import run_rules_for_fdr, RuleContext
        from src.config.dates import today as get_today
        from src.config.models import FDR as FDRM
        all_fdrs = db.query(FDRM).filter(FDRM.deposit_id == fdr.deposit_id).all()
        ctx = RuleContext(db=db, institution_name=fdr.deposit.institution.name,
                         deposit_required_amount=fdr.deposit.required_amount,
                         all_fdrs=all_fdrs, verification=v, demo_today=get_today())
        run_rules_for_fdr(fdr, ctx, db)

    write_audit(db, user_id=current_user.id, entity_type="bank_verification", entity_id=fdr_id,
                action=f"DECIDE_{body.decision}", before=before, after=ver_dict(v))
    db.commit()
    db.refresh(v)
    return {"data": ver_dict(v)}
