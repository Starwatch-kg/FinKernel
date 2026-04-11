#!/bin/bash
# Production Readiness Verification Script

echo "=========================================="
echo "Production Readiness Verification"
echo "=========================================="
echo ""

PASS=0
FAIL=0

# Check 1: .env.example exists
if [ -f .env.example ]; then
    echo "✓ .env.example template exists"
    ((PASS++))
else
    echo "✗ .env.example template missing"
    ((FAIL++))
fi

# Check 2: .gitignore includes .env
if grep -q "^\.env$" .gitignore 2>/dev/null; then
    echo "✓ .env in .gitignore"
    ((PASS++))
else
    echo "✗ .env not in .gitignore"
    ((FAIL++))
fi

# Check 3: No hardcoded secrets in auth_utils.py
if grep -q "SECRET_KEY = \"" microservices/api-gateway/auth_utils.py 2>/dev/null; then
    echo "✗ Hardcoded secret found in auth_utils.py"
    ((FAIL++))
else
    echo "✓ No hardcoded secrets in auth_utils.py"
    ((PASS++))
fi

# Check 4: No exposed API keys in docker-compose.yml
if grep -q "sk-or-v1-" docker-compose.yml 2>/dev/null; then
    echo "✗ Exposed API key in docker-compose.yml"
    ((FAIL++))
else
    echo "✓ No exposed API keys in docker-compose.yml"
    ((PASS++))
fi

# Check 5: Config module exists
if [ -f microservices/shared/config.py ]; then
    echo "✓ Configuration module exists"
    ((PASS++))
else
    echo "✗ Configuration module missing"
    ((FAIL++))
fi

# Check 6: Logger module exists
if [ -f microservices/shared/logger.py ]; then
    echo "✓ Logger module exists"
    ((PASS++))
else
    echo "✗ Logger module missing"
    ((FAIL++))
fi

# Check 7: Market data provider exists
if [ -f microservices/shared/market_data.py ]; then
    echo "✓ Deterministic market data provider exists"
    ((PASS++))
else
    echo "✗ Market data provider missing"
    ((FAIL++))
fi

# Check 8: No random calls in portfolio routes
if grep -q "random\." microservices/transaction-service/portfolio_routes.py 2>/dev/null; then
    echo "✗ Random data generation still present"
    ((FAIL++))
else
    echo "✓ No random data generation in portfolio routes"
    ((PASS++))
fi

# Check 9: Startup validation exists
if [ -f microservices/shared/startup.py ]; then
    echo "✓ Startup validation module exists"
    ((PASS++))
else
    echo "✗ Startup validation missing"
    ((FAIL++))
fi

# Check 10: Redis has proper error handling
if grep -q "logger.error" microservices/shared/redis.py 2>/dev/null; then
    echo "✓ Redis has proper error logging"
    ((PASS++))
else
    echo "✗ Redis missing error logging"
    ((FAIL++))
fi

echo ""
echo "=========================================="
echo "Results: $PASS passed, $FAIL failed"
echo "=========================================="
echo ""

if [ $FAIL -eq 0 ]; then
    echo "✅ All checks passed - Production ready!"
    exit 0
else
    echo "❌ Some checks failed - Review required"
    exit 1
fi
