# Deployment Guide — Pragma AI Compliance Firewall

## Railway Deployment (Primary)

Railway auto-deploys from GitHub on every push to `main`. No Dockerfile or build config needed — Railway detects Python via `requirements.txt` and runs `uvicorn backend.main:app`.

### Step 1: Create Project

1. Go to [railway.app](https://railway.app) → **New Project**
2. Choose **Deploy from GitHub repo** → select your fork
3. Railway builds and deploys automatically

### Step 2: Add PostgreSQL

In the Railway project dashboard:
1. Click **+ New** → **Database** → **Add PostgreSQL**
2. Railway injects `DATABASE_URL` into your service automatically
3. The app calls `init_db()` on startup and creates all tables via `CREATE TABLE IF NOT EXISTS` + `ALTER TABLE` migrations — no manual schema setup needed

### Step 3: Set Environment Variables

In the Railway service → **Variables** tab, add:

| Variable | Required | Value |
|----------|----------|-------|
| `ANTHROPIC_API_KEY` | Yes | `sk-ant-...` |
| `OPENAI_API_KEY` | Yes | `sk-...` |
| `GOOGLE_CLIENT_ID` | Yes | From Google Cloud Console |
| `ALLOWED_ORIGINS` | Yes | `https://your-railway-url.up.railway.app` (comma-separated for multiple) |
| `STRIPE_SECRET_KEY` | Billing | `sk_live_...` (or `sk_test_...` for testing) |
| `STRIPE_WEBHOOK_SECRET` | Billing | `whsec_...` from Stripe Dashboard → Webhooks |
| `STRIPE_GROWTH_PRICE_ID` | Billing | `price_...` for your Growth plan product |
| `CUSTOM_MODEL_REPO` | Optional | HuggingFace repo name (e.g. `user/pragma-ethics-v1`) |
| `HF_TOKEN` | Optional | HuggingFace API token |

> `DATABASE_URL` is injected automatically by the PostgreSQL plugin — do not set it manually.

### Step 4: Verify Deployment

After Railway deploys, check the service logs for:
```
INFO     __main__ — Database ready
INFO     uvicorn.access — Application startup complete
```

Then health-check the live URL:
```bash
curl https://your-railway-url.up.railway.app/health-check
```

Expected response:
```json
{
  "status": "healthy",
  "model": { "pragma": true, "claude": true, "openai": true }
}
```

---

## Stripe Billing Setup

### Create Growth Plan Product

1. Go to [Stripe Dashboard](https://dashboard.stripe.com) → **Products** → **Add Product**
2. Name: `Pragma Growth`
3. Add a price: **$299 / month**, recurring
4. Copy the **Price ID** (`price_...`) → set as `STRIPE_GROWTH_PRICE_ID` in Railway

### Configure Webhook

1. Stripe Dashboard → **Developers** → **Webhooks** → **Add endpoint**
2. Endpoint URL: `https://your-railway-url.up.railway.app/billing/webhook`
3. Select events:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
4. Copy the **Signing secret** (`whsec_...`) → set as `STRIPE_WEBHOOK_SECRET` in Railway

### Test Billing Locally

```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe

# Forward webhooks to local server
stripe listen --forward-to localhost:8000/billing/webhook

# Trigger a test event
stripe trigger checkout.session.completed
```

---

## Local Development

```bash
# 1. Clone and install
git clone https://github.com/your-org/pragma
cd pragma
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Set env vars (copy and fill in)
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
export GOOGLE_CLIENT_ID=...
export DATABASE_URL=postgresql://postgres:password@localhost:5432/pragma
# Stripe optional for local dev — billing endpoints degrade gracefully without keys

# 3. Start local PostgreSQL (Docker)
docker run -d --name pragma-pg \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 postgres:15

# 4. Run the backend
uvicorn backend.main:app --reload
# API at http://localhost:8000
# Web dashboard at http://localhost:8000
```

---

## Running Tests

```bash
# All tests with coverage
pytest

# Specific suites
pytest tests/test_api.py -v              # 78 API endpoint tests
pytest tests/test_compliance.py -v      # 45 EU AI Act compliance tests
pytest tests/test_regulations.py -v     # Regulatory mapping
pytest tests/test_fintech_compliance.py -v  # Proxy variable guard + audit trail
```

Current status: **382 tests passing, 87% coverage**

---

## Web Frontend (Vercel — Optional)

The backend serves `frontend/index.html` directly, so no separate frontend deployment is required. If you want to host the frontend separately on Vercel:

1. [vercel.com](https://vercel.com) → **New Project** → Import GitHub repo
2. Set **Root Directory** to `frontend/`
3. No build command needed (static HTML)
4. Update `PROD_URL` in `frontend/index.html` to your Railway backend URL

---

## Mobile App (Expo EAS)

```bash
cd mobile
npm install
npm install -g eas-cli
eas login

# Development (Expo Go)
npx expo start

# Production build
eas build --platform ios      # or --platform android
eas submit --platform ios
```

Update `PROD_URL` in `mobile/src/config.ts` to your Railway URL before building for production.

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Claude claude-opus-4-6 API key (primary fallback LLM) |
| `OPENAI_API_KEY` | — | OpenAI API key (secondary fallback) |
| `GOOGLE_CLIENT_ID` | — | Google OAuth 2.0 client ID for Sign-In |
| `DATABASE_URL` | SQLite in-memory | PostgreSQL connection string (auto-injected by Railway) |
| `ALLOWED_ORIGINS` | localhost only | Comma-separated CORS origin allowlist |
| `STRIPE_SECRET_KEY` | — | Stripe secret key for billing |
| `STRIPE_WEBHOOK_SECRET` | — | Stripe webhook signing secret |
| `STRIPE_GROWTH_PRICE_ID` | — | Stripe price ID for Growth plan |
| `CUSTOM_MODEL_REPO` | — | HuggingFace repo for Pragma model (activates primary provider) |
| `HF_TOKEN` | — | HuggingFace API token |
| `OLLAMA_MODEL` | — | Local Ollama model name (e.g. `llama3`) |

---

## Troubleshooting

**Database tables not created on first deploy:**
Check Railway logs for `ERROR` lines during startup. The migration runs `CREATE TABLE IF NOT EXISTS` — safe to re-run. If a column migration fails, check the column name regex filter in `database.py`.

**CORS errors in browser:**
Ensure `ALLOWED_ORIGINS` in Railway matches the exact origin of your frontend (including protocol and port). No trailing slashes.

**Stripe webhook 400 errors:**
Verify the `STRIPE_WEBHOOK_SECRET` matches the signing secret shown in Stripe Dashboard for that specific webhook endpoint. Test locally with `stripe listen`.

**Rate limit 429 on evaluations:**
The free plan allows 100 evaluations/month. Upgrade via `/billing/create-checkout-session` or set `STRIPE_GROWTH_PRICE_ID` and subscribe.
