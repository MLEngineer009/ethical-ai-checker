# Pragma — Ethical AI Decision Checker

An API-first system that evaluates decisions using ethical reasoning frameworks, detects bias and discrimination risks, maps findings to real regulations, and supports team collaboration and programmatic access via API keys.

## Quick Start

### 1. Setup Environment
```bash
python -m venv venv
source venv/bin/activate
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
```

### 4. Health Check
```bash
curl http://localhost:8000/health-check
```

---

## API Reference

All protected endpoints require a Bearer token obtained via `/auth/guest` or `/auth/google`, or a `pragma_*` API key.

### Authentication

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/guest` | Create a guest session (no sign-in required) |
| POST | `/auth/google` | Sign in with a Google ID token |
| POST | `/logout` | Invalidate the current session |
| GET  | `/me` | Get current user info |
| GET  | `/my-stats` | Aggregate usage stats and decision history (metadata only) |

### Decision Evaluation

**Single evaluation — `POST /evaluate-decision`**
```json
{
  "decision": "Reject job candidate",
  "context": { "gender": "female", "experience": 5, "role": "engineer" },
  "category": "hiring"
}
```

Response includes:
```json
{
  "kantian_analysis": "...",
  "utilitarian_analysis": "...",
  "virtue_ethics_analysis": "...",
  "risk_flags": ["bias", "discrimination"],
  "confidence_score": 0.92,
  "recommendation": "Remove gender from evaluation criteria.",
  "provider": "claude",
  "regulatory_refs": [
    {
      "law": "EEOC Title VII (Civil Rights Act 1964)",
      "jurisdiction": "US",
      "description": "Prohibits employment discrimination based on sex.",
      "url": "https://www.eeoc.gov/...",
      "triggered_by": "bias"
    }
  ]
}
```

**Batch evaluation — `POST /evaluate-batch`**

Upload a CSV (up to 100 rows) with columns: `decision`, `category`, plus any context columns. Returns a CSV with analysis columns appended (`risk_flags`, `confidence_score`, `recommendation`, `regulatory_refs`, `provider`, `error`).

```bash
curl -X POST http://localhost:8000/evaluate-batch \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@decisions.csv"
```

**Counterfactual analysis — `POST /counterfactual`**

Runs two analyses — original context vs. modified — and diffs the results. Useful for bias audits ("what changes if gender=male vs gender=female?").

```json
{
  "decision": "Reject job application",
  "context": { "gender": "female", "experience": "5" },
  "category": "hiring",
  "changed_key": "gender",
  "changed_value": "male"
}
```

Response:
```json
{
  "original": { ... },
  "modified": { ... },
  "changed_key": "gender",
  "original_value": "female",
  "modified_value": "male",
  "diff": {
    "flags_added": [],
    "flags_removed": ["bias"],
    "confidence_delta": -0.12
  }
}
```

### PDF Report

**`POST /generate-report`** — Generate a downloadable PDF from a completed analysis.

```json
{
  "decision": "...",
  "context": { ... },
  "analysis": { ... }
}
```

### Guided Context Questions

**`GET /questions?category=hiring`** — Returns the structured questions to help users supply relevant context for a given decision category.

Categories: `hiring`, `workplace`, `finance`, `healthcare`, `policy`, `personal`, `other`

### Team / Organizations

| Method | Path | Description |
|--------|------|-------------|
| POST | `/orgs` | Create an organization (caller becomes owner) |
| POST | `/orgs/join` | Join an org using an invite code |
| GET  | `/orgs` | List your organizations |
| GET  | `/orgs/{org_id}/history` | Shared decision history for all org members |

### API Key Management

API keys (`pragma_*` prefix) allow programmatic access without a browser session.

| Method | Path | Description |
|--------|------|-------------|
| POST   | `/api-keys` | Generate a new API key (raw key shown once) |
| GET    | `/api-keys` | List your keys with usage stats |
| DELETE | `/api-keys/{key_id}` | Revoke a key |

**Using an API key:**
```bash
curl http://localhost:8000/evaluate-decision \
  -H "Authorization: Bearer pragma_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{"decision": "...", "context": {"role": "engineer"}, "category": "hiring"}'
```

---

## Running Tests

```bash
pytest                        # run all tests with coverage
pytest tests/test_api.py -v   # API endpoint tests only
pytest tests/test_regulations.py -v  # regulatory mapping tests
```

Coverage reports are generated in `docs/coverage/` (HTML) and printed to terminal. The target is 80%+.

---

## Project Structure

```
backend/
  main.py              # FastAPI app — all endpoints and request models
  database.py          # SQLite/PostgreSQL ORM — request logs, orgs, API keys
  llm_orchestrator.py  # LLM integration with Pragma → Claude → OpenAI fallback
  risk_detector.py     # Heuristic risk detection (bias, discrimination, fairness…)
  regulations.py       # (category, risk_flag) → regulatory references (EEOC, GDPR…)
  report_generator.py  # PDF report generation via reportlab
  questions.py         # Category-specific guided context questions
  auth.py              # Google OAuth + guest session management
  prompts.py           # LLM prompt templates
  config.py            # Environment configuration
frontend/
  index.html           # Single-page web UI
mobile/
  App.tsx              # Expo React Native app (iOS + Android)
tests/                 # pytest test suite (~80% coverage)
```

---

## Mobile App

The iOS/Android app is built with Expo (SDK 54). To run:

```bash
cd mobile
npm install
npx expo start
```

Scan the QR code with the Expo Go app. Update `mobile/src/config.ts` with your Mac's LAN IP for physical device testing.

---

## Deployment (GCP Cloud Run)

```bash
gcloud run deploy pragma-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --set-env-vars ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY,OPENAI_API_KEY=$OPENAI_API_KEY,GOOGLE_CLIENT_ID=$GOOGLE_CLIENT_ID
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for full instructions including custom domain and secrets management.

---

## License

MIT
