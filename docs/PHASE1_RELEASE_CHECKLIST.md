# Phase 1 Release Checklist (Non-PHI Mode)

Last updated: 2026-02-28

## 1) Goal
Release Phase 1 safely with non-PHI behavior enforced across web and SMS.

## 2) Pre-deploy checklist
1. Confirm branch includes Phase 1 files:
   - `app/services/privacy_service.py`
   - `app/services/retention_service.py`
   - updated `app/services/orchestration.py`
   - updated chat/SMS routes
2. Local quality gates:
   - `python -m ruff check app tests`
   - `python -m pytest -q`
3. Confirm docs updated:
   - `docs/PRIVACY_INCIDENT_RUNBOOK.md`
   - sprint/status files in project root

## 3) Production env checklist (Render)
Set or confirm:
1. `APP_ENV=production`
2. `COMPLIANCE_MODE=non_phi`
3. `REDACT_STORED_MESSAGES=true`
4. `NON_PHI_HANDOFF_MESSAGE=<approved web copy>`
5. `NON_PHI_HANDOFF_MESSAGE_SMS=<approved sms copy>`
6. `RETENTION_DAYS_MESSAGES=30` (or your approved number)
7. `RETENTION_DAYS_ESCALATIONS=90` (or your approved number)
8. `TWILIO_VALIDATE_SIGNATURES=true`
9. `CORS_ORIGINS=<strict website origins>`

## 4) Post-deploy smoke tests (system checks)
Use your deployed docs or API client.

1. Health:
   - `GET /v1/health` returns `status=ok` and `app_env=production`.
2. Deterministic policy:
   - Ask business hours and verify exact policy-grounded response.
3. Non-PHI restricted path:
   - Submit: "I have tinnitus and dizziness for 3 days"
   - Expect safe handoff messaging and escalation.
4. Emergency path:
   - Submit: "I have chest pain and severe dizziness"
   - Expect urgent disclaimer and escalation.
5. SMS path:
   - Send restricted medical text to Twilio webhook.
   - Expect non-PHI SMS template (no diagnostic language).
6. Retention endpoint:
   - `POST /v1/admin/privacy/retention-run` dry-run first.
   - Validate counts and run execute mode when approved.

## 5) Rollback triggers
Rollback immediately if:
1. PHI-like content appears unredacted in persisted messages/logs.
2. Restricted medical content does not short-circuit.
3. Twilio signature enforcement is bypassed unexpectedly.
4. Error rate spikes above acceptable threshold.

## 6) Sign-off record (fill during release)
1. Date/time (UTC):
2. Deployed commit:
3. Operator:
4. Smoke tests passed (yes/no):
5. Rollback required (yes/no):
6. Notes:
