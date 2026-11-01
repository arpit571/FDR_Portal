"""OCR fields router (stub — actual fields retrieved via /documents/:id/ocr)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.config.models import OCRField, FDRDocument, FDR
from src.auth.auth import get_current_user, require_roles, require_institution_scope
from src.auth.auth import SUPER_ADMIN, FINANCE_OFFICER, REVIEWER
from src.audit.audit import write_audit

router = APIRouter()


class ReviewBody(BaseModel):
    reviewed_value: str


@router.post("/{field_id}/review")
def review_field(
    field_id: str, body: ReviewBody,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not any(r in [ur.role.name for ur in current_user.roles]
               for r in [SUPER_ADMIN, FINANCE_OFFICER, REVIEWER]):
        raise HTTPException(status_code=403, detail="Not authorized")

    field = db.query(OCRField).filter(OCRField.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="OCR field not found")

    doc = db.query(FDRDocument).filter(FDRDocument.id == field.document_id).first()
    fdr = db.query(FDR).filter(FDR.id == doc.fdr_id).first() if doc else None
    if fdr:
        require_institution_scope(current_user, fdr.deposit.institution_id)

    before = {"reviewed_value": field.reviewed_value}
    field.reviewed_value = body.reviewed_value
    field.reviewed_by = current_user.id
    field.reviewed_at = datetime.utcnow()

    write_audit(db, user_id=current_user.id, entity_type="ocr_field", entity_id=field.id,
                action="REVIEW", before=before, after={"reviewed_value": body.reviewed_value})
    db.commit()
    return {"data": {"id": field.id, "reviewed_value": field.reviewed_value}}
