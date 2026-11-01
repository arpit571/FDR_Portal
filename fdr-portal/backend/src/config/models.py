"""
Complete SQLAlchemy models — all tables in one file for clarity.
Every table has id (UUID string), created_at, updated_at.
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date,
    Text, ForeignKey, UniqueConstraint, Index, JSON
)
from sqlalchemy.orm import relationship
from src.config.database import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


def now_utc():
    return datetime.utcnow()


# ---------------------------------------------------------------------------
# Roles & Users
# ---------------------------------------------------------------------------

class Role(Base):
    __tablename__ = "roles"
    id = Column(String, primary_key=True, default=new_uuid)
    name = Column(String(50), unique=True, nullable=False)
    # SUPER_ADMIN | FINANCE_OFFICER | REVIEWER | AICTE_OFFICER | AUDITOR
    users = relationship("UserRole", back_populates="role")


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=new_uuid)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=True)
    name = Column(String(200), nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)

    institution = relationship("Institution", back_populates="users")
    roles = relationship("UserRole", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    role_id = Column(String, ForeignKey("roles.id"), primary_key=True)
    user = relationship("User", back_populates="roles")
    role = relationship("Role", back_populates="users")


# ---------------------------------------------------------------------------
# Institutions & Banks
# ---------------------------------------------------------------------------

class Institution(Base):
    __tablename__ = "institutions"
    id = Column(String, primary_key=True, default=new_uuid)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(500), nullable=False)
    state = Column(String(100), nullable=True)
    approved = Column(Boolean, default=True, nullable=False)
    permanent_id = Column(String(50), nullable=True)  # AICTE Permanent ID
    trust_name = Column(String(300), nullable=True)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)

    users = relationship("User", back_populates="institution")
    deposits = relationship("Deposit", back_populates="institution")


class Bank(Base):
    __tablename__ = "banks"
    id = Column(String, primary_key=True, default=new_uuid)
    name = Column(String(200), unique=True, nullable=False)
    ifsc_prefix = Column(String(10), nullable=True)
    approved = Column(Boolean, default=True, nullable=False)
    bank_type = Column(String(50), nullable=True)  # Public | Private | Co-operative
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)

    fdrs = relationship("FDR", back_populates="bank")


# ---------------------------------------------------------------------------
# Regulatory Rules (APH amounts by year/programme/level)
# ---------------------------------------------------------------------------

class RegulatoryRule(Base):
    __tablename__ = "regulatory_rules"
    id = Column(String, primary_key=True, default=new_uuid)
    academic_year = Column(String(20), nullable=False)  # e.g. "2024-2027"
    programme = Column(String(100), nullable=False)
    education_level = Column(String(50), nullable=False)  # Diploma | UG | PG
    amount_lakh = Column(Float, nullable=False)           # in lakhs
    is_private_leased = Column(Boolean, default=False)    # doubled for private lease
    exemptions = Column(Text, nullable=True)
    valid_from = Column(Date, nullable=True)
    valid_to = Column(Date, nullable=True)
    source_clause = Column(String(100), nullable=True)    # e.g. "Clause 1.12, Table 1.4"
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)


# ---------------------------------------------------------------------------
# Deposits (parent record — backed by FDRs)
# ---------------------------------------------------------------------------

class Deposit(Base):
    __tablename__ = "deposits"
    id = Column(String, primary_key=True, default=new_uuid)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False)
    deposit_ref = Column(String(100), nullable=False)
    deposit_type = Column(String(50), default="Security Deposit")
    instrument_type = Column(String(50), default="FDR")  # FDR | RTGS | Security Deposit
    programme = Column(String(100), nullable=True)
    education_level = Column(String(50), nullable=True)
    required_amount = Column(Float, nullable=False)       # in rupees
    required_amount_override_reason = Column(Text, nullable=True)
    status = Column(String(50), default="Active")         # Active | Partially Released | Closed
    application_number = Column(String(100), nullable=True)
    loa_number = Column(String(100), nullable=True)
    affidavit3_uploaded = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)

    institution = relationship("Institution", back_populates="deposits")
    fdrs = relationship("FDR", back_populates="deposit")
    release_requests = relationship("ReleaseRequest", back_populates="deposit")


# ---------------------------------------------------------------------------
# FDRs
# ---------------------------------------------------------------------------

class FDR(Base):
    __tablename__ = "fdrs"
    id = Column(String, primary_key=True, default=new_uuid)
    deposit_id = Column(String, ForeignKey("deposits.id"), nullable=False)
    bank_id = Column(String, ForeignKey("banks.id"), nullable=False)
    fdr_number = Column(String(100), nullable=False)
    principal = Column(Float, nullable=False)             # in rupees
    rate = Column(Float, nullable=True)                   # interest rate %
    start_date = Column(Date, nullable=False)
    maturity_date = Column(Date, nullable=False)
    depositor_name = Column(String(300), nullable=True)
    status = Column(String(50), default="Draft")
    # Draft | Pending Document | Extracting | Pending Review | Active |
    # Maturity Alert | Matured - Action Pending | Renewed | Replaced | Released | Closed
    document_id = Column(String, ForeignKey("fdr_documents.id"), nullable=True)
    kind = Column(String(50), default="ORIGINAL")         # ORIGINAL | RENEWAL | REPLACEMENT
    replaces_fdr_id = Column(String, ForeignKey("fdrs.id"), nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)

    __table_args__ = (
        UniqueConstraint("bank_id", "fdr_number", name="uq_bank_fdr_number"),
        Index("ix_fdrs_maturity_status", "maturity_date", "status"),
    )

    deposit = relationship("Deposit", back_populates="fdrs")
    bank = relationship("Bank", back_populates="fdrs")
    document = relationship("FDRDocument", foreign_keys=[document_id], back_populates="fdr_primary")
    documents = relationship("FDRDocument", foreign_keys="FDRDocument.fdr_id", back_populates="fdr")
    discrepancy_cases = relationship("DiscrepancyCase", back_populates="fdr")
    alerts = relationship("Alert", back_populates="fdr")
    verification = relationship("BankVerification", back_populates="fdr", uselist=False)
    renewals_as_old = relationship("Renewal", foreign_keys="Renewal.old_fdr_id", back_populates="old_fdr")
    renewals_as_new = relationship("Renewal", foreign_keys="Renewal.new_fdr_id", back_populates="new_fdr")
    creator = relationship("User", foreign_keys=[created_by])


# ---------------------------------------------------------------------------
# Documents & OCR
# ---------------------------------------------------------------------------

class FDRDocument(Base):
    __tablename__ = "fdr_documents"
    id = Column(String, primary_key=True, default=new_uuid)
    fdr_id = Column(String, ForeignKey("fdrs.id"), nullable=False)
    file_path = Column(String(500), nullable=False)
    original_name = Column(String(300), nullable=False)
    mime = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    sha256 = Column(String(64), unique=True, nullable=False)
    ocr_status = Column(String(50), default="pending")  # pending | extracting | done | failed | mock
    uploaded_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)

    fdr = relationship("FDR", foreign_keys=[fdr_id], back_populates="documents")
    fdr_primary = relationship("FDR", foreign_keys="FDR.document_id", back_populates="document")
    ocr_fields = relationship("OCRField", back_populates="document")
    uploader = relationship("User", foreign_keys=[uploaded_by])


class OCRField(Base):
    __tablename__ = "ocr_fields"
    id = Column(String, primary_key=True, default=new_uuid)
    document_id = Column(String, ForeignKey("fdr_documents.id"), nullable=False)
    field_name = Column(String(100), nullable=False)
    extracted_value = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)             # 0.0 – 1.0
    source_text = Column(Text, nullable=True)             # raw OCR line
    reviewed_value = Column(Text, nullable=True)
    reviewed_by = Column(String, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now_utc)

    document = relationship("FDRDocument", back_populates="ocr_fields")
    reviewer = relationship("User", foreign_keys=[reviewed_by])


# ---------------------------------------------------------------------------
# Bank Verification (Certificate 3 fields)
# ---------------------------------------------------------------------------

class BankVerification(Base):
    __tablename__ = "bank_verifications"
    id = Column(String, primary_key=True, default=new_uuid)
    fdr_id = Column(String, ForeignKey("fdrs.id"), unique=True, nullable=False)
    status = Column(String(50), default="SUBMITTED")
    # SUBMITTED | CERTIFICATE_UPLOADED | PENDING | VERIFIED | DISCREPANCY_DETECTED | REJECTED
    account_holder = Column(String(300), nullable=True)
    account_number_masked = Column(String(20), nullable=True)  # show last 4 digits only
    bank_name = Column(String(200), nullable=True)
    bank_address = Column(Text, nullable=True)
    account_authentic = Column(Boolean, nullable=True)
    balance_confirmed = Column(Boolean, nullable=True)
    certified_fdr_number = Column(String(100), nullable=True)
    certified_deposit_date = Column(Date, nullable=True)
    certified_maturity_date = Column(Date, nullable=True)
    certified_amount = Column(Float, nullable=True)
    belongs_to_institution = Column(Boolean, nullable=True)
    is_authentic = Column(Boolean, nullable=True)
    loan_or_mortgage = Column(Boolean, nullable=True)
    certificate_document_id = Column(String, nullable=True)   # FK to fdr_documents
    verified_by = Column(String, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    remarks = Column(Text, nullable=True)
    submitted_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)

    fdr = relationship("FDR", back_populates="verification")
    verifier = relationship("User", foreign_keys=[verified_by])
    submitter = relationship("User", foreign_keys=[submitted_by])


# ---------------------------------------------------------------------------
# Discrepancy Rules & Cases
# ---------------------------------------------------------------------------

class DiscrepancyRule(Base):
    __tablename__ = "discrepancy_rules"
    id = Column(String, primary_key=True, default=new_uuid)
    code = Column(String(10), unique=True, nullable=False)   # R01 .. R15
    description = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False)            # Critical | High | Medium | Low
    enabled = Column(Boolean, default=True)
    source_ref = Column(Text, nullable=True)                 # APH clause or policy ref
    owner_role = Column(String(50), nullable=True)           # who typically resolves it
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)

    cases = relationship("DiscrepancyCase", back_populates="rule")


class DiscrepancyCase(Base):
    __tablename__ = "discrepancy_cases"
    id = Column(String, primary_key=True, default=new_uuid)
    fdr_id = Column(String, ForeignKey("fdrs.id"), nullable=False)
    rule_id = Column(String, ForeignKey("discrepancy_rules.id"), nullable=False)
    severity = Column(String(20), nullable=False)
    status = Column(String(50), default="Open")             # Open | Under Review | Resolved | Waived
    message = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    opened_at = Column(DateTime, default=now_utc)
    resolved_by = Column(String, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_note = Column(Text, nullable=True)
    waived_by = Column(String, ForeignKey("users.id"), nullable=True)
    waived_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)

    __table_args__ = (
        Index("ix_disc_status_severity", "status", "severity"),
    )

    fdr = relationship("FDR", back_populates="discrepancy_cases")
    rule = relationship("DiscrepancyRule", back_populates="cases")
    resolver = relationship("User", foreign_keys=[resolved_by])
    waiver = relationship("User", foreign_keys=[waived_by])


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(String, primary_key=True, default=new_uuid)
    fdr_id = Column(String, ForeignKey("fdrs.id"), nullable=False)
    alert_type = Column(String(50), nullable=False)  # MATURITY_90 | MATURITY_30 | etc.
    scheduled_for = Column(Date, nullable=False)
    channel = Column(String(50), default="in_app")   # in_app | email
    sent_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String, ForeignKey("users.id"), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    escalated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now_utc)

    __table_args__ = (
        Index("ix_alerts_scheduled", "scheduled_for"),
        UniqueConstraint("fdr_id", "alert_type", name="uq_fdr_alert_type"),
    )

    fdr = relationship("FDR", back_populates="alerts")
    acknowledger = relationship("User", foreign_keys=[acknowledged_by])


# ---------------------------------------------------------------------------
# Renewals
# ---------------------------------------------------------------------------

class Renewal(Base):
    __tablename__ = "renewals"
    id = Column(String, primary_key=True, default=new_uuid)
    old_fdr_id = Column(String, ForeignKey("fdrs.id"), nullable=False)
    new_fdr_id = Column(String, ForeignKey("fdrs.id"), nullable=False)
    kind = Column(String(50), nullable=False)               # RENEWAL | REPLACEMENT
    reason = Column(Text, nullable=True)
    renewed_on = Column(DateTime, default=now_utc)
    renewed_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=now_utc)

    old_fdr = relationship("FDR", foreign_keys=[old_fdr_id], back_populates="renewals_as_old")
    new_fdr = relationship("FDR", foreign_keys=[new_fdr_id], back_populates="renewals_as_new")
    renewer = relationship("User", foreign_keys=[renewed_by])


# ---------------------------------------------------------------------------
# Release Requests (Maker-Checker with Clearances)
# ---------------------------------------------------------------------------

class ReleaseRequest(Base):
    __tablename__ = "release_requests"
    id = Column(String, primary_key=True, default=new_uuid)
    deposit_id = Column(String, ForeignKey("deposits.id"), nullable=False)
    amount = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(50), default="Submitted")
    # Submitted | Under Review | Cell Clearances | Approved | Rejected |
    # NOC Recorded | Refund Initiated | Closed
    noc_or_sanction = Column(String(50), nullable=True)     # NOC | Sanction Order
    noc_reference = Column(String(200), nullable=True)
    requested_by = Column(String, ForeignKey("users.id"), nullable=False)
    rejection_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)

    deposit = relationship("Deposit", back_populates="release_requests")
    requester = relationship("User", foreign_keys=[requested_by])
    fdrs = relationship("ReleaseRequestFDR", back_populates="release_request")
    documents = relationship("ReleaseDocument", back_populates="release_request")
    clearances = relationship("Clearance", back_populates="release_request")
    approval_steps = relationship("ApprovalStep", back_populates="release_request",
                                  order_by="ApprovalStep.step_no")


class ReleaseRequestFDR(Base):
    __tablename__ = "release_request_fdrs"
    request_id = Column(String, ForeignKey("release_requests.id"), primary_key=True)
    fdr_id = Column(String, ForeignKey("fdrs.id"), primary_key=True)

    release_request = relationship("ReleaseRequest", back_populates="fdrs")
    fdr = relationship("FDR")


class ReleaseDocument(Base):
    __tablename__ = "release_documents"
    id = Column(String, primary_key=True, default=new_uuid)
    request_id = Column(String, ForeignKey("release_requests.id"), nullable=False)
    doc_type = Column(String(100), nullable=False)
    # Release Request Letter | Affidavit 6 | Copy of FDR | DD/Payment Proof | LoA/EoA
    document_id = Column(String, nullable=True)              # FK to fdr_documents if uploaded
    present = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_utc)

    release_request = relationship("ReleaseRequest", back_populates="documents")


class Clearance(Base):
    __tablename__ = "clearances"
    id = Column(String, primary_key=True, default=new_uuid)
    request_id = Column(String, ForeignKey("release_requests.id"), nullable=False)
    cell = Column(String(100), nullable=False)  # PGRC | Vigilance | Other Bureau
    status = Column(String(50), default="Pending")           # Pending | Cleared | Rejected
    remarks = Column(Text, nullable=True)
    decided_by = Column(String, ForeignKey("users.id"), nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)

    release_request = relationship("ReleaseRequest", back_populates="clearances")
    decider = relationship("User", foreign_keys=[decided_by])


class ApprovalStep(Base):
    __tablename__ = "approval_steps"
    id = Column(String, primary_key=True, default=new_uuid)
    request_id = Column(String, ForeignKey("release_requests.id"), nullable=False)
    step_no = Column(Integer, nullable=False)
    role_required = Column(String(50), nullable=False)
    approver_id = Column(String, ForeignKey("users.id"), nullable=True)
    decision = Column(String(50), nullable=True)             # approve | reject
    comment = Column(Text, nullable=True)
    due_at = Column(DateTime, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)

    release_request = relationship("ReleaseRequest", back_populates="approval_steps")
    approver = relationship("User", foreign_keys=[approver_id])


# ---------------------------------------------------------------------------
# Audit Log (append-only, hash-chained)
# ---------------------------------------------------------------------------

class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(String, primary_key=True, default=new_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(String, nullable=True)
    action = Column(String(200), nullable=False)
    before_json = Column(JSON, nullable=True)
    after_json = Column(JSON, nullable=True)
    ip = Column(String(50), nullable=True)
    prev_hash = Column(String(64), nullable=True)
    hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=now_utc)

    __table_args__ = (
        Index("ix_audit_entity", "entity_type", "entity_id"),
    )

    user = relationship("User", back_populates="audit_logs")


# ---------------------------------------------------------------------------
# System Settings (key-value)
# ---------------------------------------------------------------------------

class SystemSetting(Base):
    __tablename__ = "system_settings"
    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)
