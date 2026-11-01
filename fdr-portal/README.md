# 🏛 FDR SmartTrack Portal — SIH 26265 MVP
**AICTE Regulation Bureau — Security Deposit & Fixed Deposit Receipt (FDR) Management System**

FDR SmartTrack Portal is a production-grade web system for AICTE-recognized technical institutions to record, verify, track, renew, and release regulatory security deposits and the Fixed Deposit Receipts (FDRs) backing them.

---

## 🚀 One-Click Launch

Double-click `start_mvp.bat` in the project root or run:
```cmd
start_mvp.bat
```
This automatically launches:
1. **Backend**: FastAPI on `http://127.0.0.1:8000` (Interactive Swagger docs at `http://127.0.0.1:8000/api/docs`)
2. **Frontend**: React + Vite UI on `http://localhost:5173`
3. Opens your default web browser to `http://localhost:5173`.

---

## 👥 Demo Accounts (Password: `Demo@123`)

All demo accounts come pre-configured with realistic scenarios and sample data:

| Role | Email | Password | Primary Capabilities |
|---|---|---|---|
| **Super Admin** | `superadmin@demo.in` | `Demo@123` | Full governance, bank whitelist, demo clock, discrepancy rules, user management |
| **Finance Officer** | `finance@inst001.demo.in` | `Demo@123` | Institution deposit & FDR management, document upload, renewal & release submissions |
| **Institution Reviewer** | `reviewer@inst001.demo.in` | `Demo@123` | Human-in-the-loop OCR review queue, discrepancy resolution notes |
| **AICTE Officer** | `aicte@demo.in` | `Demo@123` | Council-wide checks, Bank Certificate 3 verification, inter-cell clearances, NOC issuance |
| **Auditor** | `auditor@demo.in` | `Demo@123` | Read-only oversight, cryptographic audit hash-chain verification & tamper testing |

*Tip: Quick 1-click login buttons for all 5 roles are provided on the login page.*

---

## 🧪 Key Capabilities & Demonstration Guide

### 1. Repository & Lifecycle Management
- Manage Institutions, Regulatory Security Deposits (APH 2024-2027 Table 1.4 rules), and FDR records.
- Complete state machine progression: `Draft` ➔ `Pending Document` ➔ `Extracting` ➔ `Pending Review` ➔ `Active` ➔ `Maturity Alert` ➔ `Matured` ➔ `Renewed / Replaced / Released / Closed`.

### 2. OCR-Assisted Document Extraction & Review Queue
- Document upload with SHA-256 fingerprinting.
- Mock extraction of FDR attributes with confidence scoring.
- Dedicated **Review Queue** (`/review`) for human reviewers to inspect low-confidence fields before instrument activation.

### 3. Automated Discrepancy Engine (Rules R01 - R15)
- Automated rule execution covering:
  - **R01**: Principal below statutory requirement
  - **R02**: Tenure below minimum regulatory threshold (e.g., < 365 days)
  - **R03**: Maturity date prior to statutory lock-in period
  - **R04**: Non-whitelisted bank (Critical — blocks activation)
  - **R05**: Duplicate FDR numbers across institutions
  - **R06**: Depositor name mismatch with institution title
  - **R07**: Instrument matured but still flagged Active
  - **R13**: Discrepancies between institution records and Bank Certificate 3
  - **R14**: Bank verification pending > 30 days
- Severity levels (`Critical`, `High`, `Medium`, `Low`) with rule toggles in Admin.

### 4. Certificate 3 Independent Bank Verification
- Clear separation between institution submissions and authorized bank certificates.
- Bank Certificate 3 verification flow (`/verification`) with AICTE approval/rejection.

### 5. Staged Maturity Alerting & Escalation
- Automated alert triggers at **90, 30, 15, and 7 days** before maturity.
- Escalation indicator for 7-day alerts unacknowledged for > 3 days.
- In-app notification center and alert acknowledgement tracking.

### 6. Renewal & Traceable Replacement Chaining
- Traceable instrument lineage linking expired FDRs to replacement FDRs.
- Interactive renewal modal on FDR detail (`/fdrs/:id`) and dedicated timeline view (`/renewals`).

### 7. Maker-Checker Release Workflow
- Full release lifecycle (`/releases`) enforcing separation of duties:
  - Document completeness checklist (Release Letter, Affidavit 6, FDR Copy, LoA/EoA).
  - Multi-cell regulatory clearances (**PGRC**, **Vigilance**, **Other Bureau**).
  - Two-step maker-checker sign-off (Maker cannot approve own submission).
  - Council NOC / Sanction Order issuance and final instrument closure.

### 8. Tamper-Evident Cryptographic Audit Trail
- Append-only audit ledger where every mutating action is hashed with SHA-256 into a block-hash chain: `hash = SHA-256(prev_hash + canonical_json(entry))`.
- Real-time cryptographic chain integrity verification (`/audit`).
- **Live Tamper Simulation & Recovery**: Simulate unauthorized database modification, verify that the chain detects tampering with the exact broken block ID, and restore integrity with 1-click.

### 9. Regulatory Reports & Analytics
- 1-click export under `/reports`:
  - **Official FDR Register** (CSV / PDF in landscape with tabular breakdown)
  - **6-Month Maturity Forecast** (PDF with upcoming maturity schedule)
  - **Discrepancy Audit Log** (CSV)

### 10. System Governance & Simulation Clock
- Fast-forward simulation clock (+7, +15, +30, +60, +90 days) on the Dashboard and Admin panel to easily simulate maturity thresholds during live demos.
- Background scheduler triggers for automated alert and discrepancy re-evaluation.

---

## 🛠 Manual Execution (Optional)

### Backend
```cmd
cd fdr-portal\backend
.venv\Scripts\activate
python -m uvicorn src.server:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend
```cmd
cd fdr-portal\frontend
npm run dev
```

### Run Tests
```cmd
cd fdr-portal\backend
.venv\Scripts\python -m pytest
```
*(All 51 compliance & state machine tests passing).*

