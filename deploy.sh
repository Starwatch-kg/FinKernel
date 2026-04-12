#!/bin/bash
# Production Deployment Script for FIN
# This is the ONLY script you need to deploy the system

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="$PROJECT_DIR/backups"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    log_info "Checking requirements..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    if ! command -v docker compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi

    log_info "✅ All requirements met"
}

backup_database() {
    log_info "Creating database backup..."

    mkdir -p "$BACKUP_DIR"
    BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql"

    if docker compose ps postgres | grep -q "Up"; then
        docker compose exec -T postgres pg_dump -U finuser financedb > "$BACKUP_FILE"
        log_info "✅ Backup created: $BACKUP_FILE"
    else
        log_warn "PostgreSQL not running, skipping backup"
    fi
}

run_migrations() {
    log_info "Running database migrations..."

    docker compose run --rm transactions alembic upgrade head

    if [ $? -eq 0 ]; then
        log_info "✅ Migrations completed"
    else
        log_error "❌ Migrations failed"
        exit 1
    fi
}

build_containers() {
    log_info "Building Docker containers..."

    docker compose build --no-cache

    if [ $? -eq 0 ]; then
        log_info "✅ Build successful"
    else
        log_error "❌ Build failed"
        exit 1
    fi
}

start_services() {
    log_info "Starting services in correct order..."

    # Start database and redis first
    log_info "Starting PostgreSQL and Redis..."
    docker compose up -d postgres redis
    sleep 5

    # Start backend services
    log_info "Starting backend services..."
    docker compose up -d transactions ai
    sleep 5

    # Start gateway
    log_info "Starting API Gateway..."
    docker compose up -d gateway
    sleep 5

    # Start frontend
    log_info "Starting frontend..."
    docker compose up -d frontend
    sleep 5

    log_info "✅ All services started"
}

health_checks() {
    log_info "Running health checks..."

    sleep 10  # Wait for services to be ready

    # Check API Gateway
    if curl -f http://localhost:8000/health &> /dev/null; then
        log_info "✅ API Gateway is healthy"
    else
        log_error "❌ API Gateway health check failed"
        exit 1
    fi

    # Check Transaction Service
    if curl -f http://localhost:8001/health &> /dev/null; then
        log_info "✅ Transaction Service is healthy"
    else
        log_error "❌ Transaction Service health check failed"
        exit 1
    fi

    # Check AI Service
    if curl -f http://localhost:8002/health &> /dev/null; then
        log_info "✅ AI Service is healthy"
    else
        log_error "❌ AI Service health check failed"
        exit 1
    fi

    # Check Frontend
    if curl -f http://localhost/health &> /dev/null; then
        log_info "✅ Frontend is healthy"
    else
        log_error "❌ Frontend health check failed"
        exit 1
    fi

    log_info "✅ All health checks passed"
}

cleanup() {
    log_info "Cleaning up old Docker images..."
    docker image prune -f
    log_info "✅ Cleanup complete"
}

show_status() {
    log_info "Service Status:"
    docker compose ps

    echo ""
    log_info "Logs (last 20 lines):"
    docker compose logs --tail=20
}

# Main deployment flow
main() {
    echo "=========================================="
    echo "  FIN Production Deployment"
    echo "=========================================="
    echo ""

    cd "$PROJECT_DIR"

    check_requirements
    backup_database
    build_containers
    run_migrations
    start_services
    health_checks
    cleanup

    echo ""
    echo "=========================================="
    log_info "🎉 Deployment successful!"
    echo "=========================================="
    echo ""

    show_status

    echo ""
    log_info "Access the application at:"
    log_info "  - Frontend: http://SERVER_IP or http://localhost"
    log_info "  - API Gateway: http://localhost:8000"
    log_info "  - Transaction Service: http://localhost:8001"
    log_info "  - AI Service: http://localhost:8002"
    echo ""
    log_info "View logs: docker-compose logs -f"
    log_info "Stop services: docker-compose down"
}

# Handle errors
trap 'log_error "Deployment failed at line $LINENO"' ERR

# Run main function
main
