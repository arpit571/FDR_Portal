"""Discrepancy rules and cases router."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.config.models import DiscrepancyRule, DiscrepancyCase, FDR, Deposit
from src.auth.auth import (get_current_user, has_role, require_roles, require_institution_scope,
                           SUPER_ADMIN, FINANCE_OFFICER, REVIEWER, AICTE_OFFICER, AUDITOR)
from src.audit.audit import write_audit

router = APIRouter()


class RuleUpdate(BaseModel):
    enabled: Optional[bool] = None
    severity: Optional[str] = None
    description: Optional[str] = None


class ResolveBody(BaseModel):
    note: str


class WaiveBody(BaseModel):
    note: str


def case_dict(c: DiscrepancyCase):
    return {
        "id": c.id, "fdr_id": c.fdr_id,
        "rule_id": c.rule_id,
        "rule_code": c.rule.code if c.rule else None,
        "rule_description": c.rule.description if c.rule else None,
        "rule_source": c.rule.source_ref if c.rule else None,
        "severity": c.severity, "status": c.status,
        "message": c.message, "details": c.details,
        "opened_at": str(c.opened_at) if c.opened_at else None,
        "resolved_by": c.resolved_by, "resolution_note": c.resolution_note,
        "waived_by": c.waived_by,
        "created_at": str(c.created_at),
    }


@router.get("")
def list_cases(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(DiscrepancyCase)
    if not has_role(current_user, SUPER_ADMIN, AICTE_OFFICER, AUDITOR):
        # Scope to institution
        q = (q.join(FDR, DiscrepancyCase.fdr_id == FDR.id)
               .join(Deposit, FDR.deposit_id == Deposit.id)
               .filter(Deposit.institution_id == current_user.institution_id))
    if status:
        q = q.filter(DiscrepancyCase.status == status)
    if severity:
        q = q.filter(DiscrepancyCase.severity == severity)
    cases = q.order_by(DiscrepancyCase.opened_at.desc()).all()
    return {"data": [case_dict(c) for c in cases]}


@router.get("/{id}")
def get_case(id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    case = db.query(DiscrepancyCase).filter(DiscrepancyCase.id == id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    fdr = db.query(FDR).filter(FDR.id == case.fdr_id).first()
    if fdr:
        require_institution_scope(current_user, fdr.deposit.institution_id)
    return {"data": case_dict(case)}


@router.post("/{id}/resolve")
def resolve_case(id: str, body: ResolveBody, db: Session = Depends(get_db),
                 current_user=Depends(get_current_user)):
    case = db.query(DiscrepancyCase).filter(DiscrepancyCase.id == id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    fdr = db.query(FDR).filter(FDR.id == case.fdr_id).first()
    if fdr:
        require_institution_scope(current_user, fdr.deposit.institution_id)
    if case.status not in ("Open", "Under Review"):
        raise HTTPException(status_code=409, detail="Case is already resolved or waived")
    before = {"status": case.status}
    case.status = "Resolved"
    case.resolved_by = current_user.id
    case.resolved_at = datetime.utcnow()
    case.resolution_note = body.note
    write_audit(db, user_id=current_user.id, entity_type="discrepancy_case", entity_id=case.id,
                action="RESOLVE", before=before, after={"status": "Resolved", "note": body.note})
    db.commit()
    return {"data": case_dict(case)}


@router.post("/{id}/waive")
def waive_case(id: str, body: WaiveBody, db: Session = Depends(get_db),
               current_user=Depends(get_current_user)):
    if not has_role(current_user, SUPER_ADMIN, AICTE_OFFICER):
        raise HTTPException(status_code=403, detail="Only AICTE Officer can waive discrepancy cases")
    case = db.query(DiscrepancyCase).filter(DiscrepancyCase.id == id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.status not in ("Open", "Under Review"):
        raise HTTPException(status_code=409, detail="Case is already resolved or waived")
    before = {"status": case.status}
    case.status = "Waived"
    case.waived_by = current_user.id
    case.waived_at = datetime.utcnow()
    case.resolution_note = body.note
    write_audit(db, user_id=current_user.id, entity_type="discrepancy_case", entity_id=case.id,
                action="WAIVE", before=before, after={"status": "Waived", "note": body.note})
    db.commit()
    return {"data": case_dict(case)}


# Rules management
@router.get("/rules/list")
def list_rules(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rules = db.query(DiscrepancyRule).order_by(DiscrepancyRule.code).all()
    return {"data": [
        {"id": r.id, "code": r.code, "description": r.description,
         "severity": r.severity, "enabled": r.enabled, "source_ref": r.source_ref,
         "owner_role": r.owner_role}
        for r in rules
    ]}


@router.patch("/rules/{id}", dependencies=[Depends(require_roles(SUPER_ADMIN))])
def update_rule(id: str, body: RuleUpdate, db: Session = Depends(get_db),
                current_user=Depends(get_current_user)):
    rule = db.query(DiscrepancyRule).filter(DiscrepancyRule.id == id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    before = {"enabled": rule.enabled, "severity": rule.severity}
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(rule, k, v)
    write_audit(db, user_id=current_user.id, entity_type="discrepancy_rule", entity_id=rule.id,
                action="UPDATE_RULE", before=before, after={"enabled": rule.enabled, "severity": rule.severity})
    db.commit()
    db.refresh(rule)
    return {"data": {"id": rule.id, "code": rule.code, "enabled": rule.enabled, "severity": rule.severity}}
