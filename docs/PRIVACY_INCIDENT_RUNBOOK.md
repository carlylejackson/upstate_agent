# Privacy Incident Runbook (Phase 1 `non_phi`)

Last updated: 2026-02-28

## 1) Trigger conditions
Start this runbook if any of the following occurs:
1. PHI/PII appears in logs, alerts, or exported reports.
2. A user reports sensitive data leakage.
3. Staff observes unsafe model behavior requesting or exposing clinical details.
4. Misconfigured environment weakens privacy controls.

## 2) Immediate response (first 30 minutes)
1. Acknowledge incident internally and assign incident owner.
2. Freeze risky surfaces:
   - disable SMS webhook traffic if needed
   - disable new reindex jobs if data contamination is suspected
3. Capture evidence:
   - request IDs
   - timestamps (UTC)
   - impacted endpoints/channels
   - sample records IDs (not full PHI payloads in shared channels)
4. Confirm current env values:
   - `COMPLIANCE_MODE=non_phi`
   - `REDACT_STORED_MESSAGES=true`
   - `TWILIO_VALIDATE_SIGNATURES=true` (production)

## 3) Containment actions
1. Rotate exposed secrets immediately (API keys, DB creds, webhook auth tokens).
2. Redact or purge impacted records using retention/cleanup tooling.
3. Temporarily force escalation-only response mode for affected channels if necessary.
4. Restrict admin endpoints to known IP sources if abuse is suspected.

## 4) Technical verification checklist
1. Verify redaction placeholders appear in stored inbound messages.
2. Verify restricted medical content short-circuits to safe handoff.
3. Verify emergency terms route to urgent disclaimer/escalation path.
4. Verify audit log captured incident-related admin actions.
5. Re-run automated tests and smoke tests before restoring normal traffic.

## 5) Communication workflow
1. Internal update to operations owner with severity and scope.
2. Staff-facing summary:
   - what happened
   - affected channels/time window
   - temporary operating mode
3. If required by policy/law, escalate to legal/compliance advisor for notification obligations.

## 6) Recovery and hardening
1. Patch root cause and deploy.
2. Reindex/cleanup if data state was impacted.
3. Add regression test that would have caught this incident.
4. Update this runbook and project status file with lessons learned.

## 7) Post-incident close criteria
1. Root cause identified and documented.
2. Fix deployed and validated in production.
3. Evidence package retained:
   - timeline
   - actions
   - tests
   - approvals
4. Owner signs off and incident status marked closed.
