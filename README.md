# Upstate Agent

Production-ready FastAPI + LangGraph scaffold for a web/SMS support agent with policy grounding, RAG, escalation workflow, and Phase 2 voice webhook support.

## Quick start

```bash
cd upstate_agent
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
uvicorn app.main:app --reload
```

## API

- `GET /v1/health`
- `GET /v1/metrics`
- `POST /v1/chat/session`
- `POST /v1/chat/message`
- `POST /v1/sms/webhook/twilio`
- `POST /v1/voice/webhook/twilio`
- `POST /v1/escalations`
- `POST /v1/admin/policy`
- `POST /v1/admin/kb/reindex`
- `POST /v1/admin/kb/approve`
- `POST /v1/admin/privacy/retention-run`

Test UI:
- `GET /chat-test`

## Notes

- Deterministic business facts (hours, phone, address) are served from policy table.
- Phase 1 defaults to `COMPLIANCE_MODE=non_phi` with medical-content short-circuit and redacted inbound storage.
- No diagnosis responses are allowed; emergency patterns trigger escalation.
- Works with SQLite for local dev and PostgreSQL/pgvector in production.
- Production steps are documented in `docs/DEPLOYMENT_RUNBOOK.md`.
- Privacy operations are documented in `docs/PRIVACY_INCIDENT_RUNBOOK.md`.
