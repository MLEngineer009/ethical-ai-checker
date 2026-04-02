#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# Pragma — Local Stack Test
# Tests the full backend (FastAPI + Pragma model) locally before Railway deploy.
#
# Usage:
#   chmod +x ml/test_local_stack.sh
#   HF_REPO=yourname/pragma-ethics-v1 HF_TOKEN=hf_xxx ./ml/test_local_stack.sh
# ──────────────────────────────────────────────────────────────────────────────

set -e

HF_REPO="${HF_REPO:-}"
HF_TOKEN="${HF_TOKEN:-}"

if [ -z "$HF_REPO" ]; then
  echo "❌ Set HF_REPO env var first:"
  echo "   HF_REPO=yourname/pragma-ethics-v1 ./ml/test_local_stack.sh"
  exit 1
fi

echo ""
echo "══════════════════════════════════════════════"
echo "  Pragma Local Stack Test"
echo "  Model: $HF_REPO"
echo "══════════════════════════════════════════════"

# Load .env
source .env 2>/dev/null || true
export CUSTOM_MODEL_REPO="$HF_REPO"
export HF_TOKEN="$HF_TOKEN"

# Start backend in background
echo ""
echo "▶ Starting backend on port 8765..."
uvicorn backend.main:app --host 127.0.0.1 --port 8765 --log-level warning &
BACKEND_PID=$!

# Wait for it to be ready
sleep 3

cleanup() {
  kill $BACKEND_PID 2>/dev/null
}
trap cleanup EXIT

echo "▶ Checking health..."
HEALTH=$(curl -s http://localhost:8765/health-check)
echo "  $HEALTH"

PRAGMA_LIVE=$(echo "$HEALTH" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['model']['pragma'])" 2>/dev/null)
if [ "$PRAGMA_LIVE" != "True" ]; then
  echo ""
  echo "⚠  model.pragma = false — CUSTOM_MODEL_REPO may not be set or HF_TOKEN missing"
  echo "   Continuing anyway (will fall through to Claude)..."
fi

# Get a guest token
echo ""
echo "▶ Getting guest token..."
TOKEN=$(curl -s -X POST http://localhost:8765/auth/guest | python3 -c "import json,sys; print(json.load(sys.stdin)['token'])")
echo "  Token: ${TOKEN:0:20}..."

# Run a test evaluation
echo ""
echo "▶ Running test evaluation..."
RESULT=$(curl -s -X POST http://localhost:8765/evaluate-decision \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "decision": "Reject job candidate",
    "category": "hiring",
    "context": {"gender": "female", "experience_years": 10, "education": "master"}
  }')

PROVIDER=$(echo "$RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('provider','unknown'))" 2>/dev/null)
CONFIDENCE=$(echo "$RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"{d.get('confidence_score',0):.0%}\")" 2>/dev/null)
FLAGS=$(echo "$RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(', '.join(d.get('risk_flags',[])))" 2>/dev/null)

echo ""
echo "══════════════════════════════════════════════"
if [ "$PROVIDER" = "pragma" ]; then
  echo "  ✅ Provider: PRAGMA (your model is live!)"
else
  echo "  ℹ  Provider: $PROVIDER"
fi
echo "  Confidence: $CONFIDENCE"
echo "  Risk flags: $FLAGS"
echo "══════════════════════════════════════════════"
echo ""

if [ "$PROVIDER" = "pragma" ]; then
  echo "🚀 Ready to deploy to Railway!"
  echo "   Set CUSTOM_MODEL_REPO=$HF_REPO in Railway Variables."
else
  echo "ℹ  Pragma model not active. Complete Colab training first, then:"
  echo "   HF_REPO=yourname/pragma-ethics-v1 ./ml/test_local_stack.sh"
fi
echo ""
