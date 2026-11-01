"""
OCR Worker — mock mode only (OCR_MODE=mock).
In mock mode, reads sidecar JSON from seed/documents/<basename>.json.
Each field in the sidecar JSON: { field_name: { value, confidence } }
"""
import os
import json
import threading
from datetime import datetime
from src.config.settings import get_settings

settings = get_settings()

SIDECAR_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "seed", "documents")


def _do_ocr(doc_id: str):
    """Run in a background thread so uploads return immediately."""
    # We need a new DB session in this thread
    from src.config.database import SessionLocal
    from src.config.models import FDRDocument, OCRField, FDR
    from src.modules.rules.engine import run_rules_for_fdr, RuleContext
    from src.config.dates import today as get_today

    db = SessionLocal()
    try:
        doc = db.query(FDRDocument).filter(FDRDocument.id == doc_id).first()
        if not doc:
            return

        doc.ocr_status = "extracting"
        db.commit()

        if settings.OCR_MODE == "mock":
            # Look for sidecar JSON with same base name as original file
            base = os.path.splitext(doc.original_name)[0]
            sidecar_path = os.path.join(SIDECAR_DIR, f"{base}.json")
            if not os.path.exists(sidecar_path):
                # Try generic fallback
                sidecar_path = os.path.join(SIDECAR_DIR, "default_ocr.json")

            if os.path.exists(sidecar_path):
                with open(sidecar_path, "r") as f:
                    data = json.load(f)
                for field_name, field_data in data.items():
                    ocr_field = OCRField(
                        document_id=doc.id,
                        field_name=field_name,
                        extracted_value=str(field_data.get("value", "")),
                        confidence=float(field_data.get("confidence", 0.95)),
                        source_text=field_data.get("source_text", ""),
                    )
                    db.add(ocr_field)
                doc.ocr_status = "mock"
            else:
                doc.ocr_status = "failed"

        else:
            # Tesseract mode (not implemented in MVP — falls back to failed)
            doc.ocr_status = "failed"

        # Update FDR status
        fdr = db.query(FDR).filter(FDR.id == doc.fdr_id).first()
        if fdr:
            from src.config.settings import get_settings as gs
            cfg = gs()
            threshold = cfg.OCR_CONFIDENCE_THRESHOLD

            # Check if any field below threshold
            db.commit()
            db.refresh(doc)
            needs_review = any(
                f.confidence is not None and f.confidence < threshold and f.reviewed_value is None
                for f in doc.ocr_fields
            )
            if needs_review:
                fdr.status = "Pending Review"
            elif fdr.status == "Extracting":
                fdr.status = "Pending Review"  # Goes to review anyway for human confirmation

        db.commit()

    except Exception as e:
        print(f"OCR worker error for doc {doc_id}: {e}")
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        db.close()


def process_ocr_async(doc_id: str):
    """Start OCR in a background thread — never blocks HTTP."""
    t = threading.Thread(target=_do_ocr, args=(doc_id,), daemon=True)
    t.start()
