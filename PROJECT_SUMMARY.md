# Pragma — Project Summary

AI compliance firewall. Intercepts AI decisions, evaluates them against regulatory policy, blocks violations before they execute, and generates audit-ready evidence. Available as a web dashboard, iOS/Android mobile app, and Python SDK.

---

## What's Built

### 1. AI Decision Firewall (Core Engine)
Every evaluation returns a structured firewall verdict:
- `firewall_action`: `"block"` | `"override_required"` | `"allow"`
- `should_block`: boolean — confidence ≥ threshold AND 2+ risk flags
- `confidence_score`: 0–1 float from the compliance model
- `risk_flags`: list of detected risks (bias, discrimination, fairness, transparency…)
- `regulatory_refs`: regulations triggered, with jurisdiction and citation URL

### 2. Multi-Framework Ethical Reasoning
Every decision is analyzed across three frameworks simultaneously:
- **Kantian** — duty-based, treats people as ends not means
- **Utilitarian** — greatest good, assesses aggregate harm
- **Virtue Ethics** — character and integrity assessment

### 3. Compliance-Aware Chat (`POST /chat`)
Conversational chatbot where every message is evaluated by the firewall before a response is generated. Blocked messages return the compliance result and regulations triggered — no AI response. Allowed messages return a contextual answer. Includes demo scenarios for hiring and lending decisions.

### 4. Risk Detection (`backend/risk_detector.py`)
Heuristic pattern matching across 8 risk categories:
`bias`, `discrimination`, `privacy`, `transparency`, `fairness`, `autonomy`, `harm`, `manipulation`

Combined with LLM-based analysis for nuanced cases. Heuristic flags are the authoritative blocking signal for the chat endpoint.

### 5. Regulatory Reference Mapping (`backend/regulations.py`)
Maps (category, risk_flag) pairs to specific regulations with citations:
- EU AI Act (August 2026 enforcement deadline)
- EEOC Title VII / Age Discrimination in Employment Act
- GDPR Article 22 (automated decision-making)
- NYC Local Law 144 ($1,500/day fine)
- CFPB Equal Credit Opportunity Act
- NIST AI Risk Management Framework
- FTC AI Guidance / Executive Order 14110

### 6. Batch Evaluation (`POST /evaluate-batch`)
CSV upload, up to 100 rows. Returns results CSV with analysis columns appended.

### 7. Counterfactual Analysis (`POST /counterfactual`)
Detects whether changing a protected attribute (gender, age, race) changes the compliance verdict. Returns `flags_added`, `flags_removed`, `confidence_delta`.

### 8. PDF Audit Reports (`POST /generate-report`)
One-click PDF generation from any completed analysis. Suitable for regulatory submission.

### 9. Guided Context Questions (`GET /questions`)
Category-specific structured questions for `hiring`, `workplace`, `finance`, `healthcare`, `policy`, `personal`, `other`.

### 10. Authentication
Google OAuth, guest sessions (full feature access, no sign-up), JWT session tokens.

### 11. Organizations & Team Accounts
Create workspaces, generate invite codes, join orgs, shared decision history.

### 12. API Key Management
Generate `pragma_*` API keys, track usage, revoke individually.

### 13. LLM Orchestration (`backend/llm_orchestrator.py`)
Fallback chain: Custom Pragma model → Claude (extended thinking) → GPT-4o → heuristic mock.

---

## Python SDK (`pragma-sdk/`)

Separate installable package. One-line integration:

```python
client = Pragma(OpenAI(), policy_id="hr-v1", pragma_api_key="...")
# Every client.chat.completions.create() call is now firewall-enforced
```

- Sync (`Pragma`) and async (`AsyncPragma`) clients
- Modes: `block` (raise `ComplianceError`), `flag` (attach `.pragma_result`), `audit`
- Configurable `block_threshold` per instance
- Supports OpenAI, AsyncOpenAI, AzureOpenAI, AsyncAzureOpenAI
- Live end-to-end tested

---

## Web Dashboard (`frontend/index.html`)

Single-file SaaS dashboard. Served directly from FastAPI.

**Tabs:**
- **Evaluate** — guided context, firewall verdict, regulatory refs, PDF download
- **History** — past decision metadata
- **Batch** — CSV drag-and-drop, results download
- **Chat** — compliance chatbot, 4 demo scenarios, per-message firewall badges
- **Settings** — org management, API key management

**Landing page:** Real lawsuit data (iTutorGroup $365K, Workday class action), regulatory deadline tracker (NYC LL144, GDPR, EU AI Act Aug 2026).

---

## Mobile App (`mobile/`)

Expo React Native — iOS and Android.

**Screens:** Auth (social proof + sign-in), Home (evaluate), Results (firewall verdict banner), History, Chat (compliance chatbot with scenario shortcuts).

---

## Testing

**Coverage: 93.7%** across 141 tests (78 API, 21 regulatory mapping, 42 org/API key).
StaticPool-isolated in-memory SQLite per test for full isolation.

---

## API Quick Reference

```bash
# Guest session
curl -X POST http://localhost:8000/auth/guest

# Evaluate
curl -X POST http://localhost:8000/evaluate-decision \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"decision":"...","context":{"role":"engineer"},"category":"hiring"}'

# Chat
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"message":"Should we reject the 58-year-old?","category":"hiring"}'

# Batch
curl -X POST http://localhost:8000/evaluate-batch \
  -H "Authorization: Bearer $TOKEN" -F "file=@decisions.csv"

# Counterfactual
curl -X POST http://localhost:8000/counterfactual \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"decision":"...","context":{...},"changed_key":"gender","changed_value":"male"}'
```

---

## Running Locally

```bash
# Backend + web
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload   # → http://localhost:8000

# Mobile
cd mobile && npm install && npx expo start

# SDK
cd pragma-sdk && pip install -e ".[dev]" && python test_live.py

# Tests
pytest --cov=backend --cov-report=term-missing
```
