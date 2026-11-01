"""Review queue router — lists all OCR fields below confidence threshold that need review."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.config.models import OCRField, FDRDocument, FDR, Deposit
from src.auth.auth import get_current_user, has_role
from src.auth.auth import SUPER_ADMIN, AICTE_OFFICER, AUDITOR
from src.config.settings import get_settings

router = APIRouter()
settings = get_settings()


@router.get("")
def get_review_queue(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    threshold = settings.OCR_CONFIDENCE_THRESHOLD
    q = db.query(OCRField).filter(
        OCRField.confidence < threshold,
        OCRField.reviewed_value == None,
    )
    # Scope to institution unless admin/aicte/auditor
    if not has_role(current_user, SUPER_ADMIN, AICTE_OFFICER, AUDITOR):
        # Join through document → fdr → deposit to scope
        q = (
            q.join(FDRDocument, OCRField.document_id == FDRDocument.id)
             .join(FDR, FDRDocument.fdr_id == FDR.id)
             .join(Deposit, FDR.deposit_id == Deposit.id)
             .filter(Deposit.institution_id == current_user.institution_id)
        )

    fields = q.all()
    result = []
    for f in fields:
        doc = db.query(FDRDocument).filter(FDRDocument.id == f.document_id).first()
        fdr = db.query(FDR).filter(FDR.id == doc.fdr_id).first() if doc else None
        result.append({
            "id": f.id, "field_name": f.field_name,
            "extracted_value": f.extracted_value,
            "confidence": f.confidence, "source_text": f.source_text,
            "document_id": f.document_id,
            "fdr_id": doc.fdr_id if doc else None,
            "fdr_number": fdr.fdr_number if fdr else None,
        })
    return {"data": result}
