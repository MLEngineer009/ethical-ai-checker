# Getting Started Guide

## Quick Start (5 minutes)

### 1. Clone & Setup

```bash
cd /Users/chakpotluri/Desktop/StartupIdea

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Key

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your OpenAI API key
export OPENAI_API_KEY=sk-your-actual-key-here
```

### 3. Run Backend Server

```bash
cd StartupIdea
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Server running on `http://localhost:8000`

### 4. Test API

**Health Check:**
```bash
curl http://localhost:8000/health-check
```

**Evaluate Decision:**
```bash
curl -X POST http://localhost:8000/evaluate-decision \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "Reject job candidate",
    "context": {
      "experience": 5,
      "gender": "female",
      "education": "non-elite"
    }
  }'
```

**Sample Response:**
```json
{
  "kantian_analysis": "This decision violates the principle of fairness...",
  "utilitarian_analysis": "Rejecting based on gender reduces overall benefit...",
  "virtue_ethics_analysis": "This lacks integrity and fairness...",
  "risk_flags": ["bias", "fairness"],
  "confidence_score": 0.92,
  "recommendation": "Remove gender from evaluation criteria"
}
```

### 5. Run Tests

```bash
pytest tests/test_api.py -v
```

## Core Concepts

### Ethical Frameworks

1. **Kantian Ethics**: Evaluates fairness and universality
   - *Key question*: "Can this decision be applied equally to everyone?"

2. **Utilitarianism**: Maximizes overall good
   - *Key question*: "Does this decision benefit the most people?"

3. **Virtue Ethics**: Reflects character and integrity
   - *Key question*: "Does this reflect good character?"

### Risk Detection

The system flags:
- **bias**: Sensitive attributes (gender, race, age, etc.) present in context
- **fairness**: Disproportionate group impact or exclusionary reasoning
- **discrimination**: Explicit group-based decision criteria
- **transparency**: Unclear reasoning or insufficient context

## API Reference

### POST /evaluate-decision

Evaluate a decision through ethical reasoning frameworks.

**Request:**
```json
{
  "decision": "string (required)",
  "context": {
    "key": "value",
    "...": "..."
  }
}
```

**Response:**
```json
{
  "kantian_analysis": "string",
  "utilitarian_analysis": "string",
  "virtue_ethics_analysis": "string",
  "risk_flags": ["string"],
  "confidence_score": 0.0-1.0,
  "recommendation": "string"
}
```

**Error Response:**
```json
{
  "detail": "error message"
}
```

**Status Codes:**
- `200`: Success
- `400`: Bad request (missing fields, empty values)
- `500`: Server error (LLM integration issue)

### GET /health-check

Check API availability.

**Response:**
```json
{
  "status": "healthy",
  "service": "ethical-ai-decision-checker"
}
```

## Use Case Examples

### Hiring Decision
```bash
curl -X POST http://localhost:8000/evaluate-decision \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "Reject candidate for engineering role",
    "context": {
      "gender": "female",
      "years_experience": 8,
      "education": "bootcamp",
      "github_stars": 500
    }
  }'
```

**Expected**: Flags "bias" and "fairness" due to gender in decision.

### Loan Approval
```bash
curl -X POST http://localhost:8000/evaluate-decision \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "Deny loan application",
    "context": {
      "credit_score": 720,
      "income": 85000,
      "zip_code": "90210",
      "employment_years": 12
    }
  }'
```

**Expected**: Flags "bias" and "discrimination" due to zip code.

### Fair Decision
```bash
curl -X POST http://localhost:8000/evaluate-decision \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "Approve promotion",
    "context": {
      "performance_rating": 4.8,
      "years_in_role": 3,
      "collaboration_feedback": "excellent"
    }
  }'
```

**Expected**: Low risk flags, high confidence score.

## Project Structure

```
StartupIdea/
├── backend/
│   ├── main.py              # FastAPI app & routes
│   ├── prompts.py           # LLM prompt templates
│   ├── risk_detector.py     # Risk detection heuristics
│   ├── response_formatter.py# Response validation
│   ├── config.py            # Configuration
│   └── __init__.py
├── frontend/
│   └── index.html           # Web UI (optional)
├── tests/
│   ├── test_api.py          # Integration tests
│   └── USE_CASES.md         # Test scenarios
├── main.py                  # Entry point
├── requirements.txt         # Dependencies
├── .env.example             # Environment template
├── .github/
│   └── copilot-instructions.md  # AI developer guide
├── README.md                # Project overview
├── DEPLOYMENT.md            # GCP deployment guide
└── Dockerfile               # Docker configuration
```

## Development Workflow

### Adding New Risk Detection Rule

Edit `backend/risk_detector.py`:

```python
def detect_custom_risks(decision: str, context: dict) -> List[str]:
    """Detect custom risks."""
    flags = []
    
    if some_condition(decision, context):
        flags.append("custom_risk_type")
    
    return flags

# Add to detect_all_risks():
def detect_all_risks(decision: str, context: dict) -> List[str]:
    all_flags = set()
    all_flags.update(detect_custom_risks(decision, context))
    # ... other detectors
    return sorted(list(all_flags))
```

### Modifying LLM Prompts

Edit `backend/prompts.py`:

```python
SYSTEM_PROMPT = """New system prompt with updated instructions..."""

USER_PROMPT_TEMPLATE = """New user prompt template with {decision} and {context}"""
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test
pytest tests/test_api.py::test_evaluate_decision_hiring_bias -v

# With coverage
pytest tests/ --cov=backend --cov-report=html
```

## Deployment

For GCP deployment, see [DEPLOYMENT.md](./DEPLOYMENT.md)

Quick deploy:
```bash
gcloud run deploy ethical-ai-checker \
  --source . \
  --set-env-vars OPENAI_API_KEY=$OPENAI_API_KEY
```

## Troubleshooting

**ImportError with backend modules:**
```bash
# Ensure you're in the project root
cd /Users/chakpotluri/Desktop/StartupIdea

# Use the venv python
source venv/bin/activate
```

**OpenAI API errors:**
```bash
# Verify API key
echo $OPENAI_API_KEY

# Check it's valid format (sk-...)
```

**Server won't start:**
```bash
# Check port is available
lsof -i :8000

# If occupied, kill process
kill -9 <PID>

# Or use different port
uvicorn main:app --port 8001
```

**Tests fail:**
```bash
# Ensure server is running
# Try rebuilding venv
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Next Steps

1. ✅ Set up API and run tests
2. 🔑 Configure real OpenAI API key (not test key)
3. 🧪 Test with more complex decisions and contexts
4. 🚀 Deploy to GCP Cloud Run
5. 🔐 Add API key authentication for production
6. 📊 Add monitoring and logging
7. 💾 Implement audit logging for decisions
8. 🎨 Enhance frontend UI

## Support

For issues:
1. Check `.github/copilot-instructions.md` for architecture details
2. Review test cases in `tests/USE_CASES.md`
3. Check `DEPLOYMENT.md` for deployment issues
4. See `backend/` files for implementation details
