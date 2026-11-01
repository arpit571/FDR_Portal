# 🏛 FDR SmartTrack Portal — SIH 26265 MVP
**AICTE Regulation Bureau — Security Deposit & Fixed Deposit Receipt (FDR) Management System**

FDR SmartTrack Portal is a production-grade web system for AICTE-recognized technical institutions to record, verify, track, renew, and release regulatory security deposits and the Fixed Deposit Receipts (FDRs) backing them.

---

## 🚀 One-Click Launch

Double-click `start_mvp.bat` in this folder or run:
```cmd
start_mvp.bat
```
This automatically launches:
1. **Backend**: FastAPI on `http://127.0.0.1:8000` (Interactive Swagger docs at `http://127.0.0.1:8000/api/docs`)
2. **Frontend**: React + Vite UI on `http://localhost:5173`
3. Opens your default web browser to `http://localhost:5173`.

---

## 👥 Demo Accounts (Password: `Demo@123`)

| Role | Email | Password | Primary Capabilities |
|---|---|---|---|
| **Super Admin** | `superadmin@demo.in` | `Demo@123` | Full governance, bank whitelist, demo clock, discrepancy rules, user management |
| **Finance Officer** | `finance@inst001.demo.in` | `Demo@123` | Institution deposit & FDR management, document upload, renewal & release submissions |
| **Institution Reviewer** | `reviewer@inst001.demo.in` | `Demo@123` | Human-in-the-loop OCR review queue, discrepancy resolution notes |
| **AICTE Officer** | `aicte@demo.in` | `Demo@123` | Council-wide checks, Bank Certificate 3 verification, inter-cell clearances, NOC issuance |
| **Auditor** | `auditor@demo.in` | `Demo@123` | Read-only oversight, cryptographic audit hash-chain verification & tamper testing |

*Tip: Quick 1-click login buttons for all 5 roles are provided on the login page.*

---

## 🧪 Key Capabilities

1. **Repository & Lifecycle Management**: Centralized records for Institutions, Security Deposits (APH Table 1.4 rules), and FDRs with state machine progression.
2. **OCR-Assisted Document Extraction & Review**: File upload with SHA-256 fingerprinting, field confidence scores, and dedicated Human-in-the-Loop review queue.
3. **Automated Discrepancy Engine**: 15 automated compliance checks (R01-R15) with severity classification and blocking activation on Critical issues.
4. **Certificate 3 Independent Bank Verification**: Bank certificate records and AICTE verification/rejection workflow.
5. **Maturity & Staged Alerting**: Proactive alerts at 90, 30, 15, and 7 days prior to maturity, with 3-day escalation indicators.
6. **Renewal & Replacement Tracking**: Traceable instrument chaining linking expired FDRs to active replacement instruments.
7. **Maker-Checker Release Workflow**: Clearances (PGRC, Vigilance, Other Bureau), 2-step approval sign-off, NOC recording, and closure.
8. **Tamper-Evident Cryptographic Audit Trail**: Append-only ledger secured by SHA-256 block-hash chaining with on-demand verification and live tamper simulation.
9. **Regulatory Reports & Analytics**: 1-click export of Official FDR Register (PDF/CSV), 6-Month Maturity Forecast (PDF), and Discrepancy Log (CSV).
10. **Simulation Clock**: Fast-forward simulation clock to easily demonstrate maturity transitions during evaluation.

