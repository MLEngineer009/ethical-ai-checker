# Pragma — AI Compliance Firewall

An API-first compliance enforcement layer for AI systems. Pragma evaluates decisions against regulatory policy (EU AI Act, EEOC, GDPR, NYC LL144, CFPB), blocks violations before they execute, and generates audit-ready evidence — available as a web dashboard, mobile app, and Python SDK.

## Quick Start

### 1. Setup Environment
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure API Keys
```bash
export ANTHROPIC_API_KEY=your_anthropic_key        # primary LLM
export OPENAI_API_KEY=your_openai_key              # fallback LLM
export GOOGLE_CLIENT_ID=your_google_client_id      # for Google Sign-In
export DATABASE_URL=postgresql://...               # PostgreSQL connection string
export STRIPE_SECRET_KEY=sk_live_...              # Stripe billing (optional)
export STRIPE_WEBHOOK_SECRET=whsec_...            # Stripe webhook signature
export STRIPE_GROWTH_PRICE_ID=price_...           # Stripe Growth plan price ID
export ALLOWED_ORIGINS=https://yourdomain.com     # CORS allowlist (comma-separated)
```

### 3. Run Backend
```bash
uvicorn backend.main:app --reload
# API available at http://localhost:8000
# Web dashboard at http://localhost:8000
```

### 4. Health Check
```bash
curl http://localhost:8000/health-check
```

### 5. Demo Quick Start (optional)

Pre-seed a fictional EU high-risk AI system (LoanSight AI by Veridian Finance SA) for a live demo or investor presentation — no wizard required:

```bash
python seed_demo.py
# Seeds system_id, then visit the Compliance tab → click the system → Generate Certificate
```

The demo system produces a realistic mix of compliance verdicts:
- Art. 4 AI Literacy → **PASS** (declaration + evidence notes + date)
- Art. 17 QMS → **PARTIAL** (declaration only, no supporting docs)
- Art. 25 Instructions → **PASS** (deployer handbook reference)
- Art. 25 Monitoring → **PASS** (drift alerts with start date)
- Art. 27 FRIA → **FAIL** (not conducted — critical gap)
- Art. 30 EU DB Registration → **PARTIAL** (no registration number yet)
- Art. 33 Conformity Assessment → **PARTIAL** (no certificate docs)

Alternatively, click **"▶ Try Demo — LoanSight AI"** in the Compliance tab to pre-fill the wizard without running the script.

---

## SDK (Python)

The fastest way to integrate. Wraps any OpenAI-compatible client with one line:

```python
from openai import OpenAI
from pragma import Pragma, ComplianceError

client = Pragma(
    OpenAI(),
    policy_id="hr-compliance-v1",
    pragma_api_key="your-key",
    base_url="http://localhost:8000",
)

try:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Reject her — she is 58 years old."}]
    )
except ComplianceError as e:
    print(e.result.firewall_action)   # "block"
    print(e.result.risk_flags)        # ["bias", "discrimination", "fairness"]
    print(e.result.violations[0].regulation)  # "EEOC Title VII"
```

See [pragma-sdk/README.md](../pragma-sdk/README.md) for full SDK documentation.

---

## API Reference

All protected endpoints require a Bearer token from `/auth/guest` or `/auth/google`, or a `pragma_*` API key.

### Authentication

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/guest` | Create a guest session (no sign-in required) |
| POST | `/auth/google` | Sign in with a Google ID token |
| POST | `/logout` | Invalidate the current session |
| GET  | `/me` | Current user info |
| GET  | `/my-stats` | Aggregate usage stats (metadata only, no PII) |

### Compliance Firewall

**Single evaluation — `POST /evaluate-decision`**
```json
{
  "decision": "Reject job candidate",
  "context": { "gender": "female", "experience": 5, "role": "engineer" },
  "category": "hiring",
  "block_threshold": 0.8
}
```

Response:
```json
{
  "kantian_analysis": "...",
  "utilitarian_analysis": "...",
  "virtue_ethics_analysis": "...",
  "risk_flags": ["bias", "discrimination"],
  "confidence_score": 0.92,
  "recommendation": "Evaluate candidates on qualifications only.",
  "provider": "pragma",
  "firewall_action": "block",
  "should_block": true,
  "override_required": false,
  "regulatory_refs": [
    {
      "law": "EEOC Title VII (Civil Rights Act 1964)",
      "jurisdiction": "United States",
      "description": "Prohibits employment discrimination based on sex.",
      "url": "https://www.eeoc.gov/...",
      "triggered_by": "bias"
    }
  ]
}
```

**Firewall actions:**

| Action | Condition | Meaning |
|--------|-----------|---------|
| `block` | confidence ≥ threshold AND 2+ flags | Hard stop — do not proceed |
| `override_required` | 1+ flags, below block threshold | Human review required |
| `allow` | No significant risk | Proceed |

**Compliance-aware chat — `POST /chat`**

Conversational interface. Evaluates the message through the firewall before generating a response. Blocked messages return the compliance result with no AI response.

```json
{
  "message": "Should we reject the 58-year-old applicant?",
  "category": "hiring",
  "history": [],
  "block_threshold": 0.8
}
```

Response:
```json
{
  "user_message": "Should we reject the 58-year-old applicant?",
  "ai_response": null,
  "blocked": true,
  "firewall_action": "block",
  "risk_flags": ["bias", "fairness", "transparency"],
  "confidence_score": 0.9,
  "recommendation": "Evaluate candidates based on qualifications, not age.",
  "violations": [...]
}
```

**Batch evaluation — `POST /evaluate-batch`**

Upload a CSV (up to 100 rows) with columns: `decision`, `category`, plus any context columns. Returns a results CSV with analysis columns appended.

```bash
curl -X POST http://localhost:8000/evaluate-batch \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@decisions.csv"
```

**Counterfactual analysis — `POST /counterfactual`**

Runs two analyses — original vs. modified context — and diffs the results. Used to detect whether changing a protected attribute (gender, age, race) changes the outcome.

```json
{
  "decision": "Reject job application",
  "context": { "gender": "female", "experience": "5" },
  "category": "hiring",
  "changed_key": "gender",
  "changed_value": "male"
}
```

Response includes `diff.flags_added`, `diff.flags_removed`, `diff.confidence_delta`.

### Reports & Audit

**`POST /generate-report`** — Generate a downloadable PDF audit report from a completed analysis. Suitable for submission to regulators.

**`GET /questions?category=hiring`** — Guided context questions for a given category.

Categories: `hiring`, `workplace`, `finance`, `healthcare`, `policy`, `personal`, `other`

### Billing

| Method | Path | Description |
|--------|------|-------------|
| GET  | `/billing/subscription` | Current plan, eval usage, period end |
| POST | `/billing/create-checkout-session` | Start Stripe Checkout for Growth plan ($299/mo) |
| POST | `/billing/portal` | Open Stripe Customer Portal to manage subscription |
| POST | `/billing/webhook` | Stripe webhook receiver (signature-verified) |

Plans:

| Plan | Price | Evaluations/month |
|------|-------|-------------------|
| Free | $0 | 100 |
| Growth | $299/mo | 2,000 |
| Enterprise | Contact sales | Unlimited |

### Organizations

| Method | Path | Description |
|--------|------|-------------|
| POST | `/orgs` | Create an organization |
| POST | `/orgs/join` | Join via invite code |
| GET  | `/orgs` | List your organizations |
| GET  | `/orgs/{org_id}/history` | Shared decision history for the org |

### API Key Management

| Method | Path | Description |
|--------|------|-------------|
| POST   | `/api-keys` | Generate a new `pragma_*` API key |
| GET    | `/api-keys` | List keys with usage stats |
| DELETE | `/api-keys/{key_id}` | Revoke a key |

### Fintech Compliance

**Proxy Variable Guard** — built into `POST /evaluate-decision`. When the decision context includes fields that proxy for protected demographics under ECOA/Regulation B, the response includes a `proxy_variables_detected` list and the `bias`/`discrimination` risk flags are automatically raised.

Detected proxy fields:

| Field | Risk |
|-------|------|
| `zip_code` | Geographic redlining proxy |
| `last_name` | National origin / ethnicity proxy |
| `ip_country` | National origin proxy |
| `email_domain` | National origin / religion proxy |
| `device_language` | National origin proxy |
| `birth_date` / `age` | Age discrimination proxy |

Updated `POST /evaluate-decision` response (now includes audit and proxy fields):
```json
{
  "firewall_action": "block",
  "risk_flags": ["bias", "discrimination"],
  "confidence_score": 0.91,
  "regulatory_refs": [...],
  "audit_log_id": 42,
  "proxy_variables_detected": [
    {
      "field": "zip_code",
      "value": "90210",
      "risk": "Geographic redlining proxy for race/national origin",
      "regulation": "ECOA / Regulation B — 15 U.S.C. § 1691"
    }
  ]
}
```

**`POST /proxy-variable-report`** — Returns a structured report of all proxy variables found in a given context, with field, value, risk description, and ECOA/Regulation B citation.

```json
{ "context": { "zip_code": "60620", "last_name": "Garcia" } }
```

**Immutable Audit Trail**

Every call to `POST /evaluate-decision` writes one row to the `audit_log` table. The row stores the sha256 hash of the input (no raw PII), the firewall verdict, proxy variables detected, regulatory refs triggered, provider, and category.

| Method | Path | Description |
|--------|------|-------------|
| GET  | `/audit/log` | Last 50 audit entries for the current user |
| POST | `/audit/override` | Record a human investigator override (EU AI Act Art. 14) |

`POST /audit/override` request:
```json
{
  "audit_log_id": 42,
  "reason": "Reviewed by compliance officer — context cleared after manual review."
}
```

Response:
```json
{ "status": "override recorded", "audit_log_id": 42 }
```

### EU AI Act Data Lineage & Compliance Certificate

**Register an AI system — `POST /ai-systems`**
```json
{
  "system_name": "LoanScore v2",
  "company_name": "Acme Financial",
  "risk_tier": "high",
  "use_case": "Credit scoring for retail lending",
  "model_version": "2.1.0",
  "training_data_sources": ["internal-loan-history-2018-2023", "credit-bureau-feed"],
  "intended_purpose": "Automated credit risk assessment",
  "geographic_scope": "United States"
}
```

Response includes the assigned `system_id`.

**`GET /ai-systems`** — List all registered AI systems for the current user.

**`GET /ai-systems/{id}/compliance`** — Compute the full 15-article EU AI Act compliance checklist:

| Article | Check | Pass condition |
|---------|-------|----------------|
| Art. 4  | AI Literacy | `art4_literacy_training: true` declared |
| Art. 5  | Prohibited practices | No prohibited practices in use case or purpose |
| Art. 6  | High-risk classification | `art6_annex_category` declared (Annex III) |
| Art. 9  | Risk management | 10+ evaluations with risk flags recorded |
| Art. 10 | Data governance | `training_data_sources` declared (non-empty) |
| Art. 11 | Technical documentation | All profile fields completed |
| Art. 12 | Record-keeping | Audit trail active with at least 1 entry |
| Art. 13 | Transparency | Regulatory refs mapped in evaluations |
| Art. 14 | Human oversight | At least one HITL override recorded |
| Art. 15 | Accuracy & robustness | `art15_accuracy_metric` + `art15_robustness_tested: true` |
| Art. 17 | Quality management | `art17_qms_documented: true` |
| Art. 25 | Deployer obligations | `art25_instructions_provided` + `art25_monitoring_active` |
| Art. 27 | FRIA | `art27_fria_conducted: true` |
| Art. 30 | EU AI database | `art30_eu_db_registered` + `art30_registration_number` declared |
| Art. 33 | Conformity assessment | `art33_conformity_type` declared |

**Evidence-based scoring:** Declaration alone yields `partial`. A full `pass` requires the declaration field plus documentation notes and a dated entry in the audit trail. Articles without supporting evidence receive a **DECLARATION ONLY** badge on the certificate.

> **Note:** Art. 5 failure overrides the verdict to `prohibited` regardless of score — a prohibited system cannot receive a certificate.

Response:
```json
{
  "system_id": 7,
  "articles": {
    "art_4":  { "status": "pass",    "evidence": "AI literacy training confirmed by operator." },
    "art_5":  { "status": "pass",    "evidence": "No prohibited practices detected." },
    "art_6":  { "status": "pass",    "evidence": "High-risk classification confirmed. Annex III category: A.4 — Employment..." },
    "art_9":  { "status": "pass",    "evidence": "14 evaluations logged; risk flags detected: true" },
    "art_10": { "status": "pass",    "evidence": "2 training data source(s) declared" },
    "art_11": { "status": "pass",    "evidence": "6/6 fields completed" },
    "art_12": { "status": "pass",    "evidence": "14 audit log entries; proxy variables caught: 3" },
    "art_13": { "status": "partial", "evidence": "Regulatory references mapped: false; evaluations run: 14" },
    "art_14": { "status": "fail",    "evidence": "0 human override(s) recorded in audit trail" },
    "art_15": { "status": "pass",    "evidence": "Accuracy metric declared: F1=0.94; Robustness testing: confirmed" },
    "art_17": { "status": "pass",    "evidence": "Quality management system confirmed." },
    "art_25": { "status": "pass",    "evidence": "Instructions for use provided: yes; monitoring active: yes" },
    "art_27": { "status": "pass",    "evidence": "FRIA completed and documented." },
    "art_30": { "status": "pass",    "evidence": "Registered in EU AI database: yes; Registration number: EU-2024-001" },
    "art_33": { "status": "pass",    "evidence": "Self-assessment conformity assessment completed (Annex VI)" }
  },
  "overall_score": 0.87,
  "verdict": "partial"
}
```

Verdicts: `ready` (score ≥ 0.9), `partial` (0.6–0.9), `not_ready` (< 0.6), `prohibited` (Art. 5 fail).

**`POST /ai-systems/{id}/certificate`** — Generate a PDF compliance readiness certificate.

> Note: This is a readiness report, not a legal notified-body certification under the EU AI Act.

The PDF contains:
- Certificate ID (e.g. `PRAGMA-A3F9C2`)
- Issue date and valid-until date (1 year)
- Company name, system name, risk tier
- Per-article checklist with evidence (15 articles)
- Overall compliance score
- **SELF-ASSESSMENT ONLY** diagonal watermark across both pages
- **DECLARATION ONLY** badge on any article that lacks supporting documentation

The certificate record is stored in the `compliance_certificates` table and can be re-downloaded.

---

## Running Tests

```bash
pytest                                 # all tests with coverage
pytest tests/test_api.py -v            # API endpoint tests
pytest tests/test_regulations.py -v   # regulatory mapping
pytest tests/test_orgs_and_api_keys.py -v
```

Coverage: 87% across 382 tests.

---

## Project Structure

```
backend/
  main.py                   # FastAPI app — all endpoints, firewall logic, chat, Stripe billing, rate limiting
  database.py               # SQLAlchemy ORM — request logs, orgs, API keys, audit log, AI systems, certificates, subscriptions
  llm_orchestrator.py       # Pragma model → Claude → OpenAI fallback chain
  risk_detector.py          # Heuristic risk detection (bias, discrimination…) + proxy variable guard
  regulations.py            # Risk flag → regulatory reference mapping
  report_generator.py       # PDF audit report generation
  compliance_engine.py      # EU AI Act per-article compliance checklist computation (15 articles)
  compliance_certificate.py # PDF compliance readiness certificate generation (SELF-ASSESSMENT ONLY watermark)
  questions.py              # Category-specific guided context questions
  auth.py                   # Google OAuth + guest session management
  custom_model.py           # Fine-tuned Pragma compliance model interface

frontend/
  index.html           # Single-file SaaS dashboard (vanilla JS)
                       # Tabs: Evaluate, History, Batch, Chat, Audit Log (🔐), Compliance (🏛️), Settings
                       # Includes: XSS-safe esc() helper, Stripe billing card, 5-step assessment wizard,
                       # mobile bottom nav bar, "Try Demo — LoanSight AI" one-click demo button

mobile/
  App.tsx              # Tab navigator (Evaluate, History, Chat)
  src/screens/
    HomeScreen.tsx     # Decision evaluation with guided context
    ResultsScreen.tsx  # Compliance report with firewall verdict banner
    HistoryScreen.tsx  # Past decision metadata
    ChatScreen.tsx     # Compliance-aware conversational chatbot
    AuthScreen.tsx     # Landing with social proof + sign-in
  src/services/api.ts  # API client + TypeScript interfaces

pragma-sdk/            # Python SDK (separate package)
  pragma/
    client.py          # Pragma() and AsyncPragma() factory functions
    providers/openai.py # OpenAI/AzureOpenAI interceptors
    evaluator.py       # HTTP client for the Pragma backend
    types.py           # ComplianceResult, EvaluationRequest, PragmaConfig
    exceptions.py      # ComplianceError, PragmaAPIError, ConfigurationError

seed_demo.py           # CLI script — seeds LoanSight AI demo system into local DB
                       # Produces a realistic PASS/PARTIAL/FAIL compliance mix for demos

tests/
  conftest.py                    # Fixtures, isolated in-memory DB
  test_api.py                    # 78 endpoint tests
  test_regulations.py            # Regulatory mapping coverage
  test_orgs_and_api_keys.py      # Org and API key lifecycle
  test_fintech_compliance.py     # 18 tests: proxy variable guard, audit trail, HITL override
  test_compliance.py             # 45 tests: 15-article checklist, evidence-based scoring, prohibition detection, certificate PDF
```

---

## Mobile App

Built with Expo (React Native). Runs on iOS and Android from one codebase.

```bash
cd mobile
npm install
npx expo start
```

Scan the QR code with the Expo Go app. For physical device testing, update `mobile/src/config.ts` with your Mac's LAN IP address.

**Screens:**
- **Evaluate** — guided context form, runs compliance check, shows firewall verdict
- **Results** — full compliance report with risk flags, regulatory refs, firewall banner
- **History** — past decision metadata (no decision text stored)
- **Chat** — compliance-aware chatbot with scenario shortcuts and per-message firewall badges

---

## Deployment (Railway)

Connect the GitHub repo to Railway and it auto-deploys on every push to `main`.

1. Create project at [railway.app](https://railway.app) → Deploy from GitHub
2. Add a PostgreSQL plugin (Railway provisions the `DATABASE_URL` automatically)
3. Set environment variables in the Railway dashboard:

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude fallback LLM |
| `OPENAI_API_KEY` | Yes | GPT-4o-mini fallback |
| `GOOGLE_CLIENT_ID` | Yes | Google SSO verification |
| `DATABASE_URL` | Auto | Injected by Railway PostgreSQL plugin |
| `ALLOWED_ORIGINS` | Yes | Comma-separated allowed CORS origins (e.g. `https://yourdomain.com`) |
| `STRIPE_SECRET_KEY` | Billing | Stripe secret key (`sk_live_...`) |
| `STRIPE_WEBHOOK_SECRET` | Billing | Stripe webhook signing secret (`whsec_...`) |
| `STRIPE_GROWTH_PRICE_ID` | Billing | Price ID for the Growth plan (`price_...`) |
| `CUSTOM_MODEL_REPO` | Optional | HuggingFace repo for the Pragma model |
| `HF_TOKEN` | Optional | HuggingFace API token |

The SDK can point to the deployed instance via `base_url="https://your-railway-url"`.

---

## Security

| Control | Implementation |
|---------|---------------|
| XSS prevention | `esc()` helper using `document.createTextNode()` applied to all dynamic HTML in the frontend |
| CORS | Explicit allowlist via `ALLOWED_ORIGINS` env var — no wildcard origins |
| Input limits | Decision text ≤ 4,000 chars; context payload ≤ 8,000 chars |
| Batch rate limiting | Batch CSV endpoint checks monthly plan limit before processing |
| SQL injection | Column names in migration `ALTER TABLE` validated with `re.compile(r'^[a-z_][a-z0-9_]*$')` |
| Stripe webhooks | Signature verified with `stripe.WebhookSignature.verify_header()` before any processing |
| Structured logging | `logging.basicConfig` with timestamp/level/name format across `main.py`, `compliance_engine.py`, `database.py` |

---

## License

MIT
