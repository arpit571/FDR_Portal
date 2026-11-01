# FDR SmartTrack Portal — SIH 26265 Consolidated Specification
AICTE Regulation Bureau — Security Deposit & Fixed Deposit Receipt (FDR) Management System

## 1. Product Summary & Scope
A centralized web portal where AICTE-recognized institutions record their regulatory security deposits and the Fixed Deposit Receipts (FDRs) that back them.

### Core Capabilities
1. **Repository & Lifecycle Management**: Centralized records for Institutions, Security Deposits, and FDRs with full state machine progression.
2. **OCR-Assisted Document Extraction & Review**: Document upload with SHA-256 fingerprinting, field extraction with confidence scores, and human-in-the-loop review queue for low-confidence fields.
3. **Automated Discrepancy Engine**: 15 automated compliance checks (minimum tenure, minimum amount, non-whitelisted banks, maturity before lock-in, duplicate FDR numbers, name mismatch, lien encumbrances).
4. **Certificate 3 Independent Bank Verification**: Separation between institution-submitted data and authorized bank-issued Certificate 3 confirmations.
5. **Maturity & Staged Alerting**: Scheduled reminders at 90, 30, 15, and 7 days prior to maturity, with escalation indicators.
6. **Renewal & Replacement Tracking**: Traceable instrument chaining linking expired FDRs to active replacement instruments.
7. **Maker-Checker Release Workflow**: Formal release request processing requiring cell clearances (PGRC, Vigilance) and two-step sign-off before Council NOC and closure.
8. **Tamper-Evident Cryptographic Audit Trail**: Append-only ledger secured by SHA-256 block-hash chaining with an on-demand verification endpoint.
9. **Regulatory Reports & Analytics**: 1-click export of Official FDR Register (PDF/CSV), 6-Month Maturity Forecast (PDF), and Discrepancy Audit Log (CSV).
10. **System Governance**: Fast-forward simulation clock, bank whitelist management, user RBAC, and APH Table 1.4 regulatory deposit rules.

## 2. User Roles & RBAC Matrix
- **SUPER_ADMIN**: Full system governance, regulatory rules, bank whitelist, demo clock, user creation.
- **FINANCE_OFFICER**: Institution-scoped; creates/edits deposits and FDRs, uploads documents, requests renewals and releases.
- **REVIEWER**: Institution-scoped; human-in-the-loop OCR review, discrepancy resolution, Step 1 release review.
- **AICTE_OFFICER**: Council-wide checker; verifies bank Certificate 3 records, clears regulatory cells, Step 2 release approval, issues NOCs.
- **AUDITOR**: Read-only oversight across all institutions; verifies cryptographic hash-chain integrity.

## 3. Demo Accounts (Password: Demo@123)
| Role | Email |
|---|---|
| Super Admin | superadmin@demo.in |
| Finance Officer | finance@inst001.demo.in |
| Institution Reviewer | reviewer@inst001.demo.in |
| AICTE Officer | aicte@demo.in |
| Auditor | auditor@demo.in |

