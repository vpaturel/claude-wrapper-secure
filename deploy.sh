#!/bin/bash
#
# Deploy Claude Multi-Tenant API to GCP Cloud Run
#
# Usage:
#   bash deploy.sh <project_id> <region>
#
# Example:
#   bash deploy.sh my-gcp-project us-central1

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

PROJECT_ID="${1:-}"
REGION="${2:-us-central1}"
SERVICE_NAME="claude-multi-tenant-api"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# ============================================================================
# Validation
# ============================================================================

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: PROJECT_ID required"
    echo "Usage: bash deploy.sh <project_id> <region>"
    exit 1
fi

echo "🚀 Deploying Claude Multi-Tenant API"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Project:  $PROJECT_ID"
echo "Region:   $REGION"
echo "Service:  $SERVICE_NAME"
echo "Image:    $IMAGE_NAME"
echo ""

# ============================================================================
# Build & Push
# ============================================================================

echo "📦 Building Docker image..."
gcloud builds submit \
    --project="$PROJECT_ID" \
    --tag="$IMAGE_NAME" \
    --timeout=10m \
    .

echo "✅ Image built: $IMAGE_NAME"

# ============================================================================
# Deploy Cloud Run
# ============================================================================

echo ""
echo "🚀 Deploying to Cloud Run..."

gcloud run deploy "$SERVICE_NAME" \
    --project="$PROJECT_ID" \
    --image="$IMAGE_NAME" \
    --platform=managed \
    --region="$REGION" \
    --allow-unauthenticated \
    --memory=2Gi \
    --cpu=2 \
    --timeout=300s \
    --min-instances=1 \
    --max-instances=10 \
    --concurrency=10 \
    --port=8080 \
    --set-env-vars="ENVIRONMENT=production" \
    --service-account="default"

echo ""
echo "✅ Deployment complete!"

# ============================================================================
# Get Service URL
# ============================================================================

SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --format="value(status.url)")

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 API deployed successfully!"
echo ""
echo "URL:     $SERVICE_URL"
echo "Health:  $SERVICE_URL/health"
echo "Docs:    $SERVICE_URL/docs"
echo ""
echo "📚 Test API:"
echo ""
echo "curl -X POST $SERVICE_URL/v1/messages \\"
echo "  -H \"Authorization: Bearer sk-ant-oat01-YOUR_TOKEN\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"messages\": [{\"role\": \"user\", \"content\": \"Hello\"}]}'"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
