# Pragma — Technical Architecture

## System Overview

Pragma is a single-deployment SaaS application: one FastAPI backend serves the web dashboard (static HTML), all API endpoints, and the compliance engine. There is no microservices layer — intentionally simple to operate on Railway with a single PostgreSQL database.

```
┌─────────────────────────────────────────────────────────────────┐
│                         Clients                                 │
│  Browser (SPA)  ·  Mobile (Expo/RN)  ·  SDK  ·  Direct API    │
└────────────┬──────────────┬──────────────┬──────────────────────┘
             │              │              │
             ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (main.py)                     │
│                                                                 │
│  Auth  ·  Firewall  ·  Compliance  ·  Evidence  ·  Billing     │
│  Chat  ·  Batch     ·  Dashboard   ·  Audit     ·  Orgs        │
└────┬────────────────────────────────────────────────────────────┘
     │
     ├──► LLM Orchestrator ──► Pragma model → Claude → OpenAI → mock
     │
     ├──► Risk Detector (heuristic pattern matching)
     │
     ├──► Compliance Engine (15-article EU AI Act checker)
     │
     ├──► Evidence Analyzer (Claude — document + interview scoring)
     │
     ├──► PostgreSQL (Railway) / SQLite (local dev)
     │
     ├──► Resend (transactional email)
     │
     └──► Stripe (billing)
```

---

## Component Breakdown

### 1. FastAPI Backend (`backend/main.py`)

Single-file entrypoint. All endpoints, auth middleware, rate limiting, and static file serving in one place. Key design choices:

- **No router split** — all routes in `main.py`. Simple enough to not warrant fragmentation.
- **Sync + async mix** — most endpoints are `async def` but DB calls are synchronous (SQLAlchemy core, not async). This is fine on Railway where there is one worker process and concurrency is handled by uvicorn's thread pool.
- **Session token auth** — custom `X-Session-Token` header (not JWT). Tokens are 32-byte hex stored in an in-memory dict (per-process). This means sessions are lost on redeploy — acceptable for the current scale.
- **API key auth** — `pragma_*` prefixed keys stored in the DB for SDK use.

### 2. LLM Orchestrator (`backend/llm_orchestrator.py`)

Waterfall fallback chain for compliance analysis:

```
Pragma (custom fine-tuned model on Ollama/HuggingFace)
  → Claude Sonnet (Anthropic SDK)
    → GPT-4o-mini (OpenAI SDK)
      → heuristic mock (always available)
```

Each provider is tried in order; the first success wins. The mock ensures the firewall always returns a result even with no API keys configured (useful for dev). Provider is recorded in the response so clients know which model scored the decision.

### 3. Risk Detector (`backend/risk_detector.py`)

Two-layer detection:

**Layer 1 — Heuristic keyword matching** (runs synchronously, no LLM call)
- 8 risk categories: `bias`, `discrimination`, `privacy`, `transparency`, `fairness`, `autonomy`, `harm`, `manipulation`
- Pattern matching on decision text + context values
- ECOA proxy variable detection: `zip_code`, `last_name`, `ip_country`, `email_domain`, `birth_date`, `age`, etc.

**Layer 2 — LLM analysis** (via orchestrator)
- Generates `confidence_score`, `recommendation`, per-framework ethical analysis
- LLM flags supplement but do not override heuristic flags for blocking decisions

Firewall verdict logic:
```
block            = confidence ≥ threshold AND len(risk_flags) ≥ 2
override_required = len(risk_flags) ≥ 1 AND NOT block
allow            = no flags
```

### 4. Compliance Engine (`backend/compliance_engine.py`)

Evaluates a registered AI system against all 15 EU AI Act articles. Stateless — takes a `system` dict and `stats` dict, returns scores. No DB writes (snapshot saving happens in the endpoint layer).

**Scoring:**
- `pass` = declaration + evidence notes + dated entry → 1.0 points
- `partial` = declaration only (no supporting docs) → 0.5 points
- `fail` = not declared or evidence contradictory → 0.0 points
- `overall_score` = (passes × 1.0 + partials × 0.5) / 15

**Art. 5 special rule:** A prohibited use case (social scoring, real-time biometric, etc.) overrides the verdict to `prohibited` regardless of score. Prohibited systems cannot receive a certificate.

### 5. Evidence Analyzer (`backend/evidence_analyzer.py`)

Claude-powered module for deep evidence validation. Two functions:

**`analyze_document(article_key, title, requirement, filename, file_data)`**
- Extracts text from uploaded files (PDF via `pypdf`, plain text for .txt/.md/.csv)
- Sends document excerpt (max 12,000 chars) to Claude with the specific article's legal requirement
- Returns: `notes`, `date`, `verdict` (pass/partial/insufficient), `explanation`, `confidence`

**`score_interview(article_key, title, requirement, questions_and_answers)`**
- Takes structured Q&A for an article
- Claude evaluates the answers against the legal requirement
- Returns: `notes`, `verdict` (pass/partial/fail), `feedback`, `missing` (list of gaps)

Both functions use the same Claude model (`claude-sonnet-4-6`) with a strict JSON-only system prompt.

### 6. Interview Engine (`backend/interview_engine.py`)

Static data module — no Claude calls. Defines 4–5 article-specific questions for each of the 9 interviewable articles (Art. 4, 9, 10, 11, 17, 25, 27, 30, 33). Questions are written against the actual legal requirement text, not generic governance questions.

### 7. Notifications (`backend/notifications.py` + `backend/email_service.py`)

**Three notification types:**
- `welcome` — sent once on first Google login (36,500 day dedup window)
- `gap_reminder` — sent per-system with FAIL/PARTIAL articles, 30-day cadence
- `countdown` — weekly EU AI Act deadline countdown for users with high-risk systems

**Architecture decisions:**
- Railway cron job (`send_notifications.py`) runs at 09:00 UTC daily — avoids duplicate sends that would happen with in-process APScheduler across multiple instances
- `notification_log` table deduplicates sends at the DB level
- Resend API for transactional email (simpler than SES/SendGrid for this scale)
- All emails include a unique `unsubscribe_token` for one-click unsubscribe

### 8. Database (`backend/database.py`)

SQLAlchemy Core (not ORM). All queries use the expression language, not models. This keeps the schema explicit and avoids magic.

**Tables:**

| Table | Purpose |
|---|---|
| `request_logs` | Every firewall evaluation (anon_id, hash, verdict, flags) |
| `audit_log` | Immutable audit trail with HITL override support |
| `analysis_feedback` | User thumbs up/down on evaluations |
| `waitlist` | Pre-launch email capture |
| `organizations` | Team workspaces |
| `org_members` | User ↔ org membership |
| `api_keys` | `pragma_*` SDK keys with usage tracking |
| `ai_systems` | Registered AI systems with all 15-article evidence fields |
| `compliance_certificates` | Issued certificate records |
| `subscriptions` | Stripe subscription state |
| `users` | Google-authenticated user profiles + unsubscribe token |
| `notification_log` | Sent notification deduplication log |
| `compliance_snapshots` | Daily compliance score snapshots per system (for trend charts) |

**Identity:** Two parallel identity systems:
- `anon_id` = SHA-256 of `google_sub` — used in `request_logs`, `audit_log`, etc. (no PII)
- `google_sub` — used directly in `users`, `ai_systems`, `compliance_snapshots`, `notification_log`

**Migrations:** `init_db()` uses `inspect()` to check for missing columns and runs `ALTER TABLE` statements. This is a simple, dependency-free migration approach suitable for a single-instance deployment.

### 9. Auth (`backend/auth.py`)

- **Google OAuth:** Verifies Google ID tokens using `google.oauth2.id_token.verify_oauth2_token`. Extracts `sub`, `name`, `email`, `picture`.
- **Guest sessions:** Random `guest_{hex}` sub, full feature access, no email.
- **Session store:** In-memory Python dict (`_sessions`). Lost on restart. Acceptable tradeoff — users re-authenticate via Google.
- **Session token:** 32-byte random hex (64-char string) in `X-Session-Token` header.

---

## Data Flow: Firewall Evaluation

```
POST /evaluate-decision
        │
        ▼
  parse + validate request
        │
        ▼
  detect_all_risks(decision, context, category)
    ├── keyword heuristics
    └── detect_fintech_proxy_variables(context)
        │
        ▼
  llm_orchestrator.evaluate(decision, context)
    → confidence_score, regulatory_refs, ethical analyses
        │
        ▼
  _compute_firewall(risk_flags, confidence_score)
    → firewall_action, should_block
        │
        ▼
  write to audit_log (anon_id, hash, verdict, flags)
        │
        ▼
  return EthicalAnalysis response
```

## Data Flow: Compliance Check + Snapshot

```
GET /ai-systems/{id}/compliance
        │
        ▼
  get_ai_system(system_id, google_sub)  ← ownership check
        │
        ▼
  get_audit_stats_for_system(google_sub)
        │
        ▼
  compute_compliance(system, stats)
    → 15 article statuses, overall_score, verdict
        │
        ├──► save_compliance_snapshot()  ← once per day, non-fatal
        │
        └──► return compliance result
```

## Data Flow: Evidence Upload

```
POST /evidence/extract  (multipart)
        │
        ├── read file bytes (max 10 MB)
        │
        ├── _extract_text(filename, bytes)
        │     ├── .pdf → pypdf PdfReader
        │     └── .txt/.md/.csv → UTF-8 decode
        │
        ├── truncate to 12,000 chars
        │
        ├── claude: analyze_document(article_key, requirement, doc_text)
        │     → {notes, date, verdict, explanation, confidence}
        │
        └── return result (frontend auto-fills wizard fields)
```

---

## Frontend Architecture (`frontend/index.html`)

Single HTML file — no build step, no framework, no bundler. Served by FastAPI's static file handler.

**Why single file:** Minimises deployment complexity. Everything ships as one response with no asset pipeline.

**Key JS patterns:**
- `esc(str)` — XSS-safe text insertion via `document.createTextNode()`
- `switchTab(name)` — tab routing with URL state
- `sessionToken` — global variable set on auth, sent as `X-Session-Token` header on all API calls
- All API calls are `async/await` fetch with error handling

**Tab structure:**
```
Evaluate  →  single decision firewall
History   →  paginated decision log
Batch     →  CSV upload + results download
Audit     →  audit trail with override panel
EU AI Act →  system registration wizard + compliance checklist + certificate download
Dashboard →  score trend sparklines + article heatmap + deadline countdown
Settings  →  billing, orgs, API keys, notification preferences
```

**EU AI Act wizard:** 5-step flow collecting all 15 articles' evidence. Steps 4–5 include "📄 Upload doc" and "💬 Interview" buttons that call the evidence API and auto-fill fields.

**Dashboard:** Loads on tab activation. Calls `/dashboard/summary`, renders:
- Deadline countdown bar (days to 1 Aug 2026, colour by urgency)
- Summary stat cards
- Per-system cards with SVG sparkline trend charts (no chart library — pure `<polyline>`)
- 15-article heatmap grid (✓/~/✗ per article per system)

---

## Deployment Architecture (Railway)

```
GitHub main branch
        │  push
        ▼
Railway build (Nixpacks)
  pip install -r requirements.txt
        │
        ▼
Railway service
  uvicorn backend.main:app --host 0.0.0.0 --port $PORT
        │
        ├── Serves frontend/index.html
        ├── Handles all API requests
        └── Connects to PostgreSQL plugin (DATABASE_URL auto-injected)

Railway cron (daily 09:00 UTC)
  python send_notifications.py
        │
        └── Sends welcome / gap reminder / countdown emails via Resend
```

**Environment variables required:**

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Auto-injected by Railway PostgreSQL plugin |
| `ANTHROPIC_API_KEY` | Claude (compliance engine + evidence analyzer) |
| `OPENAI_API_KEY` | GPT-4o-mini fallback |
| `GOOGLE_CLIENT_ID` | Google OAuth token verification |
| `RESEND_API_KEY` | Transactional email |
| `EMAIL_FROM` | Sender address e.g. `Pragma <notifications@usepragma.co>` |
| `APP_URL` | Production URL for email links |
| `STRIPE_SECRET_KEY` | Billing |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signature verification |
| `STRIPE_GROWTH_PRICE_ID` | Growth plan price ID |
| `ALLOWED_ORIGINS` | CORS allowlist |

---

## Testing Architecture

**Framework:** pytest + pytest-asyncio + httpx TestClient

**Database isolation:** `StaticPool` in-memory SQLite per test run. `conftest.py` patches `_engine` before any module imports so tests never touch the real DB.

**Coverage threshold:** 80% enforced in CI. Current: 82.5% across 434 tests.

**Test file map:**

| File | What it covers |
|---|---|
| `test_api.py` | All HTTP endpoints (78 tests) |
| `test_compliance.py` | 15-article engine, evidence scoring, prohibition detection, certificate PDF |
| `test_fintech_compliance.py` | Proxy variable guard, audit trail, HITL override |
| `test_regulations.py` | Regulatory reference mapping |
| `test_orgs_and_api_keys.py` | Org lifecycle, API key CRUD |
| `test_auth.py` | Session management, Google OAuth, guest sessions |
| `test_notifications.py` | Email templates, notification logic, deduplication |
| `test_evidence.py` | Document extraction, interview scoring, question engine |

---

## Security Controls

| Control | Implementation |
|---|---|
| XSS | `esc()` helper uses `document.createTextNode()` for all dynamic HTML |
| CORS | Explicit `ALLOWED_ORIGINS` allowlist — no wildcard |
| Input limits | Decision ≤ 4,000 chars; context ≤ 8,000 chars; file uploads ≤ 10 MB |
| SQL injection | Migration `ALTER TABLE` column names validated with `^[a-z_][a-z0-9_]*$` |
| Stripe webhooks | `stripe.WebhookSignature.verify_header()` before any processing |
| Auth | Session tokens are 32-byte random hex; no JWTs to decode client-side |
| PII | Raw decision text is never stored — only `sha256(input)` in `request_logs` |
| File uploads | Type checked by extension; PDF parsed in-memory; no disk writes |
