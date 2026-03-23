# Ethical AI Decision Checker

An API-first system that evaluates decisions using ethical reasoning frameworks and detects risks like bias and discrimination.

## Quick Start

### 1. Setup Environment
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Set OpenAI API Key
```bash
export OPENAI_API_KEY=your_key_here
```

### 3. Run Backend
```bash
cd backend
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

### 4. Health Check
```bash
curl http://localhost:8000/health-check
```

## API Usage

### Evaluate a Decision

**Endpoint**: `POST /localhost:8000/evaluate-decision`

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

**Response**:
```json
{
  "kantian_analysis": "This decision violates the principle of universality...",
  "utilitarian_analysis": "Rejecting based on gender reduces overall good...",
  "virtue_ethics_analysis": "This lacks integrity and fairness...",
  "risk_flags": ["bias", "fairness", "discrimination"],
  "confidence_score": 0.92,
  "recommendation": "Remove gender from evaluation and focus on experience and skills"
}
```

## Running Tests

```bash
pytest tests/test_api.py -v
```

## Project Structure

```
backend/
  main.py              # FastAPI application
  prompts.py           # LLM prompt templates
  risk_detector.py     # Risk detection heuristics
frontend/              # (React UI - future)
tests/
  test_api.py          # Integration tests
requirements.txt       # Python dependencies
```

## Development

See `.github/copilot-instructions.md` for detailed conventions and architecture patterns.

## Deployment (GCP)

Deploy to Cloud Run:
```bash
gcloud run deploy ethical-ai-checker \
  --source . \
  --platform managed \
  --region us-central1 \
  --set-env-vars OPENAI_API_KEY=$OPENAI_API_KEY
```

## License

MIT
