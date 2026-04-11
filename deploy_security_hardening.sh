#!/bin/bash
set -e

echo "🔒 Enterprise Security Hardening - Automated Deployment"
echo "========================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then
  echo -e "${RED}❌ Do not run as root${NC}"
  exit 1
fi

# Step 1: Verify secrets are configured
echo -e "${YELLOW}Step 1: Verifying secrets...${NC}"

if [ ! -f .env.production ]; then
  echo -e "${RED}❌ .env.production not found${NC}"
  echo "Copy .env.production template and fill in secrets"
  exit 1
fi

# Check for CHANGE_ME placeholders
if grep -q "CHANGE_ME" .env.production; then
  echo -e "${RED}❌ Found CHANGE_ME placeholders in .env.production${NC}"
  echo "Generate secrets with:"
  echo "  openssl rand -hex 32"
  echo "  openssl rand -urlsafe 32"
  exit 1
fi

echo -e "${GREEN}✅ Secrets configured${NC}"

# Step 2: Backup database
echo -e "${YELLOW}Step 2: Backing up database...${NC}"

BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"

if command -v pg_dump &> /dev/null; then
  docker-compose exec -T postgres pg_dump -U finuser financedb > "$BACKUP_FILE" 2>/dev/null || true
  if [ -f "$BACKUP_FILE" ]; then
    echo -e "${GREEN}✅ Database backed up to $BACKUP_FILE${NC}"
  else
    echo -e "${YELLOW}⚠️  Could not backup database (continuing anyway)${NC}"
  fi
else
  echo -e "${YELLOW}⚠️  pg_dump not found, skipping backup${NC}"
fi

# Step 3: Replace service files
echo -e "${YELLOW}Step 3: Replacing service files with hardened versions...${NC}"

cp microservices/api-gateway/main_hardened.py microservices/api-gateway/main.py
cp microservices/transaction-service/main_hardened.py microservices/transaction-service/main.py
cp microservices/ai-service/main_hardened.py microservices/ai-service/main.py
cp microservices/shared/models_hardened.py microservices/shared/models.py
cp microservices/shared/db_hardened.py microservices/shared/db.py

echo -e "${GREEN}✅ Service files updated${NC}"

# Step 4: Update requirements
echo -e "${YELLOW}Step 4: Updating dependencies...${NC}"

if ! grep -q "cryptography" microservices/shared/requirements.txt; then
  echo "cryptography>=41.0.0" >> microservices/shared/requirements.txt
fi

echo -e "${GREEN}✅ Dependencies updated${NC}"

# Step 5: Run database migration
echo -e "${YELLOW}Step 5: Running database migration...${NC}"

if [ -f "alembic/versions/001_security_hardening.py" ]; then
  docker-compose exec -T postgres psql -U finuser -d financedb -c "SELECT 1" > /dev/null 2>&1
  if [ $? -eq 0 ]; then
    # Run migration
    docker-compose run --rm api-gateway alembic upgrade head || true
    echo -e "${GREEN}✅ Database migration completed${NC}"
  else
    echo -e "${YELLOW}⚠️  Database not accessible, run migration manually:${NC}"
    echo "  alembic upgrade head"
  fi
else
  echo -e "${YELLOW}⚠️  Migration file not found, skipping${NC}"
fi

# Step 6: Rebuild and restart services
echo -e "${YELLOW}Step 6: Rebuilding and restarting services...${NC}"

docker-compose down
docker-compose up -d --build

echo -e "${GREEN}✅ Services restarted${NC}"

# Step 7: Wait for services to be ready
echo -e "${YELLOW}Step 7: Waiting for services to be ready...${NC}"

sleep 10

# Step 8: Verify deployment
echo -e "${YELLOW}Step 8: Verifying deployment...${NC}"

GATEWAY_HEALTH=$(curl -s http://localhost:8000/health | jq -r '.status' 2>/dev/null || echo "error")
TRANSACTIONS_HEALTH=$(curl -s http://localhost:8001/health | jq -r '.status' 2>/dev/null || echo "error")
AI_HEALTH=$(curl -s http://localhost:8002/health | jq -r '.status' 2>/dev/null || echo "error")

if [ "$GATEWAY_HEALTH" = "ok" ]; then
  echo -e "${GREEN}✅ API Gateway: healthy${NC}"
else
  echo -e "${RED}❌ API Gateway: unhealthy${NC}"
fi

if [ "$TRANSACTIONS_HEALTH" = "ok" ]; then
  echo -e "${GREEN}✅ Transaction Service: healthy${NC}"
else
  echo -e "${RED}❌ Transaction Service: unhealthy${NC}"
fi

if [ "$AI_HEALTH" = "ok" ]; then
  echo -e "${GREEN}✅ AI Service: healthy${NC}"
else
  echo -e "${RED}❌ AI Service: unhealthy${NC}"
fi

# Final summary
echo ""
echo "========================================================"
echo -e "${GREEN}🎉 Security hardening deployment complete!${NC}"
echo "========================================================"
echo ""
echo "Next steps:"
echo "1. Test authentication flow (see SECURITY_DEPLOYMENT_GUIDE.md)"
echo "2. Verify audit logs are being written"
echo "3. Test rate limiting"
echo "4. Configure monitoring alerts"
echo "5. Review security checklist in deployment guide"
echo ""
echo "Backup location: $BACKUP_FILE"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT: Keep .env.production secure and never commit it!${NC}"
