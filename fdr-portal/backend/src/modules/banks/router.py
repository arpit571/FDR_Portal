"""Banks router."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.config.models import Bank
from src.auth.auth import get_current_user, require_roles, SUPER_ADMIN
from src.audit.audit import write_audit

router = APIRouter()


class BankCreate(BaseModel):
    name: str
    ifsc_prefix: Optional[str] = None
    approved: bool = True
    bank_type: Optional[str] = None


class BankUpdate(BaseModel):
    name: Optional[str] = None
    ifsc_prefix: Optional[str] = None
    approved: Optional[bool] = None
    bank_type: Optional[str] = None


def bank_dict(b: Bank):
    return {"id": b.id, "name": b.name, "ifsc_prefix": b.ifsc_prefix,
            "approved": b.approved, "bank_type": b.bank_type}


@router.get("")
def list_banks(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    banks = db.query(Bank).all()
    return {"data": [bank_dict(b) for b in banks]}


@router.post("", dependencies=[Depends(require_roles(SUPER_ADMIN))])
def create_bank(body: BankCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if db.query(Bank).filter(Bank.name == body.name).first():
        raise HTTPException(status_code=409, detail="Bank name already exists")
    bank = Bank(**body.model_dump())
    db.add(bank)
    write_audit(db, user_id=current_user.id, entity_type="bank", entity_id=bank.id,
                action="CREATE", after=bank_dict(bank))
    db.commit()
    db.refresh(bank)
    return {"data": bank_dict(bank)}


@router.patch("/{id}", dependencies=[Depends(require_roles(SUPER_ADMIN))])
def update_bank(id: str, body: BankUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    bank = db.query(Bank).filter(Bank.id == id).first()
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
    before = bank_dict(bank)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(bank, k, v)
    write_audit(db, user_id=current_user.id, entity_type="bank", entity_id=bank.id,
                action="UPDATE", before=before, after=bank_dict(bank))
    db.commit()
    db.refresh(bank)
    return {"data": bank_dict(bank)}
