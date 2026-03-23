# Deployment Guide - Ethical AI Decision Checker

## GCP Cloud Run Deployment

This guide walks through deploying the application to Google Cloud Platform using Cloud Run.

### Prerequisites

- Google Cloud Platform account with billing enabled
- `gcloud` CLI installed and configured
- Docker installed (for local testing)

### Step 1: Create GCP Project

```bash
gcloud projects create ethical-ai-checker --set-as-default
gcloud billing projects link ethical-ai-checker --billing-account=[BILLING_ACCOUNT_ID]
```

### Step 2: Enable Required APIs

```bash
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

### Step 3: Set Environment Variables

```bash
export GCP_PROJECT_ID=$(gcloud config get-value project)
export GCP_REGION=us-central1
export OPENAI_API_KEY=your_actual_api_key_here
```

### Step 4: Build and Deploy to Cloud Run

**Option A: Deploy from source** (simplest)

```bash
gcloud run deploy ethical-ai-checker \
  --source . \
  --platform managed \
  --region $GCP_REGION \
  --set-env-vars OPENAI_API_KEY=$OPENAI_API_KEY \
  --allow-unauthenticated
```

**Option B: Build Docker image first** (for testing locally)

```bash
# Build image
docker build -t ethical-ai-checker .

# Run locally
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  ethical-ai-checker

# Push to GCP Artifact Registry
gcloud builds submit \
  --tag gcr.io/$GCP_PROJECT_ID/ethical-ai-checker \
  --project=$GCP_PROJECT_ID

# Deploy from registry
gcloud run deploy ethical-ai-checker \
  --image gcr.io/$GCP_PROJECT_ID/ethical-ai-checker \
  --platform managed \
  --region $GCP_REGION \
  --set-env-vars OPENAI_API_KEY=$OPENAI_API_KEY \
  --allow-unauthenticated
```

### Step 5: Access Your Service

After deployment, gcloud will output a service URL. Test it:

```bash
SERVICE_URL=$(gcloud run services describe ethical-ai-checker \
  --platform managed \
  --region $GCP_REGION \
  --format 'value(status.url)')

# Health check
curl $SERVICE_URL/health-check

# Evaluate decision
curl -X POST $SERVICE_URL/evaluate-decision \
  -H "Content-Type: application/json" \
  -d '{
    "decision":"Reject candidate",
    "context":{"gender":"female","experience":5}
  }'
```

### Step 6: Enable API Authentication (Production)

For production, enable API key authentication:

```bash
# Create service account
gcloud iam service-accounts create ethical-ai-api-client

# Grant invoke permission
gcloud run services add-iam-policy-binding ethical-ai-checker \
  --member=serviceAccount:ethical-ai-api-client@$GCP_PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/run.invoker \
  --region=$GCP_REGION

# Create API key
gcloud alpha services api-keys create \
  --display-name="Ethical AI API Key" \
  --api-target=run.googleapis.com
```

### Step 7: Configure Auto-scaling (Optional)

```bash
gcloud run services update ethical-ai-checker \
  --region $GCP_REGION \
  --concurrency 100 \
  --memory 512Mi \
  --cpu 1
```

### Step 8: Set Up Monitoring (Optional)

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ethical-ai-checker" \
  --limit 50 \
  --project=$GCP_PROJECT_ID
```

### Step 9: Update Environment Variables

To update the OpenAI API key after deployment:

```bash
gcloud run services update ethical-ai-checker \
  --set-env-vars OPENAI_API_KEY=new_key_here \
  --region $GCP_REGION
```

## Dockerfile Configuration

The application uses this deployment configuration:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

This is specified in `app.yaml` for App Engine or generated automatically by Cloud Run.

## Environment Variables

**Required**:
- `OPENAI_API_KEY`: Your OpenAI API key

**Optional**:
- `LLM_MODEL`: LLM model name (default: `gpt-4`)
- `LLM_TEMPERATURE`: Temperature for LLM (default: `0.7`)
- `LLM_MAX_TOKENS`: Max tokens for LLM response (default: `1500`)
- `API_HOST`: API bind host (default: `0.0.0.0`)
- `API_PORT`: API bind port (default: `8000`)
- `ENVIRONMENT`: `development` or `production` (default: `development`)

## Troubleshooting

**Service fails to deploy:**
```bash
gcloud run deploy ethical-ai-checker --source . \
  --platform managed \
  --region $GCP_REGION \
  --debug
```

**Check logs:**
```bash
gcloud run services describe ethical-ai-checker \
  --region $GCP_REGION

gcloud logging read "resource.type=cloud_run_revision" \
  --limit 100 \
  --format json \
  --project=$GCP_PROJECT_ID
```

**Test endpoint directly:**
```bash
curl -v $SERVICE_URL/health-check
```

## Cost Considerations

- Cloud Run: ~$0.00001667 per vCPU-second, ~$0.0000025 per GB-second
- Typical request: 1-2 seconds, ~256MB
- Estimated cost: ~$0.10 per 1000 requests
- Monthly: ~$3-5 for moderate usage

## Next Steps

1. Set up CI/CD with Cloud Build for automated deployments
2. Add rate limiting with API Gateway
3. Enable Cloud Tasks for async processing
4. Set up monitoring alerts with Cloud Monitoring
5. Create custom domain with Cloud Load Balancing
