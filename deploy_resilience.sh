#!/bin/bash
# Complete Resilience Deployment Script

set -e

echo "🛡️ RESILIENCE & SELF-HEALING DEPLOYMENT"
echo "========================================"
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}✅${NC} $1"; }
error() { echo -e "${RED}❌${NC} $1"; }
warn() { echo -e "${YELLOW}⚠️${NC}  $1"; }

# Step 1: Verify prerequisites
echo "Step 1: Verifying prerequisites..."

if ! command -v docker-compose &> /dev/null; then
    error "docker-compose not found"
    exit 1
fi

if ! command -v openssl &> /dev/null; then
    error "openssl not found"
    exit 1
fi

log "Prerequisites verified"

# Step 2: Generate secrets if needed
echo ""
echo "Step 2: Checking secrets configuration..."

if [ ! -f .env.production ]; then
    warn ".env.production not found, creating from template..."

    JWT_SECRET=$(openssl rand -hex 32)
    ENCRYPTION_KEY=$(openssl rand -hex 32)
    INTERNAL_KEY=$(openssl rand -urlsafe 32)

    cat > .env.production <<EOF
# Auto-generated secrets - $(date)
JWT_SECRET_KEY=$JWT_SECRET
ENCRYPTION_KEY=$ENCRYPTION_KEY
INTERNAL_SERVICE_KEY=$INTERNAL_KEY

# Configure these manually:
SECRETS_BACKEND=env
ADMIN_EMAILS=admin@example.com
ALLOWED_ORIGINS=http://localhost:3000
ALERT_WEBHOOK_URL=

# Database
DATABASE_URL=postgresql+asyncpg://finuser:finpass123@postgres:5432/financedb
REDIS_URL=redis://redis:6379/0
EOF

    log "Generated .env.production with secure secrets"
    warn "IMPORTANT: Review and update .env.production before production deployment!"
else
    log ".env.production exists"
fi

# Step 3: Install dependencies
echo ""
echo "Step 3: Updating dependencies..."

if ! grep -q "prometheus-client" microservices/shared/requirements.txt 2>/dev/null; then
    echo "prometheus-client>=0.19.0" >> microservices/shared/requirements.txt
fi

log "Dependencies updated"

# Step 4: Create backup directory
echo ""
echo "Step 4: Setting up backup system..."

mkdir -p /backups
chmod +x scripts/backup_restore.sh
chmod +x scripts/chaos_test.sh

log "Backup system ready"

# Step 5: Deploy resilient services
echo ""
echo "Step 5: Deploying resilient services..."

if [ -f microservices/api-gateway/main_resilient.py ]; then
    cp microservices/api-gateway/main_resilient.py microservices/api-gateway/main.py
    log "Deployed resilient API Gateway"
else
    warn "main_resilient.py not found, skipping"
fi

# Step 6: Restart services
echo ""
echo "Step 6: Restarting services..."

docker-compose down
docker-compose up -d --build

log "Services restarted"

# Step 7: Wait for services
echo ""
echo "Step 7: Waiting for services to be ready..."

sleep 15

# Step 8: Verify deployment
echo ""
echo "Step 8: Verifying deployment..."

GATEWAY_OK=false
METRICS_OK=false

if curl -s http://localhost:8000/health | grep -q "status"; then
    GATEWAY_OK=true
    log "API Gateway: healthy"
else
    error "API Gateway: unhealthy"
fi

if curl -s http://localhost:8000/metrics | grep -q "http_requests_total"; then
    METRICS_OK=true
    log "Metrics endpoint: working"
else
    warn "Metrics endpoint: not accessible"
fi

# Step 9: Run basic tests
echo ""
echo "Step 9: Running basic resilience tests..."

# Test health endpoint
HEALTH=$(curl -s http://localhost:8000/health)
if echo "$HEALTH" | grep -q "components"; then
    log "Health check: enhanced monitoring active"
else
    warn "Health check: basic mode"
fi

# Step 10: Summary
echo ""
echo "========================================"
echo "DEPLOYMENT SUMMARY"
echo "========================================"

if $GATEWAY_OK && $METRICS_OK; then
    log "Resilience deployment successful!"
    echo ""
    echo "Next steps:"
    echo "1. Configure alerting webhook in .env.production"
    echo "2. Set up automated backups: crontab -e"
    echo "   Add: 0 2 * * * /path/to/scripts/backup_restore.sh backup"
    echo "3. Run chaos tests: ./scripts/chaos_test.sh all"
    echo "4. Configure Prometheus scraping: http://localhost:8000/metrics"
    echo "5. Review RESILIENCE_COMPLETE.md for operational procedures"
else
    error "Deployment completed with warnings"
    echo "Check logs: docker-compose logs"
fi

echo ""
echo "Documentation:"
echo "  - RESILIENCE_COMPLETE.md - Complete resilience guide"
echo "  - SECURITY_DEPLOYMENT_GUIDE.md - Security features"
echo "  - scripts/backup_restore.sh - Backup operations"
echo "  - scripts/chaos_test.sh - Chaos testing"
echo ""
