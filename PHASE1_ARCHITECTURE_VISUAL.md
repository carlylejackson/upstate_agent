# Phase 1 Architecture Visual (Non-PHI)

Last updated: 2026-03-01

## 1) End-to-End System View

```mermaid
flowchart LR
    UserWeb["Website User"] --> WebAPI["/v1/chat/session + /v1/chat/message"]
    UserSMS["SMS User"] --> Twilio["Twilio Number"]
    Twilio --> SMSWebhook["/v1/sms/webhook/twilio"]
    StaffOps["Staff/Admin"] --> AdminAPI["/v1/admin/*"]
    Integrator["Internal System"] --> EscAPI["/v1/escalations (X-Escalation-Key)"]

    WebAPI --> Orchestrator["LangGraph Orchestrator"]
    SMSWebhook --> Orchestrator
    EscAPI --> EscSvc["Escalation Service"]
    AdminAPI --> PolicyKB["Policy + KB Services"]

    Orchestrator --> Privacy["Privacy Screen + Redaction"]
    Orchestrator --> Policy["Deterministic Policy Rules"]
    Orchestrator --> Retrieval["Retrieval Service (pgvector / lexical fallback)"]
    Orchestrator --> LLM["LLM Service"]
    Orchestrator --> Guardrail["Guardrail + Escalation Router"]

    Retrieval --> DB[("Postgres + pgvector")]
    Policy --> DB
    Guardrail --> EscSvc
    EscSvc --> DB
    EscSvc --> Email["SMTP Escalation Email (minimal content)"]
    PolicyKB --> DB
    PolicyKB --> Crawl["Website Crawl + Reindex"]
```

## 2) AI/Logic Decision Path

```mermaid
flowchart TD
    Inbound["Inbound Message"] --> Compliance{"Privacy/Compliance Screen"}
    Compliance -- "Restricted clinical/medical text" --> SafeHandoff["Return non-PHI handoff text"]
    SafeHandoff --> Escalate["Create Escalation Ticket (redacted excerpt)"]
    Escalate --> Reply["Respond with ticket acknowledgment"]

    Compliance -- "Allowed text" --> Deterministic{"Deterministic policy hit?"}
    Deterministic -- "Yes" --> PolicyReply["Policy-grounded response"]
    Deterministic -- "No" --> Intent["Intent classification"]
    Intent --> Retrieve["Retrieve top-k knowledge chunks"]
    Retrieve --> Draft["Draft response (LLM/fallback)"]
    Draft --> Guardrail{"Guardrail pass?"}
    Guardrail -- "No/low confidence/risk" --> Escalate
    Guardrail -- "Yes" --> Final["Return final response"]
```

## 3) Retrieval + Knowledge Pipeline

```mermaid
flowchart LR
    Source["Approved Website URLs"] --> Fetch["Crawler Fetch + Clean HTML"]
    Fetch --> Chunk["Semantic Chunking"]
    Chunk --> Embed["Embedding Generation"]
    Embed --> Upsert["KB Upsert"]
    Upsert --> DB[("kb_chunks table + embedding vector")]
    UserQuery["User Query"] --> QueryEmbed["Query Embedding"]
    QueryEmbed --> VecSearch["pgvector similarity search"]
    VecSearch --> Refs["Top-k references"]
    Refs --> Draft["Response drafting context"]
```

## 4) Security and Hardening Controls (Phase 1)

```mermaid
flowchart TD
    Startup["App Startup"] --> ProdCheck{"APP_ENV=production?"}
    ProdCheck -- "Yes" --> Validate["Validate strong keys + strict CORS"]
    Validate --> Run["App starts"]
    ProdCheck -- "No" --> Run

    AdminReq["Admin Request"] --> AdminAuth["X-Admin-Key / ADMIN_API_KEYS"]
    EscReq["Escalation Request"] --> EscAuth["X-Escalation-Key"]
    SMSReq["Twilio Webhook"] --> SigCheck["Twilio Signature Validation"]
    AnyReq["Any Request"] --> RateLimit["Rate Limiting (Redis if configured, in-memory fallback)"]

    Store["Inbound Storage"] --> Redact["PII redaction placeholders"]
    EscStore["Escalation Persistence"] --> EscRedact["Redacted excerpt only"]
    EmailSend["Escalation Email"] --> MinEmail["Excerpt omitted by default"]
```

## 5) Key API Surface (Current)
1. `GET /v1/health`
2. `GET /v1/metrics`
3. `POST /v1/chat/session`
4. `POST /v1/chat/message`
5. `POST /v1/sms/webhook/twilio`
6. `POST /v1/voice/webhook/twilio`
7. `POST /v1/escalations` (requires `X-Escalation-Key`)
8. `POST /v1/admin/policy` (requires `X-Admin-Key`)
9. `POST /v1/admin/kb/reindex` (requires `X-Admin-Key`)
10. `POST /v1/admin/kb/approve` (requires `X-Admin-Key`)
11. `POST /v1/admin/privacy/retention-run` (requires `X-Admin-Key`)

## 6) Quick Operator Mental Model
1. Policy facts answer first.
2. AI answers only where allowed and useful.
3. Risk/uncertainty routes to human escalation.
4. Stored and emailed escalation content is minimized.
5. Production startup blocks unsafe default secrets/config.
