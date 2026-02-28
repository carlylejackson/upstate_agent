# Deployment Runbook (Render + Postgres/pgvector)

## 1. Provision
1. Create Render web service from `upstate_agent`.
2. Create managed Postgres.
3. Set `DATABASE_URL` from Render DB connection string.

## 2. Environment variables
Required:
- `APP_ENV=production`
- `LOG_LEVEL=INFO`
- `ADMIN_API_KEY=<strong-random-value>`
- `OPENAI_API_KEY=<key>`
- `DEFAULT_MODEL=gpt-4.1-mini`
- `FALLBACK_MODEL=gpt-4.1`
- `EMBEDDING_MODEL=text-embedding-3-small`
- `TWILIO_AUTH_TOKEN=<token>`
- `TWILIO_VALIDATE_SIGNATURES=true`
- `SMTP_*` + escalation addresses
- `KB_SOURCE_URLS=<csv urls>`

## 3. DB setup
1. Deploy app once to create base tables.
2. Run `db/migrations/001_pgvector.sql` against Postgres.
3. Run reindex endpoint:
   - `POST /v1/admin/kb/reindex` with `X-Admin-Key`.

## 4. Health checks
- `/v1/health`
- `/v1/metrics`

## 5. Smoke tests
1. Root and docs reachable.
2. Chat deterministic response works.
3. Unknown query escalates.
4. Twilio webhook rejects bad signature when enabled.

## 6. Rollback
1. Roll back Render deploy.
2. If needed, disable `TWILIO_VALIDATE_SIGNATURES` temporarily for incident isolation.
3. Restore previous policy values via admin API.
