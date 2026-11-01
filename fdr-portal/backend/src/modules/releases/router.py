"""
Release requests router — maker-checker with cell clearances, NOC, and refund flow.
Critical rule: release is NEVER triggered by maturity alone.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.config.models import (
    ReleaseRequest, ReleaseRequestFDR, ReleaseDocument, Clearance,
    ApprovalStep, Deposit, FDR, User
)
from src.auth.auth import (
    get_current_user, has_role, require_institution_scope,
    SUPER_ADMIN, FINANCE_OFFICER, REVIEWER, AICTE_OFFICER, AUDITOR
)
from src.audit.audit import write_audit
from src.config.dates import now as get_now

router = APIRouter()

REQUIRED_DOCS = [
    "Release Request Letter",
    "Affidavit 6",
    "Copy of FDR",
    "Latest LoA/EoA",
]
CLEARANCE_CELLS = ["PGRC", "Vigilance", "Other Bureau"]


class ReleaseCreate(BaseModel):
    deposit_id: str
    amount: float
    reason: str
    fdr_ids: List[str] = []
    noc_or_sanction: Optional[str] = None  # NOC | Sanction Order


class DocPresenceUpdate(BaseModel):
    doc_type: str
    present: bool
    notes: Optional[str] = None


class ClearanceBody(BaseModel):
    status: str  # Pending | Cleared | Rejected
    remarks: Optional[str] = None


class StepDecision(BaseModel):
    decision: str  # approve | reject
    comment: Optional[str] = None


class NocBody(BaseModel):
    noc_or_sanction: str  # NOC | Sanction Order
    reference: str


def rr_dict(rr: ReleaseRequest):
    return {
        "id": rr.id, "deposit_id": rr.deposit_id, "amount": rr.amount,
        "reason": rr.reason, "status": rr.status,
        "noc_or_sanction": rr.noc_or_sanction, "noc_reference": rr.noc_reference,
        "requested_by": rr.requested_by, "rejection_comment": rr.rejection_comment,
        "created_at": str(rr.created_at),
        "fdr_ids": [rf.fdr_id for rf in rr.fdrs],
        "documents": [
            {"doc_type": d.doc_type, "present": d.present, "notes": d.notes}
            for d in rr.documents
        ],
        "clearances": [
            {"cell": c.cell, "status": c.status, "remarks": c.remarks,
             "decided_at": str(c.decided_at) if c.decided_at else None}
            for c in rr.clearances
        ],
        "approval_steps": [
            {"step_no": s.step_no, "role_required": s.role_required,
             "decision": s.decision, "comment": s.comment,
             "decided_at": str(s.decided_at) if s.decided_at else None,
             "due_at": str(s.due_at) if s.due_at else None}
            for s in rr.approval_steps
        ],
    }


@router.get("")
def list_releases(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    q = db.query(ReleaseRequest)
    if not has_role(current_user, SUPER_ADMIN, AICTE_OFFICER, AUDITOR):
        q = (q.join(Deposit, ReleaseRequest.deposit_id == Deposit.id)
               .filter(Deposit.institution_id == current_user.institution_id))
    return {"data": [rr_dict(rr) for rr in q.order_by(ReleaseRequest.created_at.desc()).all()]}


@router.post("")
def create_release(body: ReleaseCreate, db: Session = Depends(get_db),
                   current_user=Depends(get_current_user)):
    if not has_role(current_user, SUPER_ADMIN, FINANCE_OFFICER):
        raise HTTPException(status_code=403, detail="Only Finance Officer can submit release requests")

    dep = db.query(Deposit).filter(Deposit.id == body.deposit_id).first()
    if not dep:
        raise HTTPException(status_code=404, detail="Deposit not found")
    require_institution_scope(current_user, dep.institution_id)

    # Validate amount
    active_principal = sum(
        f.principal for f in dep.fdrs if f.status in ("Active", "Maturity Alert")
    )
    if body.amount > active_principal:
        raise HTTPException(
            status_code=422,
            detail=f"Release amount ₹{body.amount:,.0f} exceeds active principal ₹{active_principal:,.0f}"
        )
    if not body.reason:
        raise HTTPException(status_code=422, detail="Reason is required")

    rr = ReleaseRequest(
        deposit_id=body.deposit_id, amount=body.amount, reason=body.reason,
        status="Submitted", requested_by=current_user.id,
        noc_or_sanction=body.noc_or_sanction,
    )
    db.add(rr)
    db.flush()

    # Link FDRs
    for fdr_id in body.fdr_ids:
        db.add(ReleaseRequestFDR(request_id=rr.id, fdr_id=fdr_id))

    # Create document checklist
    for doc_type in REQUIRED_DOCS:
        db.add(ReleaseDocument(request_id=rr.id, doc_type=doc_type, present=False))

    # Create clearances
    for cell in CLEARANCE_CELLS:
        db.add(Clearance(request_id=rr.id, cell=cell, status="Pending"))

    # Create approval steps
    now = get_now()
    db.add(ApprovalStep(
        request_id=rr.id, step_no=1, role_required=AICTE_OFFICER,
        due_at=now + timedelta(days=7),
    ))

    write_audit(db, user_id=current_user.id, entity_type="release_request", entity_id=rr.id,
                action="CREATE", after={"amount": rr.amount, "deposit_id": rr.deposit_id})
    db.commit()
    db.refresh(rr)
    return {"data": rr_dict(rr)}


@router.get("/{id}")
def get_release(id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rr = db.query(ReleaseRequest).filter(ReleaseRequest.id == id).first()
    if not rr:
        raise HTTPException(status_code=404, detail="Release request not found")
    dep = db.query(Deposit).filter(Deposit.id == rr.deposit_id).first()
    if dep:
        require_institution_scope(current_user, dep.institution_id)
    return {"data": rr_dict(rr)}


@router.post("/{id}/documents")
def update_document(id: str, body: DocPresenceUpdate, db: Session = Depends(get_db),
                    current_user=Depends(get_current_user)):
    if not has_role(current_user, SUPER_ADMIN, FINANCE_OFFICER, REVIEWER):
        raise HTTPException(status_code=403, detail="Not authorized")
    rr = db.query(ReleaseRequest).filter(ReleaseRequest.id == id).first()
    if not rr:
        raise HTTPException(status_code=404, detail="Release request not found")
    dep = db.query(Deposit).filter(Deposit.id == rr.deposit_id).first()
    if dep:
        require_institution_scope(current_user, dep.institution_id)

    doc = db.query(ReleaseDocument).filter(
        ReleaseDocument.request_id == id, ReleaseDocument.doc_type == body.doc_type
    ).first()
    if not doc:
        doc = ReleaseDocument(request_id=id, doc_type=body.doc_type)
        db.add(doc)

    doc.present = body.present
    doc.notes = body.notes
    write_audit(db, user_id=current_user.id, entity_type="release_document", entity_id=id,
                action="UPDATE_DOC", after={"doc_type": body.doc_type, "present": body.present})
    db.commit()
    return {"data": rr_dict(rr)}


@router.post("/{id}/clearances/{cell}")
def update_clearance(id: str, cell: str, body: ClearanceBody,
                     db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if not has_role(current_user, SUPER_ADMIN, AICTE_OFFICER):
        raise HTTPException(status_code=403, detail="Only AICTE Officer can update clearances")
    c = db.query(Clearance).filter(
        Clearance.request_id == id, Clearance.cell == cell
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="Clearance not found")
    if body.status not in ("Pending", "Cleared", "Rejected"):
        raise HTTPException(status_code=422, detail="Status must be Pending, Cleared, or Rejected")
    before = {"status": c.status}
    c.status = body.status
    c.remarks = body.remarks
    c.decided_by = current_user.id
    c.decided_at = datetime.utcnow()
    write_audit(db, user_id=current_user.id, entity_type="clearance", entity_id=c.id,
                action=f"CLEARANCE_{body.status}", before=before, after={"status": body.status})
    db.commit()
    return {"data": rr_dict(db.query(ReleaseRequest).filter(ReleaseRequest.id == id).first())}


@router.post("/{id}/steps/{step_no}/decide")
def decide_step(id: str, step_no: int, body: StepDecision,
                db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rr = db.query(ReleaseRequest).filter(ReleaseRequest.id == id).first()
    if not rr:
        raise HTTPException(status_code=404, detail="Release request not found")

    step = db.query(ApprovalStep).filter(
        ApprovalStep.request_id == id, ApprovalStep.step_no == step_no
    ).first()
    if not step:
        raise HTTPException(status_code=404, detail="Approval step not found")

    # Role check
    if not has_role(current_user, step.role_required, SUPER_ADMIN):
        raise HTTPException(status_code=403, detail=f"This step requires role: {step.role_required}")

    # CRITICAL: Maker cannot approve own request
    if rr.requested_by == current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Maker-checker violation: you cannot approve a release request you submitted."
        )

    if body.decision not in ("approve", "reject"):
        raise HTTPException(status_code=422, detail="Decision must be 'approve' or 'reject'")

    before = {"status": rr.status, "step_decision": step.decision}
    step.decision = body.decision
    step.comment = body.comment
    step.approver_id = current_user.id
    step.decided_at = datetime.utcnow()

    if body.decision == "approve":
        rr.status = "Approved"
    else:
        rr.status = "Rejected"
        rr.rejection_comment = body.comment

    write_audit(db, user_id=current_user.id, entity_type="release_request", entity_id=rr.id,
                action=f"STEP_{step_no}_{body.decision.upper()}",
                before=before, after={"status": rr.status})
    db.commit()
    db.refresh(rr)
    return {"data": rr_dict(rr)}


@router.post("/{id}/noc")
def record_noc(id: str, body: NocBody, db: Session = Depends(get_db),
               current_user=Depends(get_current_user)):
    if not has_role(current_user, SUPER_ADMIN, AICTE_OFFICER):
        raise HTTPException(status_code=403, detail="Not authorized")
    rr = db.query(ReleaseRequest).filter(ReleaseRequest.id == id).first()
    if not rr or rr.status != "Approved":
        raise HTTPException(status_code=409, detail="Release must be Approved before recording NOC/sanction")
    rr.noc_or_sanction = body.noc_or_sanction
    rr.noc_reference = body.reference
    rr.status = "NOC Recorded"
    write_audit(db, user_id=current_user.id, entity_type="release_request", entity_id=rr.id,
                action="NOC_RECORDED", after={"noc": body.noc_or_sanction, "ref": body.reference})
    db.commit()
    db.refresh(rr)
    return {"data": rr_dict(rr)}


@router.post("/{id}/close")
def close_release(id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if not has_role(current_user, SUPER_ADMIN, AICTE_OFFICER):
        raise HTTPException(status_code=403, detail="Not authorized")
    rr = db.query(ReleaseRequest).filter(ReleaseRequest.id == id).first()
    if not rr:
        raise HTTPException(status_code=404, detail="Not found")
    if rr.status not in ("NOC Recorded", "Approved"):
        raise HTTPException(status_code=409, detail="Release must have NOC recorded before closing")
    rr.status = "Closed"
    write_audit(db, user_id=current_user.id, entity_type="release_request", entity_id=rr.id,
                action="CLOSED")
    db.commit()
    db.refresh(rr)
    return {"data": rr_dict(rr)}
