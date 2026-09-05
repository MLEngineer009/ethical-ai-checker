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
│  Analytics  ·  Rule Engine  ·  Adverse Action                  │
└────┬────────────────────────────────────────────────────────────┘
     │
     ├──► L1 Compliance Engine (deterministic, <5ms, always runs)
     │     ├── HOLC geo redlining (500+ zip codes, 35 US cities)
     │     ├── ECOA proxy variable detection
     │     ├── Text scanner (14 direct + indirect phrasing patterns)
     │     ├── Compound proxy threshold scoring
     │     ├── Disparate impact risk (4/5ths rule)
     │     └── State law overlays (CA, NY, IL)
     │
     ├──► L2 LLM Orchestrator (optional, waterfall)
     │     └── Pragma model → Claude → GPT-4o-mini → heuristic mock
     │
     ├──► EU AI Act Compliance Engine (15-article scoring)
     │
     ├──► Evidence Analyzer (Claude — document + interview scoring)
     │
     ├──► Dynamic Rule Engine (DB-backed, per-org overrides)
     │
     ├──► Analytics (PostHog + own DB — non-PII user metrics)
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

Single-file entrypoint. All endpoints, auth middleware, rate limiting, and static file serving in one place.

Key design choices:
- **No router split** — all routes in `main.py`. Simple enough to not warrant fragmentation.
- **Sync + async mix** — most endpoints are `async def` but DB calls are synchronous (SQLAlchemy core, not async). Fine on Railway where concurrency is handled by uvicorn's thread pool.
- **Session token auth** — custom `X-Session-Token` header (not JWT). Tokens are 32-byte hex stored in an in-memory dict. Sessions are lost on redeploy — acceptable tradeoff.
- **API key auth** — `pragma_*` prefixed keys stored in the DB for SDK use.

### 2. L1 Compliance Engine (`backend/compliance_engine.py`)

Deterministic compliance checking that runs on every request — no LLM, no external call, no variable latency. Checks:

- **HOLC geo redlining** — 500+ historically redlined zip codes across 35 US cities (`geo_data.py`). `is_redlined(zip_code)` returns `(bool, city_name)`.
- **ECOA proxy variable detection** — `zip_code`, `last_name`, `ip_country`, `email_domain`, `birth_date`, `age` and 6+ others flagged as protected-class proxies.
- **Text scanner** — 14 regex pattern groups covering direct and indirect protected-class language:
  - Direct: race, national_origin, sex, age, disability, religion, familial_status, public_assistance
  - Indirect: "that part of town", "near retirement", "family obligations", "non-native speaker", etc.
- **Compound proxy threshold** — flags when N proxy variables appear in the same decision context.
- **Disparate impact risk** — flags when the decision pattern suggests group-level adverse impact.
- **State law overlays** — jurisdiction-specific rules for CA (FEHA), NY (HRL), IL (HRA).
- **ECOA §1002.9** — checks for required written adverse action reasons.

Each check accepts an optional `rule_config` dict from the dynamic rule engine (see below).

**Rule result statuses:** `FAIL` (block), `FLAG` (human review), `PASS` (allowed)

### 3. Dynamic Rule Engine (DB tables: `compliance_rules`, `org_rule_overrides`)

All compliance rules are stored in the database rather than hardcoded. This means:

- **Configurable thresholds** — `compound_proxy_threshold` has `flag_at`/`fail_at` values editable per org.
- **Per-org severity overrides** — an enterprise org can change a FAIL to FLAG for a specific rule.
- **Enable/disable rules** — orgs can turn off inapplicable jurisdiction overlays.
- **No code deploy needed** — rule changes take effect immediately.

`get_effective_rules(org_id)` merges global defaults with org overrides and returns the full rule set. `run_compliance_checks()` loads this at evaluation time and passes `rule_config` to each checker that accepts it (via `inspect.signature`).

15 default rules seeded on first boot:
`text_scanner_race`, `text_scanner_national_origin`, `text_scanner_sex`, `text_scanner_age`, `text_scanner_disability`, `text_scanner_religion`, `text_scanner_familial`, `text_scanner_public_assistance`, `compound_proxy_threshold`, `disparate_impact_threshold`, `employment_gap_months`, `state_overlay_ca`, `state_overlay_ny`, `state_overlay_il`, `ecoa_adverse_action_notice`, `geo_redlining`

### 4. LLM Orchestrator (`backend/llm_orchestrator.py`)

Waterfall fallback chain for deeper risk analysis (L2). Runs after L1 when enabled:

```
Pragma (custom fine-tuned model on Ollama/HuggingFace)
  → Claude Sonnet (Anthropic SDK)
    → GPT-4o-mini (OpenAI SDK)
      → heuristic mock (always available)
```

Provider recorded in the response so clients know which model scored the decision.

### 5. EU AI Act Compliance Engine (`backend/compliance_engine.py`)

Evaluates a registered AI system against all 15 EU AI Act articles. Stateless — takes a `system` dict and `stats` dict, returns scores.

**Scoring:**
- `pass` = declaration + evidence notes + dated entry → 1.0 points
- `partial` = declaration only → 0.5 points
- `fail` = not declared or contradictory evidence → 0.0 points
- `overall_score` = (passes × 1.0 + partials × 0.5) / 15

**Art. 5 special rule:** A prohibited use case overrides the verdict to `prohibited` regardless of score.

### 6. Evidence Analyzer (`backend/evidence_analyzer.py`)

Claude-powered module for deep evidence validation.

**`analyze_document(article_key, title, requirement, filename, file_data)`**
- Extracts text from PDF (pypdf) or plain text files
- Sends document excerpt (max 12,000 chars) to Claude with the specific article's legal requirement
- Returns: `notes`, `date`, `verdict` (pass/partial/insufficient), `explanation`, `confidence`

**`score_interview(article_key, title, requirement, questions_and_answers)`**
- Takes structured Q&A for an article
- Claude evaluates the answers against the legal requirement
- Returns: `notes`, `verdict`, `feedback`, `missing` (list of gaps)

### 7. Adverse Action Notice Generator

`POST /adverse-action-notice` generates ECOA §1002.9 + FCRA §615(a) compliant HTML denial notices. Accepts the decision context and returns a structured HTML document with correct statutory language, required disclosures, and timing guidance.

### 8. Disparate Impact Analysis (`POST /disparate-impact`)

Accepts a JSON array of decisions with demographic fields and applies the EEOC 4/5ths rule:
- Identifies the highest-selection-rate group as the baseline
- Flags any group with selection rate < 80% of the baseline as "ADVERSE IMPACT"
- Returns group breakdown, disparity ratios, and applicable regulatory references

### 9. Analytics (`backend/database.py` tables: `user_profiles`, `feature_events`)

Non-PII customer metadata system. Two components:

**PostHog (behavioral):** Lazy-initialized from `/config/public` — key never hardcoded in HTML. Tracks behavioral events with session replay and funnel analysis.

**Own DB (business metrics):**
- `user_profiles` — per-user aggregate: plan_tier, session_count, total_evaluations, primary_category, features_used JSON, has_api_key, has_org
- `feature_events` — append-only event log: event_name, properties JSON, session_id, timestamp

Key functions:
- `upsert_user_profile(google_sub, login_method, plan_tier, timezone, locale)` — insert or update on every login
- `track_feature_event(google_sub, event_name, properties, session_id)` — append event, update features_used
- `get_analytics_summary()` — returns DAU/WAU/MAU, login_methods, plan_dist, category_usage, feature_adoption, session_depth, timezone_dist, new_users_by_day, event_volume_by_day, top_events

Admin analytics dashboard visible in-app for admin users only (gated by `ADMIN_EMAIL` env var).

### 10. Notifications (`backend/notifications.py` + `backend/email_service.py`)

Three notification types:
- `welcome` — sent once on first Google login (36,500 day dedup window)
- `gap_reminder` — sent per-system with FAIL/PARTIAL articles, 30-day cadence
- `countdown` — weekly EU AI Act deadline countdown for users with high-risk systems

Railway cron job (`send_notifications.py`) runs at 09:00 UTC daily. `notification_log` table deduplicates sends at the DB level.

### 11. Database (`backend/database.py`)

SQLAlchemy Core (not ORM). All tables:

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
| `compliance_snapshots` | Daily compliance score snapshots per system |
| `compliance_rules` | DB-backed rule definitions with config JSON |
| `org_rule_overrides` | Per-org severity/enabled/config customizations |
| `user_profiles` | Non-PII user metadata for analytics |
| `feature_events` | Append-only behavioral event log |

**Identity:** Two parallel identity systems:
- `anon_id` = SHA-256 of `google_sub` — used in `request_logs`, `audit_log`, `user_profiles`, `feature_events`
- `google_sub` — used in `users`, `ai_systems`, `compliance_snapshots`, `notification_log`

---

## Data Flow: Firewall Evaluation

```
POST /evaluate-decision
        │
        ▼
  parse + validate request
        │
        ▼
  database.get_effective_rules(org_id)
        │
        ▼
  run_compliance_checks(decision, context, category, rule_config)
    ├── HOLC geo redlining check
    ├── ECOA proxy variable detection
    ├── Text scanner (direct + indirect patterns)
    ├── Compound proxy threshold (rule_config.flag_at / fail_at)
    ├── Disparate impact risk (rule_config.flag_at / fail_at)
    ├── State law overlays (CA/NY/IL if enabled)
    └── ECOA adverse action notice check
        │
        ▼
  llm_orchestrator.evaluate(decision, context)  [L2, optional]
    → confidence_score, regulatory_refs, ethical analyses
        │
        ▼
  _compute_firewall(compliance_checks, risk_flags, confidence_score)
    → firewall_action: block | override_required | allow
        │
        ▼
  write to audit_log (anon_id, hash, verdict, checks)
        │
        ▼
  track_feature_event(google_sub, 'decision_evaluated', {category, firewall_action})
        │
        ▼
  return EthicalAnalysis response
```

## Data Flow: JSON-LD Audit Export

```
GET /audit/export?format=jsonld
        │
        ▼
  database.get_audit_jsonld(google_sub, limit=500)
        │
        ├── Fetches all audit_log rows for user
        ├── Builds W3C PROV-compatible @context
        └── Returns JSON-LD document with:
              @context (timestamp, firewallAction, inputHash, ...)
              @type: "ComplianceAuditLog"
              entries: [{...each decision...}]
        │
        ▼
  Return as application/ld+json attachment
```

## Data Flow: Adverse Action Notice

```
POST /adverse-action-notice
  { decision, context, category, denial_reasons? }
        │
        ▼
  Build ECOA §1002.9 + FCRA §615(a) compliant HTML document
        │
        ├── Statutory denial reason language
        ├── Required CRA disclosure (if credit decision)
        ├── Applicant rights statement
        ├── Timeline guidance (30-day notice requirement)
        └── Signature block
        │
        ▼
  Return text/html document ready to send or download
```

---

## Frontend Architecture (`frontend/index.html`)

Single HTML file — no build step, no framework, no bundler. Served by FastAPI's static file handler.

**Tab structure:**
```
Evaluate   →  single decision firewall + compliance checks
History    →  paginated decision log
Batch      →  CSV upload + results download
Audit      →  audit trail with override panel + JSON-LD export
EU AI Act  →  system registration wizard + compliance checklist + certificate download
Dashboard  →  score trend sparklines + article heatmap + admin analytics panel
Demo       →  live Affirm BNPL + Workday hiring + Gemini chatbot scenarios
Settings   →  billing, orgs, API keys, compliance rule engine, notifications
```

**Analytics instrumentation (pragmaTrack):**
- `user_logged_in` — Google + guest login
- `tab_viewed` — every tab switch
- `decision_evaluated` — category, firewall_action, fail_count, flag_count
- `batch_uploaded` — file name
- `report_downloaded` — category
- `scenario_run` — scenario_id, use_case
- `api_key_created`
- `audit_exported` — format: jsonld
- `compliance_rules_viewed` — rule_count

**Admin-only features:** Admin analytics dashboard in Dashboard tab (DAU/WAU/MAU, feature adoption, top events, category usage, plan distribution, new users). Visible only when `is_admin` returned from auth.

**Landing pages:**
- `frontend/index.html` — main app (usepragma.co)
- `frontend/lending.html` — lending vertical landing page (lending.usepragma.co)

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
        ├── Serves frontend/index.html + lending.html
        ├── Handles all API requests
        └── Connects to PostgreSQL plugin (DATABASE_URL auto-injected)

Railway cron (daily 09:00 UTC)
  python send_notifications.py
        │
        └── Sends welcome / gap reminder / countdown emails via Resend
```

**Environment variables:**

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Auto-injected by Railway PostgreSQL plugin |
| `ANTHROPIC_API_KEY` | Claude (L2 analysis + evidence analyzer) |
| `OPENAI_API_KEY` | GPT-4o-mini fallback |
| `GOOGLE_CLIENT_ID` | Google OAuth token verification |
| `RESEND_API_KEY` | Transactional email |
| `EMAIL_FROM` | Sender address e.g. `Pragma <notifications@usepragma.co>` |
| `APP_URL` | Production URL for email links |
| `STRIPE_SECRET_KEY` | Billing |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signature verification |
| `STRIPE_GROWTH_PRICE_ID` | Growth plan price ID |
| `ALLOWED_ORIGINS` | CORS allowlist |
| `POSTHOG_API_KEY` | PostHog behavioral analytics (optional) |
| `POSTHOG_HOST` | PostHog host (default: https://us.i.posthog.com) |
| `ADMIN_EMAIL` | Email address with admin dashboard access (default: chak.utd@gmail.com) |

---

## Testing Architecture

**Framework:** pytest + pytest-asyncio + httpx TestClient

**Database isolation:** `StaticPool` in-memory SQLite per test run. `conftest.py` patches `_engine` before any module imports so tests never touch the real DB.

**Coverage threshold:** 80% enforced in CI. Current: 80.46% across 512 tests.

**Test file map:**

| File | What it covers |
|---|---|
| `test_api.py` | All HTTP endpoints |
| `test_compliance.py` | 15-article EU AI Act engine, evidence scoring, certificate PDF |
| `test_fintech_compliance.py` | HOLC geo data, text scanner, compound proxies, ECOA, disparate impact, state laws |
| `test_orgs_and_api_keys.py` | Org lifecycle, API key CRUD, dynamic rule engine, JSON-LD export, analytics DB functions |
| `test_auth.py` | Session management, Google OAuth, guest sessions |
| `test_notifications.py` | Email templates, notification logic, deduplication |
| `test_evidence.py` | Document extraction, interview scoring, question engine |
| `test_regulations.py` | Regulatory reference mapping |
| `test_disparity_analysis.py` | Disparate impact 4/5ths rule |

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
| PII | Raw decision text never stored — only `sha256(input)` in `request_logs` |
| Analytics PII | `/track` endpoint strips email, name, phone before storing; uses `anon_id = sha256(google_sub)` |
| File uploads | Type checked by extension; PDF parsed in-memory; no disk writes |
| Admin gating | `_is_admin()` checks email against `ADMIN_EMAIL` env var — admin endpoints 403 for all other users |
