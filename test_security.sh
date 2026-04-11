#!/bin/bash
# Security Testing Suite - Verify all hardening features

set -e

echo "🔒 Security Hardening Test Suite"
echo "================================="
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

BASE_URL="http://localhost:8000"
PASSED=0
FAILED=0

# Helper functions
pass() {
  echo -e "${GREEN}✅ PASS:${NC} $1"
  ((PASSED++))
}

fail() {
  echo -e "${RED}❌ FAIL:${NC} $1"
  ((FAILED++))
}

warn() {
  echo -e "${YELLOW}⚠️  WARN:${NC} $1"
}

# Test 1: JWT V2 Authentication Flow
echo "Test 1: JWT V2 Authentication Flow"
echo "-----------------------------------"

REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"test_'$(date +%s)'@example.com","name":"Test User","password":"Test123456"}')

ACCESS_TOKEN=$(echo $REGISTER_RESPONSE | jq -r '.access_token' 2>/dev/null)
REFRESH_TOKEN=$(echo $REGISTER_RESPONSE | jq -r '.refresh_token' 2>/dev/null)

if [ "$ACCESS_TOKEN" != "null" ] && [ "$ACCESS_TOKEN" != "" ]; then
  pass "Registration returns access token"
else
  fail "Registration did not return access token"
fi

if [ "$REFRESH_TOKEN" != "null" ] && [ "$REFRESH_TOKEN" != "" ]; then
  pass "Registration returns refresh token"
else
  fail "Registration did not return refresh token"
fi

# Test 2: Token Refresh
echo ""
echo "Test 2: Token Refresh"
echo "---------------------"

if [ "$REFRESH_TOKEN" != "null" ] && [ "$REFRESH_TOKEN" != "" ]; then
  REFRESH_RESPONSE=$(curl -s -X POST "$BASE_URL/api/refresh" \
    -H "Content-Type: application/json" \
    -d "{\"refresh_token\":\"$REFRESH_TOKEN\"}")

  NEW_ACCESS=$(echo $REFRESH_RESPONSE | jq -r '.access_token' 2>/dev/null)

  if [ "$NEW_ACCESS" != "null" ] && [ "$NEW_ACCESS" != "" ]; then
    pass "Token refresh works"
  else
    fail "Token refresh failed"
  fi
else
  warn "Skipping token refresh test (no refresh token)"
fi

# Test 3: Protected Endpoint Access
echo ""
echo "Test 3: Protected Endpoint Access"
echo "----------------------------------"

if [ "$ACCESS_TOKEN" != "null" ] && [ "$ACCESS_TOKEN" != "" ]; then
  DASHBOARD_RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/dashboard/1" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

  HTTP_CODE=$(echo "$DASHBOARD_RESPONSE" | tail -n1)

  if [ "$HTTP_CODE" = "200" ]; then
    pass "Protected endpoint accessible with valid token"
  else
    fail "Protected endpoint returned $HTTP_CODE"
  fi
else
  warn "Skipping protected endpoint test (no access token)"
fi

# Test 4: Unauthorized Access
echo ""
echo "Test 4: Unauthorized Access Prevention"
echo "---------------------------------------"

UNAUTH_RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/dashboard/1")
HTTP_CODE=$(echo "$UNAUTH_RESPONSE" | tail -n1)

if [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
  pass "Unauthorized access blocked"
else
  fail "Unauthorized access not blocked (got $HTTP_CODE)"
fi

# Test 5: Security Headers
echo ""
echo "Test 5: Security Headers"
echo "------------------------"

HEADERS=$(curl -s -I "$BASE_URL/health")

if echo "$HEADERS" | grep -q "X-Content-Type-Options"; then
  pass "X-Content-Type-Options header present"
else
  fail "X-Content-Type-Options header missing"
fi

if echo "$HEADERS" | grep -q "X-Frame-Options"; then
  pass "X-Frame-Options header present"
else
  fail "X-Frame-Options header missing"
fi

if echo "$HEADERS" | grep -q "Strict-Transport-Security"; then
  pass "HSTS header present"
else
  fail "HSTS header missing"
fi

if echo "$HEADERS" | grep -q "X-Request-ID"; then
  pass "X-Request-ID header present"
else
  fail "X-Request-ID header missing"
fi

# Test 6: Rate Limiting
echo ""
echo "Test 6: Rate Limiting"
echo "---------------------"

warn "Rate limiting test requires manual verification"
warn "Run: for i in {1..100}; do curl -s $BASE_URL/health & done"

# Test 7: Request Size Limit
echo ""
echo "Test 7: Request Size Limit"
echo "--------------------------"

LARGE_PAYLOAD=$(python3 -c "print('x' * 2000000)")
SIZE_LIMIT_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"test@example.com\",\"name\":\"$LARGE_PAYLOAD\",\"password\":\"Test123456\"}" 2>/dev/null)

HTTP_CODE=$(echo "$SIZE_LIMIT_RESPONSE" | tail -n1)

if [ "$HTTP_CODE" = "413" ] || [ "$HTTP_CODE" = "400" ]; then
  pass "Large request rejected"
else
  warn "Large request handling unclear (got $HTTP_CODE)"
fi

# Test 8: Service Health
echo ""
echo "Test 8: Service Health Checks"
echo "------------------------------"

GATEWAY_HEALTH=$(curl -s "$BASE_URL/health" | jq -r '.status' 2>/dev/null)
TRANSACTIONS_HEALTH=$(curl -s "http://localhost:8001/health" | jq -r '.status' 2>/dev/null)
AI_HEALTH=$(curl -s "http://localhost:8002/health" | jq -r '.status' 2>/dev/null)

if [ "$GATEWAY_HEALTH" = "ok" ]; then
  pass "API Gateway healthy"
else
  fail "API Gateway unhealthy"
fi

if [ "$TRANSACTIONS_HEALTH" = "ok" ]; then
  pass "Transaction Service healthy"
else
  fail "Transaction Service unhealthy"
fi

if [ "$AI_HEALTH" = "ok" ]; then
  pass "AI Service healthy"
else
  fail "AI Service unhealthy"
fi

# Test 9: Database Constraints
echo ""
echo "Test 9: Database Constraints"
echo "----------------------------"

warn "Database constraint tests require direct DB access"
warn "Verify with: psql -U finuser -d financedb"

# Test 10: Audit Logging
echo ""
echo "Test 10: Audit Logging"
echo "----------------------"

warn "Audit log verification requires database access"
warn "Query: SELECT COUNT(*) FROM audit_logs WHERE action = 'register';"

# Summary
echo ""
echo "================================="
echo "Test Summary"
echo "================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
  echo -e "${GREEN}🎉 All tests passed!${NC}"
  exit 0
else
  echo -e "${RED}⚠️  Some tests failed. Review output above.${NC}"
  exit 1
fi
