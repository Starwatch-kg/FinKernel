#!/bin/bash
# Chaos Testing Suite - Simulate production failures

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[CHAOS]${NC} $1"
}

error() {
    echo -e "${RED}[CHAOS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[CHAOS]${NC} $1"
}

# Test 1: Redis Failure
test_redis_failure() {
    log "Test 1: Simulating Redis failure..."

    docker-compose stop redis
    sleep 2

    log "Testing API with Redis down..."
    RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8000/health || echo "000")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

    if [ "$HTTP_CODE" = "200" ]; then
        log "✅ System degraded gracefully (Redis down)"
    else
        error "❌ System failed completely (expected graceful degradation)"
    fi

    log "Restoring Redis..."
    docker-compose start redis
    sleep 5
    log "Redis restored"
}

# Test 2: Database Failure
test_database_failure() {
    log "Test 2: Simulating database failure..."

    docker-compose stop postgres
    sleep 2

    log "Testing API with database down..."
    RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8000/health || echo "000")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

    if [ "$HTTP_CODE" = "503" ] || [ "$HTTP_CODE" = "500" ]; then
        log "✅ System reported unhealthy (expected)"
    else
        warn "⚠️  Unexpected response: $HTTP_CODE"
    fi

    log "Restoring database..."
    docker-compose start postgres
    sleep 10
    log "Database restored"
}

# Test 3: AI Service Timeout
test_ai_timeout() {
    log "Test 3: Simulating AI service timeout..."

    docker-compose stop ai
    sleep 2

    log "Testing dashboard with AI service down..."
    RESPONSE=$(curl -s http://localhost:8000/api/dashboard/1 \
        -H "Authorization: Bearer test_token" || echo "{}")

    if echo "$RESPONSE" | grep -q "ai_used"; then
        log "✅ Dashboard works without AI (fallback active)"
    else
        warn "⚠️  Dashboard may have issues"
    fi

    log "Restoring AI service..."
    docker-compose start ai
    sleep 5
    log "AI service restored"
}

# Test 4: High Load
test_high_load() {
    log "Test 4: Simulating high load..."

    log "Sending 100 concurrent requests..."

    for i in {1..100}; do
        curl -s http://localhost:8000/health > /dev/null &
    done

    wait

    log "Checking if rate limiting kicked in..."
    RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8000/health)
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "429" ]; then
        log "✅ System handled high load (rate limiting may be active)"
    else
        error "❌ System failed under load"
    fi
}

# Test 5: Network Partition
test_network_partition() {
    log "Test 5: Simulating network partition..."

    log "Disconnecting transaction service..."
    docker-compose pause transactions
    sleep 2

    log "Testing gateway with transaction service unreachable..."
    RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8000/health || echo "000")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

    if [ "$HTTP_CODE" = "200" ]; then
        log "✅ Gateway still responsive (circuit breaker may be open)"
    else
        warn "⚠️  Gateway affected by partition"
    fi

    log "Restoring transaction service..."
    docker-compose unpause transactions
    sleep 3
    log "Transaction service restored"
}

# Test 6: Memory Pressure
test_memory_pressure() {
    log "Test 6: Simulating memory pressure..."

    log "Creating memory pressure on gateway..."
    docker-compose exec -T api-gateway sh -c "
        python3 -c 'import time; x = [0] * 10000000; time.sleep(5)' &
    " 2>/dev/null || true

    sleep 2

    RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8000/health || echo "000")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

    if [ "$HTTP_CODE" = "200" ]; then
        log "✅ System survived memory pressure"
    else
        warn "⚠️  System affected by memory pressure"
    fi
}

# Test 7: Cascading Failures
test_cascading_failures() {
    log "Test 7: Simulating cascading failures..."

    log "Stopping multiple services..."
    docker-compose stop redis ai
    sleep 3

    log "Testing system with multiple failures..."
    RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8000/health || echo "000")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "503" ]; then
        log "✅ System handled cascading failures"
    else
        error "❌ System collapsed under cascading failures"
    fi

    log "Restoring all services..."
    docker-compose start redis ai
    sleep 10
    log "All services restored"
}

# Test 8: Slow Response Times
test_slow_responses() {
    log "Test 8: Testing timeout handling..."

    log "Sending request with short timeout..."
    timeout 2 curl -s http://localhost:8000/api/dashboard/1 \
        -H "Authorization: Bearer test_token" > /dev/null || true

    log "✅ Timeout handling tested"
}

# Recovery Test
test_recovery() {
    log "Recovery Test: Full system recovery..."

    log "Restarting all services..."
    docker-compose restart

    log "Waiting for services to be ready..."
    sleep 15

    # Check all services
    GATEWAY_OK=false
    TRANSACTIONS_OK=false
    AI_OK=false

    if curl -s http://localhost:8000/health | grep -q "ok"; then
        GATEWAY_OK=true
    fi

    if curl -s http://localhost:8001/health | grep -q "ok"; then
        TRANSACTIONS_OK=true
    fi

    if curl -s http://localhost:8002/health | grep -q "ok"; then
        AI_OK=true
    fi

    if $GATEWAY_OK && $TRANSACTIONS_OK && $AI_OK; then
        log "✅ Full system recovery successful"
    else
        error "❌ Some services failed to recover"
        echo "  Gateway: $GATEWAY_OK"
        echo "  Transactions: $TRANSACTIONS_OK"
        echo "  AI: $AI_OK"
    fi
}

# Main execution
echo "╔════════════════════════════════════════╗"
echo "║   CHAOS TESTING SUITE                  ║"
echo "║   Testing System Resilience            ║"
echo "╚════════════════════════════════════════╝"
echo ""

warn "⚠️  This will disrupt running services!"
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    log "Chaos testing cancelled"
    exit 0
fi

echo ""

# Run tests
case "${1:-all}" in
    redis)
        test_redis_failure
        ;;
    database)
        test_database_failure
        ;;
    ai)
        test_ai_timeout
        ;;
    load)
        test_high_load
        ;;
    network)
        test_network_partition
        ;;
    memory)
        test_memory_pressure
        ;;
    cascade)
        test_cascading_failures
        ;;
    slow)
        test_slow_responses
        ;;
    recovery)
        test_recovery
        ;;
    all)
        test_redis_failure
        echo ""
        test_ai_timeout
        echo ""
        test_high_load
        echo ""
        test_network_partition
        echo ""
        test_cascading_failures
        echo ""
        test_recovery
        ;;
    *)
        echo "Usage: $0 {redis|database|ai|load|network|memory|cascade|slow|recovery|all}"
        exit 1
        ;;
esac

echo ""
log "Chaos testing complete!"
