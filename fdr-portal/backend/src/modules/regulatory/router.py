"""Regulatory Rules router (APH amounts by academic year/programme/level)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.config.models import RegulatoryRule
from src.auth.auth import get_current_user, require_roles, SUPER_ADMIN
from src.audit.audit import write_audit

router = APIRouter()


class RuleCreate(BaseModel):
    academic_year: str
    programme: str
    education_level: str
    amount_lakh: float
    is_private_leased: bool = False
    exemptions: Optional[str] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    source_clause: Optional[str] = None


class RuleUpdate(BaseModel):
    amount_lakh: Optional[float] = None
    exemptions: Optional[str] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    source_clause: Optional[str] = None


def rule_dict(r: RegulatoryRule):
    return {
        "id": r.id, "academic_year": r.academic_year, "programme": r.programme,
        "education_level": r.education_level, "amount_lakh": r.amount_lakh,
        "amount_rupees": r.amount_lakh * 100000,
        "is_private_leased": r.is_private_leased, "exemptions": r.exemptions,
        "valid_from": str(r.valid_from) if r.valid_from else None,
        "valid_to": str(r.valid_to) if r.valid_to else None,
        "source_clause": r.source_clause,
    }


@router.get("")
def list_rules(year: Optional[str] = None, db: Session = Depends(get_db),
               current_user=Depends(get_current_user)):
    q = db.query(RegulatoryRule)
    if year:
        q = q.filter(RegulatoryRule.academic_year == year)
    return {"data": [rule_dict(r) for r in q.all()]}


@router.post("", dependencies=[Depends(require_roles(SUPER_ADMIN))])
def create_rule(body: RuleCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rule = RegulatoryRule(**body.model_dump())
    db.add(rule)
    write_audit(db, user_id=current_user.id, entity_type="regulatory_rule", entity_id=rule.id,
                action="CREATE", after=rule_dict(rule))
    db.commit()
    db.refresh(rule)
    return {"data": rule_dict(rule)}


@router.patch("/{id}", dependencies=[Depends(require_roles(SUPER_ADMIN))])
def update_rule(id: str, body: RuleUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rule = db.query(RegulatoryRule).filter(RegulatoryRule.id == id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Regulatory rule not found")
    before = rule_dict(rule)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(rule, k, v)
    write_audit(db, user_id=current_user.id, entity_type="regulatory_rule", entity_id=rule.id,
                action="UPDATE", before=before, after=rule_dict(rule))
    db.commit()
    db.refresh(rule)
    return {"data": rule_dict(rule)}
