# Upstate Agent Reference: Agentic, ML, and Software Concepts

## Purpose
This document summarizes the key concepts used in the Upstate Agent system and explains why each major tool/service was selected. It is meant as a learning reference and a technical handoff artifact.

---

## 1) High-Level Architecture (Current State)

## 1.1 Runtime topology
1. **Web Service (Render)**
- Hosts FastAPI application.
- Exposes REST endpoints (`/v1/...`) and docs (`/docs`).
- Handles orchestration, policy logic, retrieval, and integrations.

2. **Managed PostgreSQL (Render)**
- Stores sessions, messages, policy records, KB chunks, escalations, leads, and audit logs.
- Has `pgvector` extension enabled for vector similarity retrieval path.

3. **External Providers**
- **OpenAI** for intent classification, response generation, and embeddings.
- **Twilio** for SMS/voice webhook ingress (signature verification supported).
- **SMTP provider** for escalation notifications/digest emails.

## 1.2 Request flow (chat)
1. Client calls `POST /v1/chat/message`.
2. LangGraph orchestrator runs deterministic policy checks first (hours/phone/address).
3. If deterministic path not triggered:
- classify intent,
- retrieve context (vector or lexical fallback),
- draft response,
- run guardrails.
4. If risky/low-confidence/emergency -> escalation ticket created.
5. Persist interaction + return structured response.

## 1.3 Request flow (SMS)
1. Twilio posts to `/v1/sms/webhook/twilio`.
2. Signature validated (if enabled).
3. Message mapped to session by hashed phone identifier.
4. Same orchestrator path as web chat.
5. Response returned as TwiML XML.

## 1.4 Request flow (admin)
1. Admin endpoint called with `X-Admin-Key`.
2. Policy update and/or KB reindex/approve action executed.
3. Audit log entry stored.

---

## 2) Agentic AI Concepts Incorporated

1. **Agent Orchestration Graph (LangGraph)**
- We implemented multi-step reasoning as explicit nodes: deterministic -> intent -> retrieve -> draft -> guardrail -> escalate/finalize.
- Benefit: clear control flow, inspectable behavior, deterministic branching.

2. **Tool-Augmented Agent Behavior**
- The agent calls internal tools/services (policy lookup, retrieval, escalation service), rather than generating free-form answers only.
- Benefit: more reliable and operationally aligned responses.

3. **Policy-First Deterministic Routing**
- Certain intents are hard-coded to policy data (hours, phone, address), bypassing model creativity.
- Benefit: reduces hallucinations on business-critical facts.

4. **Guardrails as a First-Class Stage**
- Emergency and low-confidence checks occur after draft generation.
- Benefit: safety/quality governance before final response.

5. **Escalation as an Agent Outcome**
- “I don’t know safely” triggers ticketing instead of forcing an answer.
- Benefit: better trust and reduced harmful responses.

---

## 3) ML/LLM Concepts Incorporated

1. **Intent Classification**
- Query mapped to intent taxonomy (`hours_location_contact`, `appointment_request`, `clinical_risk_or_emergency`, etc.).
- Uses heuristic fallback plus LLM classification.

2. **Retrieval-Augmented Generation (RAG)**
- Website pages are crawled, chunked, and stored with embeddings.
- At response time, relevant chunks are retrieved and passed as context.

3. **Embeddings + Similarity Search**
- Embeddings created using OpenAI embedding model.
- Postgres + pgvector path present; lexical similarity fallback available.

4. **Confidence-Aware Handling**
- Confidence and context availability drive escalation decisions.
- Low confidence or unknowns trigger safer fallback/escalation.

5. **Model Routing Strategy**
- Config supports primary + fallback models.
- Aligns cost/latency with quality targets.

---

## 4) Software Engineering Concepts Incorporated

1. **Service-Oriented API Design**
- Clear endpoint boundaries for chat, admin, integration webhooks, and health/metrics.

2. **Typed Schemas (Pydantic)**
- Request/response models enforce contract correctness and generate OpenAPI docs.

3. **Persistence + Data Modeling (SQLAlchemy)**
- Explicit models for sessions/messages/policies/KB chunks/escalations/leads/audit.

4. **Environment-Driven Configuration**
- Runtime behavior controlled via env vars (`DATABASE_URL`, model names, keys, flags).

5. **Operational Observability**
- Health endpoint + metrics endpoint + request-id middleware.

6. **Security Controls (MVP-level)**
- Admin header key auth.
- Optional Twilio signature validation.
- Secret placeholders in infra config.

7. **Testing Strategy**
- Unit/API tests for chat/admin/webhook behavior.
- Integration-style tests for root/metrics/chat-test and signature validation.
- Lint checks for baseline quality.

8. **Deployment as Code**
- Render blueprint file (`render.yaml`) and CI workflow ensure reproducible setup.

---

## 5) Tool Selection Rationale

## 5.1 FastAPI
- Strong fit for typed REST APIs and automatic docs.
- Fast iteration for backend MVP.
- Excellent Python ecosystem compatibility.

## 5.2 LangGraph
- Better than single-prompt chain for explicit agent state/routing.
- Supports guardrails and deterministic fallbacks cleanly.

## 5.3 PostgreSQL + pgvector
- Single durable store for operational data + semantic retrieval.
- Lower operational complexity than split OLTP + vector DB in early stage.
- Good migration path as scale grows.

## 5.4 Twilio
- Standardized SMS/voice webhook ecosystem.
- Easy integration and production phone tooling.
- Supports security validation on webhooks.

## 5.5 OpenAI Models + Embeddings
- High-quality LLM responses and robust embedding support.
- Unified provider for generation + retrieval vectors.

## 5.6 Render
- Fast deployment path for small-team MVP.
- Managed app + managed Postgres in one platform.
- Good speed-to-production for this project stage.

## 5.7 SMTP Email Integration
- Simple, low-friction escalation path for operations.
- Works with existing staff workflows without requiring CRM first.

---

## 6) Current Capabilities (What it can do now)

1. Live API on Render with health/docs.
2. Create chat sessions and process messages.
3. Handle deterministic policy answers (hours/contact/location).
4. Perform intent-driven response generation with retrieval context.
5. Escalate emergency/unknown-risk cases to ticket records.
6. Receive SMS webhook requests and return TwiML responses.
7. Run voice webhook logic for after-hours messaging.
8. Reindex website content into KB chunks and embeddings.
9. Maintain audit trail for admin operations.
10. Expose metrics for sessions/messages/escalations/leads.

---

## 7) Known Gaps and Recommended Next Work

1. **Vector write-path completion**
- Ensure embeddings are persisted in vector column used by pgvector similarity query.

2. **Security hardening**
- Restrict CORS origins.
- Move from static admin key toward stronger admin auth for long-term use.
- Enable Twilio signature enforcement in production after final webhook verification.

3. **Secrets hygiene**
- Rotate any secrets previously exposed during setup.

4. **Operational hardening**
- Add rate limiting and abuse controls.
- Add load tests and alert thresholds.
- Run backup/restore drills.

5. **Product upgrades**
- Optional direct scheduling integration.
- Optional richer frontend widget UX and transcript analytics dashboard.

---

## 8) Mental Model (Quick Summary)

Think of this system as three layers:
1. **Reliable facts layer** (policy table + deterministic rules).
2. **Intelligent assistant layer** (LLM + retrieval + orchestration).
3. **Operations layer** (escalation, audit, metrics, deploy/runtime controls).

This layered approach is what makes it both useful and safer for real client interactions.
