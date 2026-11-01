"""Documents router — upload with SHA-256 hashing and authorized download."""
import hashlib
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.config.models import FDRDocument, FDR, Deposit
from src.auth.auth import get_current_user, has_role, require_institution_scope
from src.auth.auth import SUPER_ADMIN, FINANCE_OFFICER, AICTE_OFFICER, AUDITOR, REVIEWER
from src.audit.audit import write_audit
from src.config.settings import get_settings
from src.jobs.ocr_worker import process_ocr_async

router = APIRouter()
settings = get_settings()

ALLOWED_MIME = {"application/pdf", "image/jpeg", "image/png", "image/jpg"}
MAX_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/fdrs/{fdr_id}/document")
async def upload_document(
    fdr_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not has_role(current_user, SUPER_ADMIN, FINANCE_OFFICER, REVIEWER):
        raise HTTPException(status_code=403, detail="Not authorized")

    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR not found")
    require_institution_scope(current_user, fdr.deposit.institution_id)

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=422, detail="File exceeds 10 MB limit")

    mime = file.content_type or ""
    if mime not in ALLOWED_MIME and not file.filename.lower().endswith((".pdf", ".jpg", ".jpeg", ".png")):
        raise HTTPException(status_code=422, detail=f"Unsupported file type: {mime}")

    # SHA-256 hash
    sha256 = hashlib.sha256(content).hexdigest()
    existing = db.query(FDRDocument).filter(FDRDocument.sha256 == sha256).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"This file has already been uploaded (duplicate SHA-256). Document ID: {existing.id}"
        )

    # Save with UUID filename to prevent guessing
    ext = os.path.splitext(file.filename)[1] if file.filename else ".bin"
    safe_name = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(settings.STORAGE_PATH, safe_name)
    os.makedirs(settings.STORAGE_PATH, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)

    doc = FDRDocument(
        fdr_id=fdr_id,
        file_path=file_path,
        original_name=file.filename or "upload",
        mime=mime,
        size_bytes=len(content),
        sha256=sha256,
        ocr_status="pending",
        uploaded_by=current_user.id,
    )
    db.add(doc)
    db.flush()

    # Set as primary document on FDR
    fdr.document_id = doc.id
    if fdr.status == "Draft":
        fdr.status = "Extracting"

    write_audit(db, user_id=current_user.id, entity_type="document", entity_id=doc.id,
                action="UPLOAD", after={"fdr_id": fdr_id, "original_name": doc.original_name,
                                        "sha256": sha256[:16] + "..."})
    db.commit()
    db.refresh(doc)

    # Trigger OCR asynchronously (non-blocking)
    process_ocr_async(doc.id)

    return {"data": {
        "id": doc.id, "fdr_id": fdr_id, "original_name": doc.original_name,
        "sha256": sha256, "ocr_status": doc.ocr_status, "size_bytes": doc.size_bytes,
    }}


@router.get("/{id}/file")
def download_document(id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    doc = db.query(FDRDocument).filter(FDRDocument.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    fdr = db.query(FDR).filter(FDR.id == doc.fdr_id).first()
    if fdr:
        require_institution_scope(current_user, fdr.deposit.institution_id)
    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(doc.file_path, media_type=doc.mime, filename=doc.original_name)


@router.get("/{id}/ocr")
def get_ocr_fields(id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    doc = db.query(FDRDocument).filter(FDRDocument.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    fields = [
        {
            "id": f.id, "field_name": f.field_name,
            "extracted_value": f.extracted_value, "confidence": f.confidence,
            "source_text": f.source_text,
            "reviewed_value": f.reviewed_value,
            "reviewed_by": f.reviewed_by,
            "reviewed_at": str(f.reviewed_at) if f.reviewed_at else None,
        }
        for f in doc.ocr_fields
    ]
    return {"data": {"doc_id": id, "ocr_status": doc.ocr_status, "fields": fields}}
