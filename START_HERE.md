# 🚀 START HERE - Ethical AI Decision Checker

Welcome! This is a **complete, production-ready API** for evaluating decisions using ethical reasoning frameworks.

## ⚡ Quick Links

- **Just want to run it?** → See [GETTING_STARTED.md](./GETTING_STARTED.md)
- **Ready to deploy?** → See [DEPLOYMENT.md](./DEPLOYMENT.md)
- **Want the full story?** → See [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md)
- **Need developer conventions?** → See [.github/copilot-instructions.md](./.github/copilot-instructions.md)
- **Launch checklist?** → See [LAUNCH_CHECKLIST.md](./LAUNCH_CHECKLIST.md)

## 🎯 What This Does

The system evaluates decisions (hiring, lending, policy, etc.) through **three ethical frameworks**:

1. **Kantian Ethics** - Is it fair and universally applicable?
2. **Utilitarian** - Does it maximize overall good?
3. **Virtue Ethics** - Does it reflect integrity?

It also **detects risks** like bias, discrimination, and transparency issues.

## ⚡ 60-Second Test

```bash
# 1. Start server (if not running)
cd /Users/chakpotluri/Desktop/StartupIdea
source venv/bin/activate  
uvicorn main:app --port 8000 &

# 2. Test the API
curl -X POST http://localhost:8000/evaluate-decision \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "Reject job candidate",
    "context": {"gender": "female", "experience": 5}
  }' | python -m json.tool

# 3. Check result
# You should see risk_flags: ["bias", "fairness"]
```

## 📊 Example Response

```json
{
  "kantian_analysis": "This violates fairness principles...",
  "utilitarian_analysis": "Rejecting based on gender reduces overall benefit...",
  "virtue_ethics_analysis": "This lacks integrity...",
  "risk_flags": ["bias", "fairness"],
  "confidence_score": 0.92,
  "recommendation": "Remove gender from evaluation criteria"
}
```

## 🏗️ Project Structure

```
/
├── backend/              ← Core API (FastAPI)
├── frontend/             ← Web UI (HTML)
├── tests/                ← Integration tests (6 passing ✅)
├── GETTING_STARTED.md    ← Setup & usage guide
├── DEPLOYMENT.md         ← GCP deployment guide
├── PROJECT_SUMMARY.md    ← Architecture details
└── requirements.txt      ← Python dependencies
```

## ✅ Status

- **API**: ✅ Live and tested
- **Tests**: ✅ 6/6 passing
- **Documentation**: ✅ Comprehensive
- **Deployment**: ✅ GCP Cloud Run ready
- **Frontend**: ✅ Interactive UI included

## 🚀 Next Steps

**Option 1: Run Locally**
```bash
source venv/bin/activate
uvicorn main:app --reload --port 8000
# Open http://localhost:8000 in your browser
```

**Option 2: Deploy to GCP**
```bash
gcloud run deploy ethical-ai-checker --source . \
  --set-env-vars OPENAI_API_KEY=$OPENAI_API_KEY
```

**Option 3: Test via API**
```bash
# See GETTING_STARTED.md for 10+ examples
pytest tests/test_api.py -v
```

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [GETTING_STARTED.md](./GETTING_STARTED.md) | Setup, API reference, examples |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | GCP Cloud Run step-by-step guide |
| [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md) | Architecture, design decisions |
| [.github/copilot-instructions.md](./.github/copilot-instructions.md) | AI developer conventions |
| [tests/USE_CASES.md](./tests/USE_CASES.md) | Real-world test scenarios |
| [LAUNCH_CHECKLIST.md](./LAUNCH_CHECKLIST.md) | Complete feature checklist |

## 🔑 Environment Setup

```bash
# Copy template
cp .env.example .env

# Edit with your OpenAI key
export OPENAI_API_KEY=sk-your-actual-key-here
```

## 🧪 Run Tests

```bash
pytest tests/test_api.py -v
# Expected: 6 passed ✅
```

## 💬 Common Questions

**Q: How do I customize the ethical frameworks?**
A: Edit `backend/prompts.py` to modify system prompts or `backend/risk_detector.py` to add risk rules.

**Q: Can I use a different LLM?**
A: Yes! The system uses OpenAI by default, but you can modify `backend/main.py` to integrate Claude, Gemini, etc.

**Q: Is this production-ready?**
A: Yes! It has error handling, validation, tests, and Dockerfile. Just add API key authentication for your use case.

**Q: What's the cost?**
A: GCP Cloud Run is ~$0.00001667/vCPU-second. Typical: ~$0.10 per 1,000 requests or ~$3-5/month.

## 📞 Support

- **Architecture questions** → `.github/copilot-instructions.md`
- **Getting started** → `GETTING_STARTED.md`
- **Deployment help** → `DEPLOYMENT.md`
- **Implementation details** → `PROJECT_SUMMARY.md`

---

**🎉 You're all set! Pick a doc above and get started.** 🚀
