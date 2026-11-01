"""
Audit trail — append-only, SHA-256 hash-chained log.
Every mutating operation calls write_audit().
"""
import hashlib
import json
from datetime import datetime
from typing import Any, Optional
from sqlalchemy.orm import Session
from src.config.models import AuditLog


def _canonical(obj: Any) -> str:
    """Produce a deterministic JSON string for hashing."""
    return json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))


def _compute_hash(prev_hash: Optional[str], entry_data: dict) -> str:
    """SHA-256(prev_hash + canonical(entry_data))."""
    payload = (prev_hash or "") + _canonical(entry_data)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_audit(
    db: Session,
    *,
    user_id: Optional[str],
    entity_type: str,
    entity_id: Optional[str],
    action: str,
    before: Optional[Any] = None,
    after: Optional[Any] = None,
    ip: Optional[str] = None,
) -> AuditLog:
    """
    Append one entry to the audit log and maintain the hash chain.
    Must be called within an active DB transaction — caller commits.
    """
    from datetime import timedelta
    # Get last entry's hash
    last = db.query(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).first()
    prev_hash = last.hash if last else None

    now_dt = datetime.utcnow()
    if last and last.created_at and last.created_at >= now_dt:
        now_dt = last.created_at + timedelta(microseconds=1)

    entry_data = {
        "user_id": user_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action,
        "before_json": before,
        "after_json": after,
        "ip": ip,
        "created_at": now_dt.isoformat(),
    }

    h = _compute_hash(prev_hash, entry_data)

    log = AuditLog(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        before_json=before,
        after_json=after,
        ip=ip,
        prev_hash=prev_hash,
        hash=h,
        created_at=now_dt,
    )
    db.add(log)
    db.flush()
    return log


def verify_chain(db: Session) -> dict:
    """
    Recompute the hash chain from the beginning.
    Returns {"intact": True} or {"intact": False, "broken_at": entry_id, "message": ...}
    """
    entries = db.query(AuditLog).order_by(AuditLog.created_at.asc(), AuditLog.id.asc()).all()
    prev_hash = None
    for entry in entries:
        entry_data = {
            "user_id": entry.user_id,
            "entity_type": entry.entity_type,
            "entity_id": entry.entity_id,
            "action": entry.action,
            "before_json": entry.before_json,
            "after_json": entry.after_json,
            "ip": entry.ip,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        }
        expected = _compute_hash(prev_hash, entry_data)
        if expected != entry.hash:
            return {
                "intact": False,
                "broken_at": entry.id,
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
                "message": f"Hash mismatch at entry {entry.id}. Expected {expected[:16]}…, found {entry.hash[:16]}…",
            }
        prev_hash = entry.hash

    return {"intact": True, "total_entries": len(entries)}
