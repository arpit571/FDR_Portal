"""Audit log router — query, verify chain, and tamper simulation (Auditor/Super Admin only)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.config.models import AuditLog
from src.auth.auth import get_current_user, has_role, require_roles
from src.auth.auth import SUPER_ADMIN, AUDITOR
from src.audit.audit import verify_chain

router = APIRouter()


@router.get("")
def query_audit_log(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(AuditLog)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.filter(AuditLog.entity_id == entity_id)
    logs = q.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return {"data": [
        {
            "id": l.id, "user_id": l.user_id, "entity_type": l.entity_type,
            "entity_id": l.entity_id, "action": l.action,
            "before_json": l.before_json, "after_json": l.after_json,
            "ip": l.ip, "hash": l.hash[:16] + "...",  # show partial hash
            "created_at": str(l.created_at),
        }
        for l in logs
    ]}


@router.get("/verify")
def verify_audit_chain(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Recompute the full audit hash chain. Anyone can call this."""
    result = verify_chain(db)
    return {"data": result}


@router.post("/tamper-simulate", dependencies=[Depends(require_roles(SUPER_ADMIN, AUDITOR))])
def simulate_tamper(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """
    Demo only: Edit the 2nd audit log entry's action field (breaking the hash chain).
    Then the client can call /verify to see the chain broken.
    Returns the entry ID that was tampered and the original value for restore.
    """
    entries = db.query(AuditLog).order_by(AuditLog.created_at.asc()).offset(1).limit(1).all()
    if not entries:
        raise HTTPException(status_code=404, detail="Not enough audit entries to simulate tampering")
    entry = entries[0]
    original_action = entry.action
    # Directly corrupt the action field (bypasses audit writer)
    db.execute(
        AuditLog.__table__.update()
        .where(AuditLog.id == entry.id)
        .values(action=original_action + "__TAMPERED__")
    )
    db.commit()
    return {"data": {
        "tampered_entry_id": entry.id,
        "original_action": original_action,
        "message": "Entry tampered. Call GET /api/audit/verify to see broken chain."
    }}


@router.post("/tamper-restore", dependencies=[Depends(require_roles(SUPER_ADMIN, AUDITOR))])
def restore_tamper(entry_id: str, original_action: str,
                   db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Restore tampered entry."""
    db.execute(
        AuditLog.__table__.update()
        .where(AuditLog.id == entry_id)
        .values(action=original_action.replace("__TAMPERED__", ""))
    )
    db.commit()
    return {"data": {"message": "Entry restored. Call GET /api/audit/verify to confirm chain intact."}}
