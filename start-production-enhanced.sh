#!/bin/bash
set -e

echo "🚀 Starting FIN Production System with Full Observability"
echo "=========================================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "📝 Copy .env.example to .env and configure it:"
    echo "   cp .env.example .env"
    exit 1
fi

# Validate JWT secret
JWT_SECRET=$(grep JWT_SECRET_KEY .env | cut -d '=' -f2)
if [ "$JWT_SECRET" == "CHANGE_ME_GENERATE_WITH_OPENSSL_RAND_HEX_32" ] || [ -z "$JWT_SECRET" ]; then
    echo "❌ Error: JWT_SECRET_KEY not configured"
    echo "🔐 Generate a secure secret:"
    echo "   openssl rand -hex 32"
    exit 1
fi

echo "✅ Configuration validated"
echo ""

# Build and start services
echo "🐳 Building Docker images..."
docker-compose build

echo ""
echo "🚀 Starting services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service health
echo ""
echo "🏥 Health Check:"
echo "  Gateway:      $(curl -s http://localhost:8000/health | jq -r '.status' 2>/dev/null || echo 'NOT READY')"
echo "  Transactions: $(curl -s http://localhost:8001/health | jq -r '.status' 2>/dev/null || echo 'NOT READY')"
echo "  AI Service:   $(curl -s http://localhost:8002/health | jq -r '.status' 2>/dev/null || echo 'NOT READY')"

echo ""
echo "📊 Observability Stack:"
echo "  Jaeger UI:    http://localhost:16686"
echo "  Prometheus:   http://localhost:9090"
echo "  Grafana:      http://localhost:3000 (admin/admin)"

echo ""
echo "🎯 Application:"
echo "  Frontend:     http://localhost"
echo "  API Gateway:  http://localhost:8000"
echo "  API Docs:     http://localhost:8000/docs"

echo ""
echo "📈 Metrics Endpoints:"
echo "  Gateway:      http://localhost:8000/metrics"
echo "  Transactions: http://localhost:8001/metrics"
echo "  AI Service:   http://localhost:8002/metrics"

echo ""
echo "✅ System started successfully!"
echo ""
echo "📝 View logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 Stop system:"
echo "   docker-compose down"
