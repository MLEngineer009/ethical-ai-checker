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
export ANTHROPIC_API_KEY=your_anthropic_key   # primary LLM
export OPENAI_API_KEY=your_openai_key         # fallback LLM
export GOOGLE_CLIENT_ID=your_google_client_id # for Google Sign-In
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

---

## Running Tests

```bash
pytest                                 # all tests with coverage
pytest tests/test_api.py -v            # API endpoint tests
pytest tests/test_regulations.py -v   # regulatory mapping
pytest tests/test_orgs_and_api_keys.py -v
```

Coverage: 93.7% across 78 tests.

---

## Project Structure

```
backend/
  main.py              # FastAPI app — all endpoints, firewall logic, chat
  database.py          # SQLAlchemy ORM — request logs, orgs, API keys
  llm_orchestrator.py  # Pragma model → Claude → OpenAI fallback chain
  risk_detector.py     # Heuristic risk detection (bias, discrimination…)
  regulations.py       # Risk flag → regulatory reference mapping
  report_generator.py  # PDF audit report generation
  questions.py         # Category-specific guided context questions
  auth.py              # Google OAuth + guest session management
  custom_model.py      # Fine-tuned Pragma compliance model interface

frontend/
  index.html           # Single-file SaaS dashboard (vanilla JS)
                       # Tabs: Evaluate, History, Batch, Chat, Settings

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

tests/
  conftest.py                 # Fixtures, isolated in-memory DB
  test_api.py                 # 78 endpoint tests
  test_regulations.py         # Regulatory mapping coverage
  test_orgs_and_api_keys.py   # Org and API key lifecycle
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

## Deployment (GCP Cloud Run)

```bash
gcloud run deploy pragma-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --set-env-vars ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY,OPENAI_API_KEY=$OPENAI_API_KEY,GOOGLE_CLIENT_ID=$GOOGLE_CLIENT_ID
```

The SDK can point to the deployed instance via `base_url="https://your-cloud-run-url"`.

---

## License

MIT
