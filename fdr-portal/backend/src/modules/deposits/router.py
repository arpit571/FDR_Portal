"""Deposits router with CSV import."""
import csv
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.config.models import Deposit, Institution, FDR, Bank
from src.auth.auth import get_current_user, require_roles, has_role, require_institution_scope
from src.auth.auth import SUPER_ADMIN, FINANCE_OFFICER, AICTE_OFFICER, AUDITOR, REVIEWER
from src.audit.audit import write_audit
from src.config.dates import today as get_today
from datetime import date

router = APIRouter()


class DepositCreate(BaseModel):
    institution_id: str
    deposit_ref: str
    deposit_type: str = "Security Deposit"
    instrument_type: str = "FDR"
    programme: Optional[str] = None
    education_level: Optional[str] = None
    required_amount: float
    required_amount_override_reason: Optional[str] = None
    application_number: Optional[str] = None
    loa_number: Optional[str] = None


class DepositUpdate(BaseModel):
    deposit_type: Optional[str] = None
    programme: Optional[str] = None
    education_level: Optional[str] = None
    required_amount: Optional[float] = None
    required_amount_override_reason: Optional[str] = None
    status: Optional[str] = None
    application_number: Optional[str] = None
    loa_number: Optional[str] = None


def deposit_dict(d: Deposit, db: Session = None):
    total_principal = sum(
        f.principal for f in d.fdrs
        if f.status in ("Active", "Maturity Alert")
    ) if d.fdrs else 0
    shortfall = max(0, d.required_amount - total_principal)
    return {
        "id": d.id, "institution_id": d.institution_id,
        "deposit_ref": d.deposit_ref, "deposit_type": d.deposit_type,
        "instrument_type": d.instrument_type,
        "programme": d.programme, "education_level": d.education_level,
        "required_amount": d.required_amount, "status": d.status,
        "application_number": d.application_number, "loa_number": d.loa_number,
        "total_fdr_principal": total_principal, "shortfall": shortfall,
        "fdr_count": len(d.fdrs) if d.fdrs else 0,
        "created_at": str(d.created_at),
    }


@router.get("")
def list_deposits(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    q = db.query(Deposit)
    if not has_role(current_user, SUPER_ADMIN, AICTE_OFFICER, AUDITOR):
        q = q.filter(Deposit.institution_id == current_user.institution_id)
    deposits = q.all()
    return {"data": [deposit_dict(d) for d in deposits]}


@router.post("", dependencies=[Depends(require_roles(SUPER_ADMIN, FINANCE_OFFICER))])
def create_deposit(body: DepositCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    require_institution_scope(current_user, body.institution_id)
    inst = db.query(Institution).filter(Institution.id == body.institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")
    dep = Deposit(**body.model_dump())
    db.add(dep)
    write_audit(db, user_id=current_user.id, entity_type="deposit", entity_id=dep.id,
                action="CREATE", after={"deposit_ref": dep.deposit_ref, "required_amount": dep.required_amount})
    db.commit()
    db.refresh(dep)
    return {"data": deposit_dict(dep)}


@router.get("/{id}")
def get_deposit(id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    dep = db.query(Deposit).filter(Deposit.id == id).first()
    if not dep:
        raise HTTPException(status_code=404, detail="Deposit not found")
    require_institution_scope(current_user, dep.institution_id)
    return {"data": deposit_dict(dep)}


@router.patch("/{id}", dependencies=[Depends(require_roles(SUPER_ADMIN, FINANCE_OFFICER))])
def update_deposit(id: str, body: DepositUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    dep = db.query(Deposit).filter(Deposit.id == id).first()
    if not dep:
        raise HTTPException(status_code=404, detail="Deposit not found")
    require_institution_scope(current_user, dep.institution_id)
    before = deposit_dict(dep)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(dep, k, v)
    write_audit(db, user_id=current_user.id, entity_type="deposit", entity_id=dep.id,
                action="UPDATE", before=before, after=deposit_dict(dep))
    db.commit()
    db.refresh(dep)
    return {"data": deposit_dict(dep)}


@router.post("/import")
async def import_deposits_csv(
    file: UploadFile = File(...),
    institution_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Bulk CSV import. Columns: institution_code,deposit_ref,fdr_number,bank_name,principal,rate,start_date,maturity_date"""
    if not has_role(current_user, SUPER_ADMIN, FINANCE_OFFICER):
        raise HTTPException(status_code=403, detail="Not authorized")

    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    results = []

    for i, row in enumerate(reader, 1):
        try:
            # Find institution
            inst = db.query(Institution).filter(Institution.code == row.get("institution_code", "")).first()
            if not inst:
                results.append({"row": i, "status": "rejected", "reason": f"Institution code '{row.get('institution_code')}' not found"})
                continue

            require_institution_scope(current_user, inst.id)

            # Find or create deposit
            dep = db.query(Deposit).filter(
                Deposit.institution_id == inst.id,
                Deposit.deposit_ref == row.get("deposit_ref", "")
            ).first()
            if not dep:
                dep = Deposit(
                    institution_id=inst.id,
                    deposit_ref=row.get("deposit_ref", f"IMPORT-{i}"),
                    required_amount=0,
                    status="Active",
                )
                db.add(dep)
                db.flush()

            # Find bank
            bank = db.query(Bank).filter(Bank.name.ilike(f"%{row.get('bank_name', '')}%")).first()
            if not bank:
                results.append({"row": i, "status": "rejected", "reason": f"Bank '{row.get('bank_name')}' not found"})
                continue

            # Check duplicate FDR
            existing_fdr = db.query(FDR).filter(
                FDR.bank_id == bank.id, FDR.fdr_number == row.get("fdr_number", "")
            ).first()
            if existing_fdr:
                results.append({"row": i, "status": "rejected", "reason": f"FDR number '{row.get('fdr_number')}' already exists for this bank"})
                continue

            start_date = date.fromisoformat(row["start_date"])
            maturity_date = date.fromisoformat(row["maturity_date"])
            principal = float(row["principal"])
            rate = float(row.get("rate", 0))

            if principal <= 0:
                results.append({"row": i, "status": "rejected", "reason": "Principal must be > 0"})
                continue
            if maturity_date <= start_date:
                results.append({"row": i, "status": "rejected", "reason": "Maturity date must be after start date"})
                continue

            fdr = FDR(
                deposit_id=dep.id, bank_id=bank.id,
                fdr_number=row["fdr_number"], principal=principal,
                rate=rate, start_date=start_date, maturity_date=maturity_date,
                status="Draft", kind="ORIGINAL", created_by=current_user.id,
            )
            db.add(fdr)
            results.append({"row": i, "status": "imported", "fdr_number": fdr.fdr_number})

        except Exception as e:
            results.append({"row": i, "status": "rejected", "reason": str(e)})

    db.commit()
    write_audit(db, user_id=current_user.id, entity_type="import", entity_id=None,
                action="CSV_IMPORT", after={"total": len(results)})
    db.commit()
    return {"data": results}
