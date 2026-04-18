# Pragma — Project Summary

**Positioning:** AI compliance firewall — block risky AI decisions before they become lawsuits.

---

## ✅ What's Built

### 1. AI Decision Firewall (Core Product)
- `POST /evaluate-decision` — evaluates a decision through three ethical frameworks + heuristic risk detection
- **Firewall verdict** on every response: `should_block`, `override_required`, `firewall_action` (`"block"` / `"override_required"` / `"allow"`)
- Configurable `block_threshold` (default 0.8) — enterprise customers can tune sensitivity
- Firewall logic: confidence ≥ threshold AND 2+ risk flags → block; any flag below threshold → override required

### 2. Multi-Framework Ethical Reasoning
- **Kantian Ethics** — universality and duty-based analysis
- **Utilitarian** — net benefit vs. harm across all stakeholders
- **Virtue Ethics** — character and integrity reflection
- All three evaluated independently by LLM, then combined into a single structured response

### 3. Risk Detection System (`backend/risk_detector.py`)
- `detect_bias_risks` — 15+ sensitive attributes (gender, race, age, zip code, religion, disability…)
- `detect_fairness_risks` — exclusionary keywords and group-based language
- `detect_discrimination_risks` — regex patterns for "based on X" constructs
- `detect_transparency_risks` — vague reasoning when context is sparse
- `detect_all_risks` — aggregates all four, returns sorted unique flags
- Heuristic flags merged with LLM-detected flags for maximum coverage

### 4. Regulatory Reference Mapping (`backend/regulations.py`)
- 18 laws defined: EEOC Title VII, ADA, ADEA, Equal Pay Act, NLRA, ECOA, Fair Housing Act, FCRA, CFPB UDAAP, HIPAA, ACA §1557, GDPR, GDPR Art.22, EU AI Act, EU Equal Treatment Directive, EO 14110, FTC AI Guidance, CCPA
- `(category, risk_flag)` → list of triggered laws with name, jurisdiction, description, and official URL
- Deduplicated per response — no duplicate laws even if multiple flags trigger the same law
- Returned as `regulatory_refs[]` in every evaluation response

### 5. Batch Evaluation (`POST /evaluate-batch`)
- Upload CSV up to 100 rows — columns: `decision`, `category`, plus any context columns
- Returns CSV with analysis columns appended: `risk_flags`, `confidence_score`, `recommendation`, `regulatory_refs`, `provider`, `error`
- Rows with missing decisions get an `error` column instead of failing the whole batch

### 6. Counterfactual Analysis (`POST /counterfactual`)
- Runs two analyses — original context vs. modified — and diffs the results
- Returns `diff.flags_added`, `diff.flags_removed`, `diff.confidence_delta`
- Primary use case: bias audits ("what changes if gender=male vs gender=female?")

### 7. PDF Audit Reports (`POST /generate-report`)
- Generates downloadable PDF from any completed analysis
- Includes all three framework analyses, risk flags, confidence score, regulatory references, and recommendation
- "Audit-ready evidence" — formatted for compliance and legal teams

### 8. Guided Context Questions (`GET /questions?category=`)
- Category-specific structured questions (hiring, workplace, finance, healthcare, policy, personal, other)
- Types: `text`, `select`, `multiselect`, `toggle`
- Used by both web UI and mobile app to guide users through relevant context

### 9. Authentication
- **Google SSO** — ID token verified server-side, creates persistent session
- **Guest sessions** — in-memory, no sign-up required; all features available for testing
- **API keys** — `pragma_*` prefix, SHA-256 hashed, usage metering (calls_total, calls_month)
- API key holders cannot create new keys (prevents proliferation)

### 10. Team / Organization Accounts
- `POST /orgs` — create organization, caller becomes owner, invite code generated
- `POST /orgs/join` — join via invite code
- `GET /orgs/{org_id}/history` — shared decision metadata history for all org members (no PII)

### 11. Database (`backend/database.py`)
- SQLite (dev/test) / PostgreSQL (production via `DATABASE_URL` env var)
- Tables: `request_logs`, `analysis_feedback`, `waitlist`, `organizations`, `org_members`, `api_keys`
- Privacy: decision text never stored — only word count, context keys (not values), provider, confidence, risk categories
- `anon_id()` — HMAC-based irreversible anonymisation of user sub

### 12. LLM Orchestration (`backend/llm_orchestrator.py`)
- Fallback chain: **Pragma (custom model)** → **Anthropic Claude** → **OpenAI GPT-4**
- Works offline/in tests via mock responses
- Structured JSON output parsing with validation

---

## 📱 Mobile App (Expo React Native — iOS & Android)

- **AuthScreen** — landing screen with full social proof (lawsuit stats, real cases, regulatory deadlines)
- **HomeScreen** — category selector, guided questions fetched from API, decision input
- **ResultsScreen** — firewall verdict banner (🚫/⚠️/✅), framework accordions, risk chips, confidence bar, regulatory refs, counterfactual panel, PDF download
- **HistoryScreen** — decision metadata timeline (no text stored)
- Custom bottom tab bar (Evaluate | History)
- Expo SDK 54, tested on iOS via Expo Go

---

## 🌐 Web Frontend (`frontend/index.html`)

- **Landing page** — firewall positioning, real lawsuit stats ($365K EEOC settlement, €35M EU AI Act), case studies (iTutorGroup, Workday, Amazon), regulatory deadline tracker
- **Evaluate tab** — category pills, guided questions, firewall verdict banner on results
- **History tab** — metadata timeline
- **Batch tab** — CSV drag-and-drop upload, results download
- **Settings tab** — org creation/join, API key generation/revocation

---

## 🧪 Testing

- **314 tests passing** across 9 test files — **93.7% backend coverage**
- `tests/test_api.py` — 78 endpoint integration tests (auth, evaluate, batch, counterfactual, orgs, API keys, PDF, feedback)
- `tests/test_regulations.py` — 21 tests for regulatory mapping (all categories, deduplication, edge cases)
- `tests/test_orgs_and_api_keys.py` — 42 tests for org lifecycle and API key create/verify/revoke
- `tests/test_database.py` — request logging, stats, feedback, anonymisation
- `tests/test_risk_detector.py` — all 5 detectors across edge cases
- `tests/test_llm_orchestrator.py` — parsing, normalization, fallback chain
- `tests/test_report_generator.py`, `test_auth.py`, `test_response_formatter.py`, `test_config.py`
- `conftest.py` uses `StaticPool` in-memory SQLite — all connections share one DB per test, no stale state

---

## 📁 Project Structure

```
backend/
  main.py              # FastAPI app — 28 endpoints, firewall logic, batch, counterfactual
  database.py          # ORM — request logs, orgs, API keys, feedback (SQLite/PostgreSQL)
  llm_orchestrator.py  # Pragma → Claude → OpenAI fallback chain
  risk_detector.py     # 5 heuristic risk detectors
  regulations.py       # (category, flag) → regulatory references
  report_generator.py  # PDF generation (reportlab)
  questions.py         # Guided context questions by category
  auth.py              # Google OAuth + guest sessions
  prompts.py           # LLM prompt templates
  config.py            # Environment configuration
frontend/
  index.html           # Single-page web UI (2,000+ lines)
mobile/
  App.tsx              # Navigator + custom tab bar
  src/screens/
    AuthScreen.tsx     # Landing + social proof + auth
    HomeScreen.tsx     # Guided evaluation form
    ResultsScreen.tsx  # Firewall banner + full analysis display
    HistoryScreen.tsx  # Decision metadata history
  src/services/api.ts  # Typed API client
  src/context/AuthContext.tsx
tests/                 # 314 tests, 93.7% coverage
```

---

## 🔌 API Quick Reference

```bash
# Evaluate a decision (returns firewall verdict)
curl -X POST /evaluate-decision \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"decision":"Reject candidate","context":{"gender":"female","role":"engineer"},"category":"hiring"}'

# Response includes:
# "firewall_action": "block" | "override_required" | "allow"
# "should_block": true/false
# "regulatory_refs": [{"law":"EEOC Title VII",...}]

# Batch evaluate
curl -X POST /evaluate-batch -H "Authorization: Bearer $TOKEN" -F "file=@decisions.csv"

# Counterfactual bias audit
curl -X POST /counterfactual \
  -d '{"decision":"...","context":{...},"changed_key":"gender","changed_value":"male"}'

# Generate PDF report
curl -X POST /generate-report -d '{"decision":"...","context":{...},"analysis":{...}}'
```

---

## 🚀 Running Locally

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload   # API at http://localhost:8000

# Mobile
cd mobile && npm install && npx expo start

# Tests
pytest                              # Full suite with coverage
```

---

## 🎯 Key Design Decisions

1. **Firewall positioning** — `firewall_action` is the first thing in every response; product is operational not advisory
2. **Regulatory refs built-in** — no separate compliance lookup needed; every flag maps to specific laws
3. **Privacy by design** — decision text never persisted; only metadata (word count, context keys, risk categories)
4. **Guest = full access** — all features available without sign-up for testing and sales demos
5. **API-key tier** — enables programmatic/enterprise use without browser sessions
6. **StaticPool in tests** — single in-memory SQLite connection per test; no cross-connection data loss

---

## 📈 Regulatory Deadlines (selling urgency)

| Regulation | Status | Penalty |
|------------|--------|---------|
| NYC Local Law 144 | In force July 2023 | $1,500/day |
| GDPR Article 22 | In force | 4% global revenue |
| EU AI Act (high-risk) | August 2026 deadline | €35M or 7% of global revenue |

**Real cases:** EEOC v. iTutorGroup ($365K settlement, 2023) · Mobley v. Workday (class certified, 2025) · Amazon AI hiring tool (scrapped after bias discovered, 2018)

---

**Status: In-market testing ready. 314 tests passing. 93.7% coverage.** 🚀
