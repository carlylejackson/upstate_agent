# Phase 1 Closeout Release Notes (Non-PHI)

Date: 2026-03-01  
Release scope: Phase 1 non-PHI build completion and verification

## 1) Summary
Phase 1 is complete for non-PHI operations. The release includes privacy gating, safe handoff behavior for clinical content, inbound message redaction, retention tooling, and expanded test coverage.

## 2) Included changes
1. Compliance mode and privacy config flags.
2. Inbound privacy screening service.
3. Non-PHI short-circuit path in orchestration.
4. Channel-aware handoff and appointment consent wording.
5. Redacted inbound message persistence for web and SMS.
6. Retention cleanup service and admin endpoint:
   - `POST /v1/admin/privacy/retention-run`
7. Privacy incident runbook and Phase 1 release checklist docs.
8. Unit, integration, and system smoke test expansions.
9. Escalation hardening:
   - direct escalation endpoint auth (`X-Escalation-Key`)
   - escalation email excerpt omitted by default
   - optional excerpt path redacted and truncated
   - persisted escalation excerpts redacted at service layer
10. Additional production hardening:
   - production startup safety validation for weak keys/CORS
   - Twilio signature validation default set to enabled
   - optional Redis-backed distributed rate limiting support

## 3) Validation evidence
1. `ruff` checks pass.
2. `pytest` suite passes (`30` tests).
3. Live local system smoke passes:
   - health check
   - session creation
   - deterministic hours
   - non-PHI restricted handoff
   - metrics
4. Deployed smoke sequence passed (operator-confirmed).

## 4) Operational follow-ups (post-closeout)
1. Rotate all previously exposed secrets.
2. Confirm strict production `CORS_ORIGINS`.
3. Confirm `TWILIO_VALIDATE_SIGNATURES=true` in production.
4. Redeploy after secret rotation and re-run smoke checks.

## 5) Runbook pointers
1. `docs/PHASE1_RELEASE_CHECKLIST.md`
2. `docs/PRIVACY_INCIDENT_RUNBOOK.md`
3. Root architecture/user guide:
   - `../PHASE1_NON_PHI_ARCHITECTURE_USER_GUIDE.md`
   - `../PHASE1_NON_PHI_ARCHITECTURE_USER_GUIDE.pdf`
