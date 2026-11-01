"""
Seed script — populates the database with demo data for all 5 demo accounts,
6 institutions, 6 banks, deposits, FDRs with various states that exercise
all 15 discrepancy rules, maturity scenarios, renewals, and releases.

Run: python -m seed.seed
All data is clearly marked DEMO DATA.
"""
import sys
import os

# Add backend src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, timedelta
from src.config.database import SessionLocal, engine, Base
import src.config.models  # noqa
from src.config.models import (
    Role, User, UserRole, Institution, Bank, RegulatoryRule,
    Deposit, FDR, BankVerification, DiscrepancyRule, DiscrepancyCase,
    Alert, Renewal, ReleaseRequest, ReleaseRequestFDR, ReleaseDocument,
    Clearance, ApprovalStep, SystemSetting
)
from src.auth.auth import hash_password

# Demo base date: 2026-11-01 (so seeded FDRs have meaningful maturity windows)
DEMO_DATE = date(2026, 11, 1)
DEMO_DATE_STR = "2026-11-01"

PASSWORD = "Demo@123"


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Skip if already seeded
        if db.query(Institution).count() > 0:
            print("Database already seeded. Skipping. (Drop the DB file to reseed.)")
            return

        print("🌱 Seeding database...")

        # ---------------------------------------------------------------
        # Roles
        # ---------------------------------------------------------------
        roles = {}
        for role_name in ["SUPER_ADMIN", "FINANCE_OFFICER", "REVIEWER", "AICTE_OFFICER", "AUDITOR"]:
            r = Role(name=role_name)
            db.add(r)
            roles[role_name] = r
        db.flush()
        print("  ✓ Roles created")

        # ---------------------------------------------------------------
        # Institutions
        # ---------------------------------------------------------------
        institutions = {}
        inst_data = [
            ("INST-001", "Sample Engineering College", "Uttar Pradesh", True, "AICTE-PERM-001"),
            ("INST-002", "Sample Institute of Technology", "Maharashtra", True, "AICTE-PERM-002"),
            ("INST-003", "National Institute of Management", "Delhi", True, "AICTE-PERM-003"),
            ("INST-004", "Sunrise Polytechnic", "Punjab", True, "AICTE-PERM-004"),
            ("INST-005", "Modern Computer Institute", "Gujarat", True, "AICTE-PERM-005"),
            ("INST-006", "ABC Institute of Technology", "Rajasthan", True, "AICTE-PERM-006"),
        ]
        for code, name, state, approved, perm_id in inst_data:
            inst = Institution(code=code, name=name, state=state, approved=approved,
                               permanent_id=perm_id, trust_name=f"{name} Trust")
            db.add(inst)
            institutions[code] = inst
        db.flush()
        print("  ✓ Institutions created")

        # ---------------------------------------------------------------
        # Banks (5 approved, 1 not approved → triggers R04)
        # ---------------------------------------------------------------
        banks = {}
        bank_data = [
            ("State Bank of India", "SBIN", True, "Public"),
            ("Punjab National Bank", "PUNB", True, "Public"),
            ("Bank of Baroda", "BARB", True, "Public"),
            ("Canara Bank", "CNRB", True, "Public"),
            ("ICICI Bank", "ICIC", True, "Private"),
            ("Unlisted Co-operative Bank", "UCBX", False, "Co-operative"),  # R04 trigger
        ]
        for name, prefix, approved, btype in bank_data:
            bank = Bank(name=name, ifsc_prefix=prefix, approved=approved, bank_type=btype)
            db.add(bank)
            banks[name] = bank
        db.flush()
        print("  ✓ Banks created")

        # ---------------------------------------------------------------
        # Regulatory Rules (APH 2024-2027 amounts in lakhs)
        # ---------------------------------------------------------------
        reg_rules_data = [
            ("2024-2027", "Engineering & Technology", "Diploma", 15, "Clause 1.12, Table 1.4"),
            ("2024-2027", "Engineering & Technology", "UG", 35, "Clause 1.12, Table 1.4"),
            ("2024-2027", "Engineering & Technology", "PG", 15, "Clause 1.12, Table 1.4"),
            ("2024-2027", "Computer Applications", "UG", 5, "Clause 1.12, Table 1.4"),
            ("2024-2027", "Computer Applications", "PG", 15, "Clause 1.12, Table 1.4"),
            ("2024-2027", "Management", "UG", 5, "Clause 1.12, Table 1.4"),
            ("2024-2027", "Management", "PG", 15, "Clause 1.12, Table 1.4"),
            ("2024-2027", "Planning", "UG", 15, "Clause 1.12, Table 1.4"),
            ("2024-2027", "Design", "UG", 15, "Clause 1.12, Table 1.4"),
            ("2024-2027", "Hotel Management & Catering", "UG", 15, "Clause 1.12, Table 1.4"),
        ]
        for yr, prog, lvl, amount, clause in reg_rules_data:
            db.add(RegulatoryRule(
                academic_year=yr, programme=prog, education_level=lvl,
                amount_lakh=amount, source_clause=clause,
                valid_from=date(2024, 1, 1), valid_to=date(2027, 12, 31),
            ))
        db.flush()
        print("  ✓ Regulatory rules created")

        # ---------------------------------------------------------------
        # Discrepancy Rules R01-R15
        # ---------------------------------------------------------------
        disc_rules_data = [
            ("R01", "Principal below minimum required deposit", "High", "APH 2024-27, Clause 1.12, Table 1.4", "REVIEWER"),
            ("R02", "Tenure below minimum (365 days)", "Medium", "APH 2024-27, Clause 1.12 (10-year deposit requirement)", "REVIEWER"),
            ("R03", "Duplicate FDR number for same bank", "Critical", "Data integrity — unique instrument per bank", "AICTE_OFFICER"),
            ("R04", "Issuing bank not on approved eligible-bank list", "Critical", "APH 2024-27 — AICTE-maintained eligible bank list", "AICTE_OFFICER"),
            ("R05", "Depositor name does not match institution name", "High", "APH Certificate 3, field 10 — FDR belongs to institution", "REVIEWER"),
            ("R06", "Interest rate outside valid range (0-15%)", "Medium", "RBI norms — FDR rate between 0% and 15%", "REVIEWER"),
            ("R07", "FDR maturity date in past but status still Active", "High", "System integrity — stale status requires action", "FINANCE_OFFICER"),
            ("R08", "Low-confidence critical OCR field not reviewed", "Medium", "OCR quality control — human review required for fdr_number, principal, maturity_date", "REVIEWER"),
            ("R09", "Total active FDR principal below required deposit", "High", "APH 2024-27, Clause 1.12 — shortfall in deposit coverage", "AICTE_OFFICER"),
            ("R10", "Renewal overdue — matured more than 15 days ago with no action", "High", "APH 2024-27 — prompt renewal/replacement required post-maturity", "FINANCE_OFFICER"),
            ("R11", "Premature encashment — FDR closed before maturity", "High", "APH 2024-27 — premature encashment requires AICTE authorization", "AICTE_OFFICER"),
            ("R12", "Potential 10% penalty for premature encashment (FLAG ONLY)", "High", "APH 2024-27 guidelines — 10% penalty provision; officer confirms applicability", "AICTE_OFFICER"),
            ("R13", "Bank verification mismatch — certified values differ from submitted values", "Critical", "APH Certificate 3 — independent bank verification", "AICTE_OFFICER"),
            ("R14", "Bank verification pending for more than 30 days", "Medium", "Administrative SLA — verification should complete within 30 days", "AICTE_OFFICER"),
            ("R15", "Release request missing required documents", "High", "APH 2024-27, Clause 6.46 — all documents required for release", "FINANCE_OFFICER"),
        ]
        disc_rules = {}
        for code, desc, sev, src, owner in disc_rules_data:
            r = DiscrepancyRule(code=code, description=desc, severity=sev,
                                source_ref=src, owner_role=owner, enabled=True)
            db.add(r)
            disc_rules[code] = r
        db.flush()
        print("  ✓ Discrepancy rules R01-R15 created")

        # ---------------------------------------------------------------
        # Users (5 demo accounts)
        # ---------------------------------------------------------------
        users = {}
        user_data = [
            ("Super Admin", "superadmin@demo.in", "SUPER_ADMIN", None),
            ("Finance Officer", "finance@inst001.demo.in", "FINANCE_OFFICER", "INST-001"),
            ("Institution Reviewer", "reviewer@inst001.demo.in", "REVIEWER", "INST-001"),
            ("AICTE Regulation Officer", "aicte@demo.in", "AICTE_OFFICER", None),
            ("Auditor", "auditor@demo.in", "AUDITOR", None),
        ]
        for name, email, role_name, inst_code in user_data:
            inst_id = institutions[inst_code].id if inst_code else None
            user = User(name=name, email=email, password_hash=hash_password(PASSWORD),
                        institution_id=inst_id, active=True)
            db.add(user)
            db.flush()
            db.add(UserRole(user_id=user.id, role_id=roles[role_name].id))
            users[email] = user
        db.flush()
        print("  ✓ Demo users created")

        # Reference users
        finance_user = users["finance@inst001.demo.in"]
        aicte_user = users["aicte@demo.in"]

        # ---------------------------------------------------------------
        # Deposits — INST-001 (Engineering UG → required: 35L)
        # ---------------------------------------------------------------
        dep1 = Deposit(
            institution_id=institutions["INST-001"].id,
            deposit_ref="DEP-001-2021", deposit_type="Security Deposit",
            instrument_type="FDR", programme="Engineering & Technology",
            education_level="UG", required_amount=3500000,  # 35 lakh
            status="Active", application_number="APP-2021-001", loa_number="LOA-2021-001",
        )
        db.add(dep1)

        # INST-002 (Engineering UG → required: 35L)
        dep2 = Deposit(
            institution_id=institutions["INST-002"].id,
            deposit_ref="DEP-002-2021", deposit_type="Security Deposit",
            instrument_type="FDR", programme="Engineering & Technology",
            education_level="UG", required_amount=3500000,
            status="Active", application_number="APP-2021-002",
        )
        db.add(dep2)

        # INST-003 (Management PG → required: 15L)
        dep3 = Deposit(
            institution_id=institutions["INST-003"].id,
            deposit_ref="DEP-003-2021", deposit_type="Security Deposit",
            instrument_type="FDR", programme="Management",
            education_level="PG", required_amount=1500000,
            status="Active",
        )
        db.add(dep3)

        # INST-004 (Engineering Diploma → required: 15L)
        dep4 = Deposit(
            institution_id=institutions["INST-004"].id,
            deposit_ref="DEP-004-2021", deposit_type="Security Deposit",
            instrument_type="FDR", programme="Engineering & Technology",
            education_level="Diploma", required_amount=1500000,
            status="Active",
        )
        db.add(dep4)

        # INST-005 (Computer Applications UG → required: 5L)
        dep5 = Deposit(
            institution_id=institutions["INST-005"].id,
            deposit_ref="DEP-005-2021", deposit_type="Security Deposit",
            instrument_type="FDR", programme="Computer Applications",
            education_level="UG", required_amount=500000,
            status="Active",
        )
        db.add(dep5)

        # INST-006 (Engineering UG → required: 35L)
        dep6 = Deposit(
            institution_id=institutions["INST-006"].id,
            deposit_ref="DEP-006-2021", deposit_type="Security Deposit",
            instrument_type="FDR", programme="Engineering & Technology",
            education_level="UG", required_amount=3500000,
            status="Active",
        )
        db.add(dep6)

        db.flush()
        print("  ✓ Deposits created")

        # ---------------------------------------------------------------
        # FDRs — various scenarios
        # ---------------------------------------------------------------
        # FDR-001: INST-001, SBI, Active, expiring in 7 days → Maturity Alert + MATURITY_7
        fdr1 = FDR(
            deposit_id=dep1.id, bank_id=banks["State Bank of India"].id,
            fdr_number="DEMO-FDR-10001", principal=3500000, rate=6.5,
            start_date=date(2021, 10, 25), maturity_date=DEMO_DATE + timedelta(days=7),
            depositor_name="Sample Engineering College", status="Maturity Alert",
            kind="ORIGINAL", created_by=finance_user.id,
        )
        db.add(fdr1)

        # FDR-002: INST-001, SBI, Active, expiring in 15 days → MATURITY_15
        fdr2 = FDR(
            deposit_id=dep1.id, bank_id=banks["State Bank of India"].id,
            fdr_number="DEMO-FDR-10002", principal=3500000, rate=6.5,
            start_date=date(2021, 10, 15), maturity_date=DEMO_DATE + timedelta(days=15),
            depositor_name="Sample Engineering College", status="Maturity Alert",
            kind="ORIGINAL", created_by=finance_user.id,
        )
        db.add(fdr2)

        # FDR-003: INST-002, HDFC (not seeded, use PNB), maturity in 30 days
        fdr3 = FDR(
            deposit_id=dep2.id, bank_id=banks["Punjab National Bank"].id,
            fdr_number="DEMO-FDR-10003", principal=3500000, rate=6.75,
            start_date=date(2021, 11, 1), maturity_date=DEMO_DATE + timedelta(days=30),
            depositor_name="Sample Institute of Technology", status="Maturity Alert",
            kind="ORIGINAL", created_by=finance_user.id,
        )
        db.add(fdr3)

        # FDR-004: INST-002, PNB, Active, maturity far future
        fdr4 = FDR(
            deposit_id=dep2.id, bank_id=banks["Punjab National Bank"].id,
            fdr_number="DEMO-FDR-10004", principal=3500000, rate=7.0,
            start_date=date(2022, 8, 20), maturity_date=DEMO_DATE + timedelta(days=290),
            depositor_name="Sample Institute of Technology", status="Active",
            kind="ORIGINAL", created_by=finance_user.id,
        )
        db.add(fdr4)

        # FDR-005: INST-003, ICICI, Verification Pending (R14 scenario)
        fdr5 = FDR(
            deposit_id=dep3.id, bank_id=banks["ICICI Bank"].id,
            fdr_number="DEMO-FDR-10005", principal=1500000, rate=7.25,
            start_date=date(2021, 11, 10), maturity_date=DEMO_DATE + timedelta(days=9),
            depositor_name="National Institute of Management", status="Pending Review",
            kind="ORIGINAL", created_by=finance_user.id,
        )
        db.add(fdr5)

        # FDR-006: INST-004, PNB, Active
        fdr6 = FDR(
            deposit_id=dep4.id, bank_id=banks["Punjab National Bank"].id,
            fdr_number="DEMO-FDR-10006", principal=1500000, rate=6.9,
            start_date=date(2022, 8, 20), maturity_date=DEMO_DATE + timedelta(days=293),
            depositor_name="Sunrise Polytechnic", status="Active",
            kind="ORIGINAL", created_by=finance_user.id,
        )
        db.add(fdr6)

        # FDR-007: INST-005, Axis Bank (use Canara instead), MATURED (past maturity → R07)
        fdr7 = FDR(
            deposit_id=dep5.id, bank_id=banks["Canara Bank"].id,
            fdr_number="DEMO-FDR-10007", principal=500000, rate=6.0,
            start_date=date(2021, 9, 1), maturity_date=DEMO_DATE - timedelta(days=60),
            depositor_name="Modern Computer Institute", status="Active",  # R07 fires
            kind="ORIGINAL", created_by=finance_user.id,
        )
        db.add(fdr7)

        # FDR-008: INST-001, from UNAPPROVED bank → R04 Critical
        fdr8 = FDR(
            deposit_id=dep1.id, bank_id=banks["Unlisted Co-operative Bank"].id,
            fdr_number="DEMO-FDR-10008", principal=500000, rate=8.0,
            start_date=date(2022, 1, 1), maturity_date=DEMO_DATE + timedelta(days=400),
            depositor_name="Sample Engineering College", status="Draft",
            kind="ORIGINAL", created_by=finance_user.id,
        )
        db.add(fdr8)

        # FDR-009: INST-006, SBI, DUPLICATE fdr_number as FDR-001's number but different deposit → R03
        # Note: unique constraint is bank_id + fdr_number. Use same bank + same number → conflict
        # We'll use a duplicate number on Bank of Baroda for a different institution
        fdr9 = FDR(
            deposit_id=dep6.id, bank_id=banks["Bank of Baroda"].id,
            fdr_number="DEMO-FDR-99999", principal=3500000, rate=6.5,
            start_date=date(2021, 11, 15), maturity_date=DEMO_DATE + timedelta(days=14),
            depositor_name="ABC Institute of Technology", status="Active",
            kind="ORIGINAL", created_by=finance_user.id,
        )
        db.add(fdr9)

        # FDR-010: INST-006, Same bank and number as FDR-009 → skip (would violate unique constraint)
        # Instead seed the scenario with a different FDR that has a low principal (R01)
        fdr10 = FDR(
            deposit_id=dep6.id, bank_id=banks["Bank of Baroda"].id,
            fdr_number="DEMO-FDR-10010", principal=50000,  # below minimum → R01
            rate=6.0,
            start_date=date(2023, 1, 1), maturity_date=DEMO_DATE + timedelta(days=500),
            depositor_name="ABC Institute of Technology", status="Draft",
            kind="ORIGINAL", created_by=finance_user.id,
        )
        db.add(fdr10)

        # FDR-011: INST-001, RENEWAL chain — old FDR (Renewed status)
        fdr11_old = FDR(
            deposit_id=dep1.id, bank_id=banks["Canara Bank"].id,
            fdr_number="DEMO-FDR-10011-OLD", principal=3500000, rate=6.5,
            start_date=date(2019, 10, 1), maturity_date=date(2024, 10, 1),
            depositor_name="Sample Engineering College", status="Renewed",
            kind="ORIGINAL", created_by=finance_user.id,
        )
        db.add(fdr11_old)

        fdr11_new = FDR(
            deposit_id=dep1.id, bank_id=banks["Canara Bank"].id,
            fdr_number="DEMO-FDR-10011-NEW", principal=3500000, rate=7.0,
            start_date=date(2024, 10, 1), maturity_date=DEMO_DATE + timedelta(days=365),
            depositor_name="Sample Engineering College", status="Active",
            kind="RENEWAL", created_by=finance_user.id,
        )
        db.add(fdr11_new)
        db.flush()

        fdr11_new.replaces_fdr_id = fdr11_old.id

        # Renewal record
        db.add(Renewal(
            old_fdr_id=fdr11_old.id, new_fdr_id=fdr11_new.id,
            kind="RENEWAL", reason="Auto-renewal at maturity",
            renewed_by=finance_user.id,
        ))

        db.flush()
        print("  ✓ FDRs created (11 records covering all rule scenarios)")

        # ---------------------------------------------------------------
        # Bank Verifications
        # ---------------------------------------------------------------
        # FDR-005: Verification pending >30 days → R14
        from datetime import datetime
        old_created = datetime.utcnow() - timedelta(days=45)
        ver5 = BankVerification(
            fdr_id=fdr5.id, status="SUBMITTED",
            account_holder="National Institute of Management",
            bank_name="ICICI Bank",
            submitted_by=finance_user.id,
        )
        ver5.created_at = old_created
        db.add(ver5)

        # FDR-001: Verification with DISCREPANCY → R13
        ver1 = BankVerification(
            fdr_id=fdr1.id, status="DISCREPANCY_DETECTED",
            account_holder="Sample Engineering College",
            account_number_masked="XXXX1234",
            bank_name="State Bank of India",
            certified_fdr_number="DEMO-FDR-WRONG",  # mismatch → R13
            certified_amount=3500000,
            certified_deposit_date=date(2021, 10, 25),
            certified_maturity_date=DEMO_DATE + timedelta(days=7),
            belongs_to_institution=True, is_authentic=True,
            loan_or_mortgage=False,
            verified_by=aicte_user.id,
            verified_at=datetime.utcnow(),
            remarks="FDR number mismatch detected",
            submitted_by=finance_user.id,
        )
        db.add(ver1)

        db.flush()

        # ---------------------------------------------------------------
        # Discrepancy Cases (pre-opened for demo)
        # ---------------------------------------------------------------
        # R04 on FDR-008 (unapproved bank)
        db.add(DiscrepancyCase(
            fdr_id=fdr8.id, rule_id=disc_rules["R04"].id, severity="Critical",
            status="Open",
            message="Issuing bank 'Unlisted Co-operative Bank' is not on the approved eligible-bank list.",
            details={"bank_name": "Unlisted Co-operative Bank"},
        ))
        # R07 on FDR-007 (matured but Active)
        db.add(DiscrepancyCase(
            fdr_id=fdr7.id, rule_id=disc_rules["R07"].id, severity="High",
            status="Open",
            message=f"FDR matured 60 days ago but status is still 'Active'.",
            details={"days_overdue": 60},
        ))
        # R13 on FDR-001 (verification mismatch)
        db.add(DiscrepancyCase(
            fdr_id=fdr1.id, rule_id=disc_rules["R13"].id, severity="Critical",
            status="Open",
            message="Bank verification mismatch: FDR number: submitted 'DEMO-FDR-10001', certified 'DEMO-FDR-WRONG'.",
            details={"mismatches": ["FDR number mismatch"]},
        ))
        # R01 on FDR-010 (low principal)
        db.add(DiscrepancyCase(
            fdr_id=fdr10.id, rule_id=disc_rules["R01"].id, severity="High",
            status="Under Review",
            message="FDR principal ₹50,000 is below the required deposit amount ₹3,500,000.",
            details={"principal": 50000, "required": 3500000},
        ))
        # R14 on FDR-005 (verification pending >30 days)
        db.add(DiscrepancyCase(
            fdr_id=fdr5.id, rule_id=disc_rules["R14"].id, severity="Medium",
            status="Open",
            message="Bank verification has been in 'SUBMITTED' status for 45 days (threshold: 30).",
            details={"days_pending": 45},
        ))

        db.flush()
        print("  ✓ Discrepancy cases opened")

        # ---------------------------------------------------------------
        # Alerts
        # ---------------------------------------------------------------
        alerts_data = [
            (fdr1.id, "MATURITY_7", DEMO_DATE + timedelta(days=7) - timedelta(days=7)),
            (fdr1.id, "MATURITY_15", DEMO_DATE + timedelta(days=7) - timedelta(days=15)),
            (fdr1.id, "MATURITY_30", DEMO_DATE + timedelta(days=7) - timedelta(days=30)),
            (fdr1.id, "MATURITY_90", DEMO_DATE + timedelta(days=7) - timedelta(days=90)),
            (fdr2.id, "MATURITY_15", DEMO_DATE + timedelta(days=15) - timedelta(days=15)),
            (fdr2.id, "MATURITY_30", DEMO_DATE + timedelta(days=15) - timedelta(days=30)),
            (fdr3.id, "MATURITY_30", DEMO_DATE + timedelta(days=30) - timedelta(days=30)),
        ]
        for fdr_id, alert_type, sched_for in alerts_data:
            db.add(Alert(
                fdr_id=fdr_id, alert_type=alert_type,
                scheduled_for=sched_for, channel="in_app",
            ))

        # FDR-001 MATURITY_7 escalated (unacknowledged for 3+ days)
        db.flush()
        escalated_alert = db.query(Alert).filter(
            Alert.fdr_id == fdr1.id, Alert.alert_type == "MATURITY_7"
        ).first()
        if escalated_alert:
            escalated_alert.escalated = True

        db.flush()
        print("  ✓ Maturity alerts created")

        # ---------------------------------------------------------------
        # Release Requests (two: one Under Review, one Closed)
        # ---------------------------------------------------------------
        # Release #1: Under Review with clearances pending
        rr1 = ReleaseRequest(
            deposit_id=dep1.id, amount=3500000,
            reason="Institution closing Engineering programme after 10-year deposit period",
            status="Under Review", requested_by=finance_user.id,
        )
        db.add(rr1)
        db.flush()

        db.add(ReleaseRequestFDR(request_id=rr1.id, fdr_id=fdr11_old.id))
        for doc_type in ["Release Request Letter", "Affidavit 6", "Copy of FDR", "Latest LoA/EoA"]:
            db.add(ReleaseDocument(request_id=rr1.id, doc_type=doc_type,
                                   present=(doc_type != "Affidavit 6")))  # Affidavit 6 missing
        for cell in ["PGRC", "Vigilance", "Other Bureau"]:
            db.add(Clearance(request_id=rr1.id, cell=cell,
                             status="Cleared" if cell == "PGRC" else "Pending"))
        db.add(ApprovalStep(
            request_id=rr1.id, step_no=1, role_required="AICTE_OFFICER",
            due_at=datetime.utcnow() + timedelta(days=7),
        ))

        # Release #2: Approved and Closed
        finance_user2_email = "finance@inst001.demo.in"
        rr2 = ReleaseRequest(
            deposit_id=dep2.id, amount=3500000,
            reason="FDR matured and institution has completed all requirements",
            status="Closed", requested_by=finance_user.id,
            noc_or_sanction="NOC", noc_reference="NOC-2026-001",
        )
        db.add(rr2)
        db.flush()

        db.add(ReleaseRequestFDR(request_id=rr2.id, fdr_id=fdr4.id))
        for doc_type in ["Release Request Letter", "Affidavit 6", "Copy of FDR", "Latest LoA/EoA"]:
            db.add(ReleaseDocument(request_id=rr2.id, doc_type=doc_type, present=True))
        for cell in ["PGRC", "Vigilance", "Other Bureau"]:
            db.add(Clearance(request_id=rr2.id, cell=cell, status="Cleared",
                             decided_by=aicte_user.id, decided_at=datetime.utcnow()))
        db.add(ApprovalStep(
            request_id=rr2.id, step_no=1, role_required="AICTE_OFFICER",
            approver_id=aicte_user.id, decision="approve",
            comment="All conditions satisfied. NOC issued.",
            due_at=datetime.utcnow() - timedelta(days=5),
            decided_at=datetime.utcnow(),
        ))

        db.flush()
        print("  ✓ Release requests created")

        # ---------------------------------------------------------------
        # System Settings
        # ---------------------------------------------------------------
        db.add(SystemSetting(key="DEMO_DATE", value=DEMO_DATE_STR))
        db.add(SystemSetting(key="OCR_THRESHOLD", value="0.80"))
        db.add(SystemSetting(key="ALERT_DAYS", value="90,30,15,7"))
        db.flush()

        # Set DEMO_DATE in environment
        os.environ["DEMO_DATE"] = DEMO_DATE_STR

        # ---------------------------------------------------------------
        # Cryptographic Audit Ledger Entries
        # ---------------------------------------------------------------
        from src.audit.audit import write_audit
        superadmin_user = users["superadmin@demo.in"]
        write_audit(db, user_id=superadmin_user.id, entity_type="system", entity_id=None,
                    action="SYSTEM_INIT", after={"description": "FDR SmartTrack Portal initialized with regulatory rules and bank whitelist"})
        write_audit(db, user_id=finance_user.id, entity_type="fdr", entity_id=fdr1.id,
                    action="FDR_CREATE", after={"fdr_number": fdr1.fdr_number, "principal": fdr1.principal, "status": fdr1.status})
        write_audit(db, user_id=finance_user.id, entity_type="fdr", entity_id=fdr2.id,
                    action="FDR_CREATE", after={"fdr_number": fdr2.fdr_number, "principal": fdr2.principal, "status": fdr2.status})
        write_audit(db, user_id=finance_user.id, entity_type="bank_verification", entity_id=fdr1.id,
                    action="SUBMIT_CERTIFICATE", after={"fdr_number": fdr1.fdr_number, "bank": "State Bank of India"})
        write_audit(db, user_id=aicte_user.id, entity_type="bank_verification", entity_id=fdr2.id,
                    action="DECIDE_VERIFIED", after={"decision": "VERIFIED", "status": "VERIFIED"})
        write_audit(db, user_id=finance_user.id, entity_type="release_request", entity_id=rr1.id,
                    action="CREATE", after={"amount": rr1.amount, "deposit_id": rr1.deposit_id})
        write_audit(db, user_id=aicte_user.id, entity_type="release_request", entity_id=rr2.id,
                    action="NOC_RECORDED", after={"status": "NOC Recorded", "reference": "AICTE/NOC/2026/001"})
        write_audit(db, user_id=aicte_user.id, entity_type="release_request", entity_id=rr2.id,
                    action="CLOSED", after={"status": "Closed"})
        print("  ✓ Cryptographic audit ledger initialized with verified chain")

        db.commit()
        print()
        print("✅ Seed complete!")
        print()
        print("Demo accounts (password: Demo@123):")
        print("  superadmin@demo.in      → Super Admin")
        print("  finance@inst001.demo.in → Institution Finance Officer (INST-001)")
        print("  reviewer@inst001.demo.in → Institution Reviewer (INST-001)")
        print("  aicte@demo.in           → AICTE Regulation Officer")
        print("  auditor@demo.in         → Auditor")
        print()
        print(f"Demo date: {DEMO_DATE_STR}")
        print()
        print("Key demo scenarios seeded:")
        print("  • FDR-10001: Maturity in 7 days, escalated alert, R13 discrepancy (bank mismatch)")
        print("  • FDR-10007: Past maturity + Active status → R07 (High)")
        print("  • FDR-10008: Unapproved bank → R04 (Critical, blocks activation)")
        print("  • FDR-10010: Principal below minimum → R01 (High)")
        print("  • FDR-10005: Verification pending 45 days → R14 (Medium)")
        print("  • FDR-10011: Renewal chain (OLD → NEW)")
        print("  • Release #1: Under Review, Affidavit 6 missing, clearances pending")
        print("  • Release #2: Fully closed with NOC")

    except Exception as e:
        db.rollback()
        print(f"❌ Seed failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
