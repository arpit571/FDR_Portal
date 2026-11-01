"""FDRs router — CRUD, state machine transitions, and renew/replace."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.config.models import FDR, Deposit, Bank, Renewal
from src.auth.auth import (get_current_user, require_roles, has_role,
                           require_institution_scope,
                           SUPER_ADMIN, FINANCE_OFFICER, AICTE_OFFICER, AUDITOR, REVIEWER)
from src.audit.audit import write_audit
from src.modules.rules.engine import run_rules_for_fdr, has_blocking_discrepancies, RuleContext
from src.config.dates import today as get_today

router = APIRouter()

# ---------------------------------------------------------------------------
# Allowed FDR status transitions
# ---------------------------------------------------------------------------
ALLOWED_TRANSITIONS = {
    "Draft": ["Pending Document", "Active"],
    "Pending Document": ["Extracting", "Pending Review", "Active"],
    "Extracting": ["Pending Review", "Active"],
    "Pending Review": ["Active"],
    "Active": ["Maturity Alert", "Released", "Renewed", "Replaced", "Closed"],
    "Maturity Alert": ["Matured - Action Pending", "Renewed", "Replaced", "Released"],
    "Matured - Action Pending": ["Renewed", "Replaced", "Released", "Closed"],
    "Renewed": ["Closed"],
    "Replaced": ["Closed"],
    "Released": ["Closed"],
    "Closed": [],
}


class FDRCreate(BaseModel):
    deposit_id: str
    bank_id: str
    fdr_number: str
    principal: float
    rate: Optional[float] = None
    start_date: date
    maturity_date: date
    depositor_name: Optional[str] = None
    notes: Optional[str] = None
    kind: str = "ORIGINAL"


class FDRUpdate(BaseModel):
    bank_id: Optional[str] = None
    fdr_number: Optional[str] = None
    principal: Optional[float] = None
    rate: Optional[float] = None
    start_date: Optional[date] = None
    maturity_date: Optional[date] = None
    depositor_name: Optional[str] = None
    notes: Optional[str] = None


class TransitionRequest(BaseModel):
    to_status: str
    note: Optional[str] = None


class RenewRequest(BaseModel):
    kind: str  # RENEWAL | REPLACEMENT
    new_fdr: FDRCreate
    reason: Optional[str] = None


def fdr_dict(f: FDR):
    return {
        "id": f.id, "deposit_id": f.deposit_id,
        "bank_id": f.bank_id, "bank_name": f.bank.name if f.bank else None,
        "fdr_number": f.fdr_number, "principal": f.principal, "rate": f.rate,
        "start_date": str(f.start_date), "maturity_date": str(f.maturity_date),
        "depositor_name": f.depositor_name, "status": f.status,
        "document_id": f.document_id, "kind": f.kind,
        "replaces_fdr_id": f.replaces_fdr_id, "notes": f.notes,
        "created_at": str(f.created_at),
        "days_to_maturity": (f.maturity_date - get_today()).days if f.maturity_date else None,
    }


@router.get("")
def list_fdrs(
    status: Optional[str] = None,
    bank: Optional[str] = None,
    maturity_before: Optional[date] = None,
    institution: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(FDR).join(Deposit)
    if not has_role(current_user, SUPER_ADMIN, AICTE_OFFICER, AUDITOR):
        q = q.filter(Deposit.institution_id == current_user.institution_id)
    elif institution:
        q = q.filter(Deposit.institution_id == institution)
    if status:
        q = q.filter(FDR.status == status)
    if bank:
        q = q.filter(FDR.bank_id == bank)
    if maturity_before:
        q = q.filter(FDR.maturity_date <= maturity_before)
    return {"data": [fdr_dict(f) for f in q.all()]}


@router.post("", dependencies=[Depends(require_roles(SUPER_ADMIN, FINANCE_OFFICER))])
def create_fdr(body: FDRCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    dep = db.query(Deposit).filter(Deposit.id == body.deposit_id).first()
    if not dep:
        raise HTTPException(status_code=404, detail="Deposit not found")
    require_institution_scope(current_user, dep.institution_id)

    # Validate
    if body.principal <= 0:
        raise HTTPException(status_code=422, detail="Principal must be > 0")
    if body.maturity_date <= body.start_date:
        raise HTTPException(status_code=422, detail="Maturity date must be after start date")
    if body.rate is not None and (body.rate < 0 or body.rate > 15):
        raise HTTPException(status_code=422, detail="Rate must be between 0 and 15")

    fdr = FDR(**body.model_dump(), created_by=current_user.id, status="Draft")
    db.add(fdr)
    db.flush()

    # Build context and run rules
    inst = dep.institution
    all_fdrs = db.query(FDR).filter(FDR.deposit_id == dep.id).all()
    ctx = RuleContext(
        db=db, institution_name=inst.name,
        deposit_required_amount=dep.required_amount,
        all_fdrs=all_fdrs, demo_today=get_today(),
    )
    run_rules_for_fdr(fdr, ctx, db)

    write_audit(db, user_id=current_user.id, entity_type="fdr", entity_id=fdr.id,
                action="CREATE", after=fdr_dict(fdr))
    db.commit()
    db.refresh(fdr)
    return {"data": fdr_dict(fdr)}


@router.get("/{id}")
def get_fdr(id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    fdr = db.query(FDR).filter(FDR.id == id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR not found")
    dep = fdr.deposit
    require_institution_scope(current_user, dep.institution_id)
    return {"data": fdr_dict(fdr)}


@router.patch("/{id}", dependencies=[Depends(require_roles(SUPER_ADMIN, FINANCE_OFFICER))])
def update_fdr(id: str, body: FDRUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    fdr = db.query(FDR).filter(FDR.id == id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR not found")
    require_institution_scope(current_user, fdr.deposit.institution_id)
    before = fdr_dict(fdr)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(fdr, k, v)

    # Re-run rules after update
    dep = fdr.deposit
    inst = dep.institution
    all_fdrs = db.query(FDR).filter(FDR.deposit_id == dep.id).all()
    ctx = RuleContext(db=db, institution_name=inst.name,
                     deposit_required_amount=dep.required_amount,
                     all_fdrs=all_fdrs, demo_today=get_today())
    run_rules_for_fdr(fdr, ctx, db)

    write_audit(db, user_id=current_user.id, entity_type="fdr", entity_id=fdr.id,
                action="UPDATE", before=before, after=fdr_dict(fdr))
    db.commit()
    db.refresh(fdr)
    return {"data": fdr_dict(fdr)}


@router.post("/{id}/transition")
def transition_fdr(id: str, body: TransitionRequest, db: Session = Depends(get_db),
                   current_user=Depends(get_current_user)):
    fdr = db.query(FDR).filter(FDR.id == id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR not found")
    require_institution_scope(current_user, fdr.deposit.institution_id)

    allowed = ALLOWED_TRANSITIONS.get(fdr.status, [])
    if body.to_status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot transition from '{fdr.status}' to '{body.to_status}'. Allowed: {allowed}"
        )

    # Block activation on Critical discrepancies
    if body.to_status == "Active" and has_blocking_discrepancies(fdr.id, db):
        raise HTTPException(
            status_code=409,
            detail="Cannot activate FDR: open Critical-severity discrepancy cases exist. Resolve them first."
        )

    before_status = fdr.status
    fdr.status = body.to_status
    write_audit(db, user_id=current_user.id, entity_type="fdr", entity_id=fdr.id,
                action=f"TRANSITION_{before_status}_TO_{body.to_status}",
                before={"status": before_status}, after={"status": body.to_status, "note": body.note})
    db.commit()
    db.refresh(fdr)
    return {"data": fdr_dict(fdr)}


@router.post("/{id}/renew")
def renew_fdr(id: str, body: RenewRequest, db: Session = Depends(get_db),
              current_user=Depends(get_current_user)):
    if not has_role(current_user, SUPER_ADMIN, FINANCE_OFFICER):
        raise HTTPException(status_code=403, detail="Not authorized")
    old_fdr = db.query(FDR).filter(FDR.id == id).first()
    if not old_fdr:
        raise HTTPException(status_code=404, detail="FDR not found")
    require_institution_scope(current_user, old_fdr.deposit.institution_id)

    if old_fdr.status not in ("Active", "Maturity Alert", "Matured - Action Pending"):
        raise HTTPException(status_code=409, detail="Only Active or Matured FDRs can be renewed/replaced")

    # Create new FDR
    new_data = body.new_fdr.model_dump()
    new_data["deposit_id"] = old_fdr.deposit_id
    new_data["kind"] = body.kind
    new_data["replaces_fdr_id"] = old_fdr.id
    new_data["created_by"] = current_user.id
    new_data["status"] = "Pending Document"

    new_fdr = FDR(**new_data)
    db.add(new_fdr)
    db.flush()

    # Mark old FDR
    old_status = old_fdr.status
    old_fdr.status = "Renewed" if body.kind == "RENEWAL" else "Replaced"

    # Record renewal link
    renewal = Renewal(
        old_fdr_id=old_fdr.id, new_fdr_id=new_fdr.id,
        kind=body.kind, reason=body.reason, renewed_by=current_user.id,
    )
    db.add(renewal)

    write_audit(db, user_id=current_user.id, entity_type="fdr", entity_id=old_fdr.id,
                action=f"{body.kind}_OLD", before={"status": old_status},
                after={"status": old_fdr.status, "new_fdr_id": new_fdr.id})
    write_audit(db, user_id=current_user.id, entity_type="fdr", entity_id=new_fdr.id,
                action=f"{body.kind}_NEW", after=fdr_dict(new_fdr))
    db.commit()
    db.refresh(new_fdr)
    return {"data": {"old_fdr": fdr_dict(old_fdr), "new_fdr": fdr_dict(new_fdr)}}
