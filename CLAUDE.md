# Pragma — CLAUDE.md

AI compliance firewall for automated decisions. Intercepts AI decisions before they execute, checks them against 40+ regulations deterministically (no LLM required for the check itself), and generates audit-ready evidence.

**Production:** https://www.usepragma.co  
**Repo:** github.com/MLEngineer009/ethical-ai-checker  
**Company:** Cosmos AI LLC  
**Deploy:** Railway — auto-deploys on push to `main`  

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + SQLAlchemy + PostgreSQL (Railway plugin) |
| Frontend | Single-file SPA (`frontend/index.html`) served by FastAPI |
| LLM | Anthropic Claude (primary) → OpenAI (fallback) via `LLMOrchestrator` |
| Auth | Google OAuth + guest sessions + JWT |
| Notifications | Resend API (daily Railway cron at 09:00 UTC) |
| PDF | ReportLab |
| Payments | Stripe |
| Error tracking | Sentry |

---

## Project Layout

```
backend/
  main.py               — FastAPI app, all routes, demo scenarios
  compliance_engine.py  — Two-layer deterministic checker (generic + sector)
  llm_orchestrator.py   — Claude/OpenAI wrapper; orchestrator.evaluate() is the LLM call
  risk_detector.py      — Heuristic pattern matching, proxy variable detection
  database.py           — SQLAlchemy models + all DB helpers
  auth.py               — JWT, guest sessions, Google OAuth
  regulations.py        — (category, risk_flag) → regulation citations
  compliance_certificate.py — EU AI Act PDF certificate generation
  report_generator.py   — General PDF audit reports
  evidence_analyzer.py  — Claude-based document evidence extraction
  interview_engine.py   — Guided interview for EU AI Act article evidence
  notifications.py      — Email lifecycle (welcome, gap reminder, countdown)
  semantic_layer.py     — sentence-transformers proxy detection (optional dep)
  geo_data.py           — HOLC redlining zip code data for ECOA checks

frontend/
  index.html            — Main SPA dashboard (all tabs)
  marketing.html        — Public marketing landing page (/marketing route)
  cosmos.html           — Cosmos AI LLC company page (/cosmos route)
  hiring.html / lending.html / auditing.html / business.html — static pages

tests/
  conftest.py           — Shared fixtures: isolated in-memory SQLite per test
  test_api.py           — Core API endpoint tests
  test_compliance.py    — Compliance engine tests
  test_hiring_compliance.py — Hiring-specific checker tests
  test_demo_scenarios.py — Demo scenario endpoint + compliance engine sector tests
  test_fintech_compliance.py — ECOA/FCRA proxy variable tests
  test_regulations.py   — Regulation mapping tests
  (+ 10 more test files)

pragma-sdk/             — Installable Python SDK (OpenAI wrapper)
mobile/                 — Expo React Native app (iOS + Android)
send_notifications.py   — Standalone Railway cron script
```

---

## Compliance Engine Architecture

**Two-layer design** (`backend/compliance_engine.py`):

```
_GENERIC_CHECKERS          — runs for EVERY sector
  EU AI Act Art. 13/14
  GDPR Art. 22
  Text scanner
  Compound proxy detection
  Disparate impact (generic)
  State AI laws (CO, CA, NYC, IL)

+ sector-specific:

hiring    → EEOC, FCRA pre-adverse action, ban-the-box, EU AI Act §4, 4/5ths rule
workplace → EEOC, EU AI Act §4, 4/5ths rule  (NO ban-the-box / FCRA pre-adverse)
finance   → ECOA, FCRA, FHA, UDAAP, adverse action notices
lending   → same as finance (alias)
healthcare → placeholder (HIPAA/CMS planned)
other     → generic only
```

**Key rule:** `hiring` and `workplace` are separate. Ban-the-box and FCRA pre-adverse action apply to job applications only — never to promotions, terminations, or performance reviews.

**Mock LLM in tests:** patch `backend.main.orchestrator.evaluate`, not `_run_evaluation`.

---

## Valid Categories

```python
VALID_CATEGORIES = {"hiring", "finance", "healthcare", "workplace", "policy", "personal", "other"}
```

Anything outside this set falls back to `"other"`.

---

## Key API Endpoints

```
POST /evaluate-decision     — main firewall evaluation
POST /evaluate-batch        — CSV batch (up to 100 rows)
POST /chat                  — compliance chatbot
POST /counterfactual        — protected attribute swap analysis
POST /demo/gemini-chat      — live Gemini scenarios (GC-* lending, GH-* hiring)
POST /audit/override        — HITL override for EU AI Act Art. 14
GET  /audit/log             — last 50 audit entries
POST /ai-systems            — register an AI system
GET  /ai-systems/{id}/compliance — EU AI Act article checklist
POST /ai-systems/{id}/certificate — generate PDF compliance certificate
POST /evidence/extract      — AI document evidence extraction
POST /evidence/interview    — guided article interview
GET  /health-check          — Railway healthcheck
GET  /marketing             — marketing landing page
GET  /cosmos                — company page
```

---

## Demo Scenarios

Defined in `backend/main.py` as module-level dicts:

- `_GEMINI_SCENARIOS` — GC-001 to GC-006 (lending, finance category)
- `_GEMINI_HIRING_SCENARIOS` — GH-001 to GH-006 (hiring category)

Frontend demo use case keys: `bnpl` (Affirm, 8 scenarios), `hiring` (Workday, 6 scenarios), `gemini` (live lending AI), `gemini-hiring` (live hiring AI).

**Marketing page deep-links:**
- `/?demo=1&uc=hiring` → auto guest login + open demo tab on Workday scenarios
- `/?demo=1&uc=bnpl` → Affirm BNPL scenarios
- `/?demo=1&uc=gemini-hiring` → live Gemini hiring scenarios

---

## Running Locally

```bash
# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload   # → http://localhost:8000

# Tests (requires 80% coverage)
pytest --no-cov         # skip coverage for speed
pytest                  # full run with coverage

# Mobile
cd mobile && npm install && npx expo start

# SDK
cd pragma-sdk && pip install -e ".[dev]" && python test_live.py
```

---

## Environment Variables (Railway)

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Auto-set by Railway PostgreSQL plugin |
| `ANTHROPIC_API_KEY` | Claude (primary LLM) |
| `OPENAI_API_KEY` | OpenAI (fallback LLM) |
| `GOOGLE_CLIENT_ID` | Google OAuth |
| `RESEND_API_KEY` | Email notifications |
| `EMAIL_FROM` | e.g. `Pragma <notifications@usepragma.co>` |
| `APP_URL` | Production URL |
| `GEMINI_API_KEY` | Live Gemini demo scenarios |
| `STRIPE_SECRET_KEY` | Payments |
| `SENTRY_DSN` | Error tracking |

---

## Design System

The main app and marketing page share the same visual language:

```css
--bg:          #0a0b0f   /* near-black background */
--surface:     #111318   /* card surface */
--border:      #1e2232   /* card border */
--accent:      #6366f1   /* indigo */
--accent2:     #818cf8   /* lighter indigo */
--text:        rgba(255,255,255,0.92)
--text-muted:  rgba(255,255,255,0.45)
```

Font: **Inter** (headings weight 700–800, letter-spacing -0.5px to -1.2px), **IBM Plex Mono** for code/regulation chips.

Logo: `🛡️ Pragma` with `by Cosmos AI LLC` sub-label.

---

## Testing Notes

- `conftest.py` gives every test its own isolated in-memory SQLite — no shared state between tests
- Coverage threshold: 80% (`--cov-fail-under=80` in pytest.ini) — use `--no-cov` to skip during dev
- `google.genai` is a local import inside `gemini_chat_demo()` — mock via `sys.modules` patching, not `patch("google.genai.Client")`
- The `ANTHROPIC_API_KEY` env var is stubbed to `""` in conftest.py so tests never hit the real API

---

## Deployment Flow

1. Push to `main` on GitHub
2. Railway auto-detects the push and redeploys (Nixpacks builder)
3. Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. Healthcheck: `GET /health-check`
5. Daily cron: `python send_notifications.py` at 09:00 UTC
