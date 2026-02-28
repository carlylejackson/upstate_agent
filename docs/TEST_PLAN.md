# Test Plan

## Automated
- Unit/API tests: `pytest`
- Lint: `ruff check app tests`

## Manual
- `/docs` chat session and message flow
- Admin policy updates with `X-Admin-Key`
- KB reindex/approval flow
- Twilio webhook form simulation
- Browser widget test at `/chat-test`

## Pre-production integration
- Twilio signed request validation with real credentials
- SMTP escalation delivery verification
- Postgres + pgvector retrieval quality checks
