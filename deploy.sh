#!/usr/bin/env bash
# =====================================================================
# NotifAI Enterprise - Cloud Run Deployment Script
# =====================================================================
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - GCP project with billing enabled
#   - Required APIs enabled (see below)
#
# Usage:
#   ./deploy.sh [PROJECT_ID] [REGION]
#
# Example:
#   ./deploy.sh my-project us-central1
#
# This script will:
#   1. Enable required GCP APIs
#   2. Create Artifact Registry repository
#   3. Build and push Docker image
#   4. Store secrets in Secret Manager
#   5. Deploy to Cloud Run
#
# Expected monthly cost (free tier / minimal usage):
#   - Cloud Run: $0 (within free tier: 2M requests, 180K vCPU-s, 360K GiB-s)
#   - Artifact Registry: ~$0.10/GB/month (0.5GB image = ~$0.05/month)
#   - Secret Manager: $0.06/secret/version/month (~$0.30 for 5 secrets)
#   - Gemini API: Pay per use (~$0.001-0.01 per request)
#   - TOTAL: ~$0.50-2.00/month for development workloads
#
# Optional: Cloud SQL with pgvector adds ~$7-10/month (db-f1-micro)
# =====================================================================

set -euo pipefail

PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${2:-us-central1}"
SERVICE_NAME="notifai-api"
REPO_NAME="notifai-repo"
IMAGE_NAME="notifai-api"

if [ -z "$PROJECT_ID" ]; then
    echo "ERROR: No project ID provided and no default project set."
    echo "Usage: ./deploy.sh [PROJECT_ID] [REGION]"
    exit 1
fi

echo "============================================================"
echo "  NotifAI Enterprise - Cloud Run Deployment"
echo "  Project: $PROJECT_ID"
echo "  Region:  $REGION"
echo "============================================================"
echo ""

# === Step 1: Enable required APIs ===
echo "[1/6] Enabling required GCP APIs..."
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    cloudbuild.googleapis.com \
    --project="$PROJECT_ID" --quiet
echo "  APIs enabled."

# === Step 2: Create Artifact Registry repo ===
echo "[2/6] Setting up Artifact Registry..."
gcloud artifacts repositories describe "$REPO_NAME" \
    --location="$REGION" --project="$PROJECT_ID" 2>/dev/null \
    || gcloud artifacts repositories create "$REPO_NAME" \
        --repository-format=docker \
        --location="$REGION" \
        --description="NotifAI Docker images" \
        --project="$PROJECT_ID" --quiet
echo "  Artifact Registry ready: $REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME"

# === Step 3: Build and push Docker image ===
echo "[3/6] Building and pushing Docker image..."
IMAGE_URI="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$IMAGE_NAME:latest"

docker build -f Dockerfile.cloudrun -t "$IMAGE_URI" .
docker push "$IMAGE_URI"
echo "  Image pushed: $IMAGE_URI"

# === Step 4: Store secrets in Secret Manager ===
echo "[4/6] Storing secrets in Secret Manager..."

store_secret() {
    local secret_name="$1"
    local secret_value="$2"
    if [ -z "$secret_value" ]; then
        echo "  WARNING: Skipping $secret_name (not set)"
        return
    fi
    echo "$secret_value" | gcloud secrets create "$secret_name" \
        --data-file=- --replication-policy=automatic \
        --project="$PROJECT_ID" --quiet 2>/dev/null \
        || echo "$secret_value" | gcloud secrets versions add "$secret_name" \
            --data-file=- --project="$PROJECT_ID" --quiet
    echo "  Secret stored: $secret_name"
}

# Read from environment or prompt
GOOGLE_API_KEY="${GOOGLE_API_KEY:-}"
store_secret "google-api-key" "$GOOGLE_API_KEY"

# === Step 5: Deploy to Cloud Run ===
echo "[5/6] Deploying to Cloud Run..."

# Grant Cloud Run access to secrets
gcloud secrets add-iam-policy-binding google-api-key \
    --member="serviceAccount:${PROJECT_NUMBER:-$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')}@cloudservices.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project="$PROJECT_ID" --quiet 2>/dev/null || true

gcloud run deploy "$SERVICE_NAME" \
    --image="$IMAGE_URI" \
    --platform=managed \
    --region="$REGION" \
    --allow-unauthenticated \
    --port=8080 \
    --memory=512Mi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=10 \
    --concurrency=80 \
    --timeout=300 \
    --set-env-vars="GOOGLE_GENAI_USE_ENTERPRISE=false" \
    --set-secrets="GOOGLE_API_KEY=google-api-key:latest" \
    --project="$PROJECT_ID" --quiet

# === Step 6: Get service URL ===
echo "[6/6] Deployment complete!"
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --region="$REGION" --project="$PROJECT_ID" \
    --format='value(status.url)')

echo ""
echo "============================================================"
echo "  Deployment Successful!"
echo "  Service URL: $SERVICE_URL"
echo ""
echo "  Health check: $SERVICE_URL/health"
echo "  API docs:     $SERVICE_URL/docs"
echo "  Metrics:      $SERVICE_URL/metrics"
echo ""
echo "  Expected Monthly Cost:"
echo "    Cloud Run:           \$0.00 (free tier: 2M req, 180K vCPU-s)"
echo "    Artifact Registry:   ~\$0.05 (0.5GB image)"
echo "    Secret Manager:      ~\$0.06 (1 secret)"
echo "    Gemini API:          ~\$0.50-5.00 (usage-based)"
echo "    ─────────────────────────────────────────"
echo "    TOTAL:               ~\$0.60-5.20/month"
echo ""
echo "  Optional additions:"
echo "    Cloud SQL (pgvector): +\$7-10/month (db-f1-micro)"
echo "    Vertex AI Vector Search: usage-based"
echo "============================================================"