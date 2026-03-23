# Copilot Instructions for Ethical AI Decision Checker

## System Overview

Building an **API-first ethical decision evaluation system** using LLM-powered reasoning frameworks. The system evaluates decisions against three ethical frameworks (Kantian, Utilitarian, Virtue Ethics), detects risks, and provides recommendations.

**Target Users**: HR Tech, Fintech, Enterprise AI governance teams

## Architecture Pattern

```
Frontend (React/HTML)
    ↓
FastAPI Backend (/api/evaluate-decision)
    ↓
LLM Layer (OpenAI/Claude)
    ↓
Structured Response Formatter
```

The API is the primary interface—UI is secondary. Always prioritize API contract first.

## Core API Contract

**Endpoint**: `POST /evaluate-decision`

**Request**:
```json
{
  "decision": "Reject job candidate",
  "context": {
    "experience": 5,
    "education": "non-elite",
    "gender": "female"
  }
}
```

**Response** (always this structure):
```json
{
  "kantian_analysis": "string",
  "utilitarian_analysis": "string",
  "virtue_ethics_analysis": "string",
  "risk_flags": ["bias", "fairness"],
  "confidence_score": 0.0-1.0,
  "recommendation": "string"
}
```

## Critical Conventions

### 1. Ethical Framework Implementation
Each framework must evaluate independently, then combine findings. Don't merge them early.
- **Kantian**: universality + fairness questions
- **Utilitarian**: majority benefit + harm minimization
- **Virtue Ethics**: character + integrity reflection

### 2. Risk Detection Heuristics
Flag risks based on:
- Presence of sensitive attributes (gender, race, zip code) → "bias"
- Disproportionate group impact → "fairness"
- Unclear reasoning → "transparency"
- Exclusionary patterns → "discrimination"

### 3. LLM Integration
Use a **system prompt** that defines the three frameworks upfront. Keep user prompts structured: `Decision: {{decision}}\nContext: {{context}}`

Example system prompt in `backend/prompts.py`:
```python
SYSTEM_PROMPT = """You are an ethical reasoning engine.
Evaluate decisions using three frameworks:
1. Kantian ethics (fairness, universality, duty)
2. Utilitarianism (maximizing overall good)
3. Virtue ethics (character and integrity)

Return structured analysis per framework, risk flags, and actionable recommendations."""
```

### 4. Response Formatting
Always validate LLM output conforms to the response schema before returning. Parse structured output from LLM (JSON or delimited text).

## Development Workflow

**Backend Setup**:
- `python -m venv venv && source venv/bin/activate`
- `pip install fastapi uvicorn openai`
- `uvicorn main:app --reload`

**Testing Sample**:
Use provided use cases (hiring, loan approval) as integration test scenarios. Test with biased inputs to verify risk detection works.

**Deployment**:
- Target: Google Cloud Platform (GCP)
- Cloud Run for serverless FastAPI backend
- Cloud Tasks for async processing if needed
- API Gateway + API key authentication
- Consider rate limiting for enterprise SLA

## Naming Conventions

**Python modules**: `snake_case` (e.g., `risk_detector.py`, `prompt_manager.py`)
**Classes**: `PascalCase` (e.g., `RiskDetector`, `EthicalAnalyzer`)
**Functions/methods**: `snake_case` (e.g., `evaluate_decision()`, `detect_bias_risks()`)
**Constants**: `UPPER_SNAKE_CASE` (e.g., `SYSTEM_PROMPT`, `BIAS_KEYWORDS`)
**API routes**: kebab-case (e.g., `/evaluate-decision`, `/health-check`)

## Key Files (when created)

- `backend/main.py` - FastAPI app + `/evaluate-decision` endpoint
- `backend/prompts.py` - System & user prompt templates
- `backend/risk_detector.py` - Heuristic risk flagging logic
- `frontend/` - React or simple HTML form (non-critical for MVP)
- `tests/test_api.py` - Integration tests with sample scenarios

## Quick Start for New Developers

1. Review `instructions.md` for full spec context
2. Implement `/evaluate-decision` endpoint first
3. Integrate LLM with structured prompting
4. Add risk detection heuristics
5. Test with hiring + loan rejection scenarios
6. Deploy with API key auth

## Non-Goals (Don't Build)
- Custom model training
- Complex ethical ontology
- Full GDPR/EEOC compliance automation
- Audit logging (future enhancement)

## Success Metrics
- API returns consistent, valid structured output
- Detects obvious bias cases (e.g., gender in candidate rejection)
- Recommendations are actionable and specific
- Demo-ready for enterprise clients
