"""Rules management router (standalone /api/rules)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.config.models import DiscrepancyRule
from src.auth.auth import get_current_user, require_roles, SUPER_ADMIN
from src.audit.audit import write_audit

router = APIRouter()


class RuleUpdate(BaseModel):
    enabled: Optional[bool] = None
    severity: Optional[str] = None
    description: Optional[str] = None


@router.get("")
def list_rules(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rules = db.query(DiscrepancyRule).order_by(DiscrepancyRule.code).all()
    return {"data": [
        {"id": r.id, "code": r.code, "description": r.description,
         "severity": r.severity, "enabled": r.enabled, "source_ref": r.source_ref,
         "owner_role": r.owner_role}
        for r in rules
    ]}


@router.patch("/{id}", dependencies=[Depends(require_roles(SUPER_ADMIN))])
def update_rule(id: str, body: RuleUpdate, db: Session = Depends(get_db),
                current_user=Depends(get_current_user)):
    rule = db.query(DiscrepancyRule).filter(DiscrepancyRule.id == id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    before = {"enabled": rule.enabled, "severity": rule.severity}
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(rule, k, v)
    write_audit(db, user_id=current_user.id, entity_type="discrepancy_rule", entity_id=rule.id,
                action="UPDATE_RULE", before=before, after={"enabled": rule.enabled})
    db.commit()
    db.refresh(rule)
    return {"data": {"id": rule.id, "code": rule.code, "enabled": rule.enabled, "severity": rule.severity}}
