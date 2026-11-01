"""Institutions router."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.config.models import Institution
from src.auth.auth import get_current_user, require_roles, SUPER_ADMIN, AICTE_OFFICER, AUDITOR, FINANCE_OFFICER, REVIEWER
from src.audit.audit import write_audit

router = APIRouter()


class InstitutionCreate(BaseModel):
    code: str
    name: str
    state: Optional[str] = None
    permanent_id: Optional[str] = None
    trust_name: Optional[str] = None
    approved: bool = True


class InstitutionUpdate(BaseModel):
    name: Optional[str] = None
    state: Optional[str] = None
    permanent_id: Optional[str] = None
    trust_name: Optional[str] = None
    approved: Optional[bool] = None


def inst_dict(i: Institution):
    return {
        "id": i.id, "code": i.code, "name": i.name, "state": i.state,
        "approved": i.approved, "permanent_id": i.permanent_id,
        "trust_name": i.trust_name, "created_at": str(i.created_at),
    }


@router.get("")
def list_institutions(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from src.auth.auth import has_role
    if has_role(current_user, SUPER_ADMIN, AICTE_OFFICER, AUDITOR):
        insts = db.query(Institution).all()
    else:
        # Finance/Reviewer see only their own institution
        insts = db.query(Institution).filter(Institution.id == current_user.institution_id).all()
    return {"data": [inst_dict(i) for i in insts]}


@router.post("", dependencies=[Depends(require_roles(SUPER_ADMIN))])
def create_institution(body: InstitutionCreate, db: Session = Depends(get_db),
                       current_user=Depends(get_current_user)):
    if db.query(Institution).filter(Institution.code == body.code).first():
        raise HTTPException(status_code=409, detail="Institution code already exists")
    inst = Institution(**body.model_dump())
    db.add(inst)
    write_audit(db, user_id=current_user.id, entity_type="institution", entity_id=inst.id,
                action="CREATE", after={"code": inst.code, "name": inst.name})
    db.commit()
    db.refresh(inst)
    return {"data": inst_dict(inst)}


@router.get("/:id")
def get_institution(id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    inst = db.query(Institution).filter(Institution.id == id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")
    return {"data": inst_dict(inst)}


@router.patch("/{id}", dependencies=[Depends(require_roles(SUPER_ADMIN))])
def update_institution(id: str, body: InstitutionUpdate, db: Session = Depends(get_db),
                       current_user=Depends(get_current_user)):
    inst = db.query(Institution).filter(Institution.id == id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")
    before = inst_dict(inst)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(inst, k, v)
    write_audit(db, user_id=current_user.id, entity_type="institution", entity_id=inst.id,
                action="UPDATE", before=before, after=inst_dict(inst))
    db.commit()
    db.refresh(inst)
    return {"data": inst_dict(inst)}
