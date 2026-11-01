"""
Discrepancy Rule Engine — R01 through R15.
Each rule is a pure function: check(fdr, context) -> None | dict(message, details).
Rules are registered in RULE_REGISTRY keyed by rule code.
"""
from datetime import date
from typing import Optional, Dict, Any, Callable, List
from fuzzywuzzy import fuzz
from src.config.dates import today as get_today


# ---------------------------------------------------------------------------
# Rule context — everything a rule might need
# ---------------------------------------------------------------------------

class RuleContext:
    def __init__(
        self,
        db=None,
        institution_name: str = "",
        deposit_required_amount: float = 0,
        all_fdrs: list = None,
        ocr_fields: list = None,
        verification=None,
        release_request=None,
        ocr_threshold: float = 0.80,
        min_tenure_days: int = 365,
        demo_today: Optional[date] = None,
    ):
        self.db = db
        self.institution_name = institution_name
        self.deposit_required_amount = deposit_required_amount
        self.all_fdrs = all_fdrs or []
        self.ocr_fields = ocr_fields or []
        self.verification = verification
        self.release_request = release_request
        self.ocr_threshold = ocr_threshold
        self.min_tenure_days = min_tenure_days
        self.today = demo_today or get_today()


# ---------------------------------------------------------------------------
# R01 — Principal below minimum
# ---------------------------------------------------------------------------

def check_r01(fdr, ctx: RuleContext):
    """Principal below required deposit amount."""
    required = ctx.deposit_required_amount
    if required > 0 and fdr.principal < required:
        return {
            "message": f"FDR principal ₹{fdr.principal:,.0f} is below the required deposit amount ₹{required:,.0f}.",
            "details": {"principal": fdr.principal, "required": required},
        }
    return None


# ---------------------------------------------------------------------------
# R02 — Tenure below minimum
# ---------------------------------------------------------------------------

def check_r02(fdr, ctx: RuleContext):
    """Tenure below minimum tenure days (default 365)."""
    if fdr.start_date and fdr.maturity_date:
        tenure = (fdr.maturity_date - fdr.start_date).days
        if tenure < ctx.min_tenure_days:
            return {
                "message": f"FDR tenure {tenure} days is below minimum {ctx.min_tenure_days} days.",
                "details": {"tenure_days": tenure, "min_tenure_days": ctx.min_tenure_days},
            }
    return None


# ---------------------------------------------------------------------------
# R03 — Duplicate FDR number (same bank_id + fdr_number)
# ---------------------------------------------------------------------------

def check_r03(fdr, ctx: RuleContext):
    """Duplicate FDR number for the same bank across different FDRs."""
    if not ctx.db:
        return None
    from src.config.models import FDR
    duplicates = (
        ctx.db.query(FDR)
        .filter(FDR.bank_id == fdr.bank_id, FDR.fdr_number == fdr.fdr_number, FDR.id != fdr.id)
        .all()
    )
    if duplicates:
        return {
            "message": f"FDR number {fdr.fdr_number} already exists for this bank in another record (ID: {duplicates[0].id}).",
            "details": {"duplicate_fdr_id": duplicates[0].id},
        }
    return None


# ---------------------------------------------------------------------------
# R04 — Bank not approved
# ---------------------------------------------------------------------------

def check_r04(fdr, ctx: RuleContext):
    """Issuing bank is not on the approved bank list."""
    if fdr.bank and not fdr.bank.approved:
        return {
            "message": f"Bank '{fdr.bank.name}' is not on the approved eligible-bank list.",
            "details": {"bank_id": fdr.bank_id, "bank_name": fdr.bank.name if fdr.bank else "Unknown"},
        }
    return None


# ---------------------------------------------------------------------------
# R05 — Depositor name mismatch
# ---------------------------------------------------------------------------

def check_r05(fdr, ctx: RuleContext):
    """Depositor name does not fuzzy-match institution name (threshold 85)."""
    if not fdr.depositor_name or not ctx.institution_name:
        return None
    score = fuzz.token_set_ratio(
        fdr.depositor_name.lower().strip(),
        ctx.institution_name.lower().strip()
    )
    if score < 85:
        return {
            "message": f"Depositor name '{fdr.depositor_name}' does not match institution name '{ctx.institution_name}' (similarity: {score}%).",
            "details": {"depositor_name": fdr.depositor_name, "institution_name": ctx.institution_name, "similarity": score},
        }
    return None


# ---------------------------------------------------------------------------
# R06 — Rate out of range
# ---------------------------------------------------------------------------

def check_r06(fdr, ctx: RuleContext):
    """Interest rate is outside 0–15% range."""
    if fdr.rate is not None and (fdr.rate < 0 or fdr.rate > 15):
        return {
            "message": f"Interest rate {fdr.rate}% is outside the valid range (0–15%).",
            "details": {"rate": fdr.rate},
        }
    return None


# ---------------------------------------------------------------------------
# R07 — Maturity in past, status Active
# ---------------------------------------------------------------------------

def check_r07(fdr, ctx: RuleContext):
    """FDR maturity date is in the past but status is still Active."""
    if fdr.maturity_date and fdr.status in ("Active", "Maturity Alert"):
        if fdr.maturity_date < ctx.today:
            days_overdue = (ctx.today - fdr.maturity_date).days
            return {
                "message": f"FDR matured {days_overdue} days ago on {fdr.maturity_date} but status is still '{fdr.status}'.",
                "details": {"maturity_date": str(fdr.maturity_date), "days_overdue": days_overdue},
            }
    return None


# ---------------------------------------------------------------------------
# R08 — Low-confidence critical field not reviewed
# ---------------------------------------------------------------------------

def check_r08(fdr, ctx: RuleContext):
    """Critical OCR fields (fdr_number, principal, maturity_date) have low confidence and are unreviewed."""
    critical_fields = {"fdr_number", "principal", "maturity_date"}
    low_conf_unreviewed = []
    for field in ctx.ocr_fields:
        if (
            field.field_name in critical_fields
            and field.confidence is not None
            and field.confidence < ctx.ocr_threshold
            and field.reviewed_value is None
        ):
            low_conf_unreviewed.append({
                "field": field.field_name,
                "confidence": field.confidence,
                "value": field.extracted_value,
            })
    if low_conf_unreviewed:
        return {
            "message": f"Critical OCR fields have low confidence and have not been reviewed: {[f['field'] for f in low_conf_unreviewed]}.",
            "details": {"fields": low_conf_unreviewed},
        }
    return None


# ---------------------------------------------------------------------------
# R09 — Shortfall vs required deposit
# ---------------------------------------------------------------------------

def check_r09(fdr, ctx: RuleContext):
    """Sum of active FDR principals is less than the required deposit amount."""
    active_principal = sum(
        f.principal for f in ctx.all_fdrs
        if f.status in ("Active", "Maturity Alert") and f.deposit_id == fdr.deposit_id
    )
    required = ctx.deposit_required_amount
    if required > 0 and active_principal < required:
        shortfall = required - active_principal
        return {
            "message": f"Total active FDR principal ₹{active_principal:,.0f} is below required deposit ₹{required:,.0f}. Shortfall: ₹{shortfall:,.0f}.",
            "details": {"active_principal": active_principal, "required": required, "shortfall": shortfall},
        }
    return None


# ---------------------------------------------------------------------------
# R10 — Renewal overdue (>15 days past maturity with no action)
# ---------------------------------------------------------------------------

def check_r10(fdr, ctx: RuleContext):
    """FDR has been in 'Matured - Action Pending' for more than 15 days."""
    if fdr.status == "Matured - Action Pending" and fdr.maturity_date:
        days_overdue = (ctx.today - fdr.maturity_date).days
        if days_overdue > 15:
            return {
                "message": f"FDR has been past maturity for {days_overdue} days without renewal or release action.",
                "details": {"maturity_date": str(fdr.maturity_date), "days_overdue": days_overdue},
            }
    return None


# ---------------------------------------------------------------------------
# R11 — Premature encashment
# ---------------------------------------------------------------------------

def check_r11(fdr, ctx: RuleContext):
    """FDR closed or withdrawn before maturity date."""
    if fdr.status in ("Closed", "Released") and fdr.maturity_date:
        if fdr.maturity_date > ctx.today:
            return {
                "message": f"FDR was closed/released on {ctx.today} before its maturity date {fdr.maturity_date} — potential premature encashment.",
                "details": {"maturity_date": str(fdr.maturity_date), "status": fdr.status},
            }
    return None


# ---------------------------------------------------------------------------
# R12 — Penalty applicability flag
# ---------------------------------------------------------------------------

def check_r12(fdr, ctx: RuleContext):
    """Flag for potential 10% penalty (premature encashment or missing required deposit).
    This is a FLAG ONLY — final applicability confirmed by authorized officer."""
    # Fires when R11 fires (premature) or when R09's shortfall is critical
    if fdr.status in ("Closed", "Released") and fdr.maturity_date and fdr.maturity_date > ctx.today:
        penalty_amount = fdr.principal * 0.10
        return {
            "message": f"Potential 10% penalty of ₹{penalty_amount:,.0f} may apply for premature encashment. AICTE officer must confirm applicability.",
            "details": {"principal": fdr.principal, "estimated_penalty": penalty_amount, "flag_only": True},
        }
    return None


# ---------------------------------------------------------------------------
# R13 — Bank verification mismatch
# ---------------------------------------------------------------------------

def check_r13(fdr, ctx: RuleContext):
    """Any bank-certified value differs from institution-submitted value."""
    v = ctx.verification
    if not v or v.status not in ("VERIFIED", "DISCREPANCY_DETECTED"):
        return None

    mismatches = []
    if v.certified_fdr_number and v.certified_fdr_number != fdr.fdr_number:
        mismatches.append(f"FDR number: submitted '{fdr.fdr_number}', certified '{v.certified_fdr_number}'")
    if v.certified_amount and abs(v.certified_amount - fdr.principal) > 1:
        mismatches.append(f"Amount: submitted {fdr.principal:,.0f}, certified {v.certified_amount:,.0f}")
    if v.certified_maturity_date and fdr.maturity_date and v.certified_maturity_date != fdr.maturity_date:
        mismatches.append(f"Maturity date: submitted {fdr.maturity_date}, certified {v.certified_maturity_date}")
    if v.belongs_to_institution is False:
        mismatches.append("Bank certifies FDR does NOT belong to this institution")
    if v.is_authentic is False:
        mismatches.append("Bank certifies FDR is NOT authentic")

    if mismatches:
        return {
            "message": f"Bank verification mismatch: {'; '.join(mismatches)}.",
            "details": {"mismatches": mismatches},
        }
    return None


# ---------------------------------------------------------------------------
# R14 — Verification pending too long (>30 days)
# ---------------------------------------------------------------------------

def check_r14(fdr, ctx: RuleContext):
    """Bank verification has been in SUBMITTED or PENDING status for more than 30 days."""
    v = ctx.verification
    if not v or v.status not in ("SUBMITTED", "PENDING"):
        return None
    if v.created_at:
        days_pending = (ctx.today - v.created_at.date()).days
        if days_pending > 30:
            return {
                "message": f"Bank verification has been in '{v.status}' status for {days_pending} days (threshold: 30).",
                "details": {"verification_status": v.status, "days_pending": days_pending},
            }
    return None


# ---------------------------------------------------------------------------
# R15 — Missing release document
# ---------------------------------------------------------------------------

def check_r15(fdr, ctx: RuleContext):
    """Release request is missing required documents."""
    rr = ctx.release_request
    if not rr:
        return None

    required_docs = [
        "Release Request Letter",
        "Affidavit 6",
        "Copy of FDR",
        "Latest LoA/EoA",
    ]
    missing = []
    present_types = {rd.doc_type for rd in rr.documents if rd.present}
    for doc in required_docs:
        if doc not in present_types:
            missing.append(doc)

    if missing:
        return {
            "message": f"Release request is missing required documents: {', '.join(missing)}.",
            "details": {"missing_documents": missing},
        }
    return None


# ---------------------------------------------------------------------------
# Rule Registry
# ---------------------------------------------------------------------------

RULE_REGISTRY: Dict[str, Callable] = {
    "R01": check_r01,
    "R02": check_r02,
    "R03": check_r03,
    "R04": check_r04,
    "R05": check_r05,
    "R06": check_r06,
    "R07": check_r07,
    "R08": check_r08,
    "R09": check_r09,
    "R10": check_r10,
    "R11": check_r11,
    "R12": check_r12,
    "R13": check_r13,
    "R14": check_r14,
    "R15": check_r15,
}


# ---------------------------------------------------------------------------
# Rule runner
# ---------------------------------------------------------------------------

def run_rules_for_fdr(fdr, ctx: RuleContext, db) -> List[dict]:
    """
    Run all enabled rules for one FDR.
    Creates DiscrepancyCase rows for any failures.
    Returns list of new case dicts.
    """
    from src.config.models import DiscrepancyRule, DiscrepancyCase
    from src.audit.audit import write_audit

    rules = db.query(DiscrepancyRule).filter(DiscrepancyRule.enabled == True).all()
    new_cases = []

    for rule in rules:
        fn = RULE_REGISTRY.get(rule.code)
        if not fn:
            continue
        result = fn(fdr, ctx)
        if result:
            # Check if open case already exists
            existing = (
                db.query(DiscrepancyCase)
                .filter(
                    DiscrepancyCase.fdr_id == fdr.id,
                    DiscrepancyCase.rule_id == rule.id,
                    DiscrepancyCase.status.in_(["Open", "Under Review"]),
                )
                .first()
            )
            if existing:
                continue  # don't create duplicate

            case = DiscrepancyCase(
                fdr_id=fdr.id,
                rule_id=rule.id,
                severity=rule.severity,
                status="Open",
                message=result["message"],
                details=result.get("details"),
            )
            db.add(case)
            new_cases.append({
                "rule_code": rule.code,
                "severity": rule.severity,
                "message": result["message"],
            })

    return new_cases


def has_blocking_discrepancies(fdr_id: str, db) -> bool:
    """Return True if any Critical-severity open discrepancy case exists for this FDR."""
    from src.config.models import DiscrepancyCase
    return db.query(DiscrepancyCase).filter(
        DiscrepancyCase.fdr_id == fdr_id,
        DiscrepancyCase.severity == "Critical",
        DiscrepancyCase.status.in_(["Open", "Under Review"]),
    ).count() > 0
