#!/bin/bash
set -e

echo "🚀 Starting Financial AI Assistant..."
echo ""

if ! command -v docker &> /dev/null; then
    echo "❌ Docker not installed"
    exit 1
fi

echo "🧹 Cleaning old containers..."
docker-compose down 2>/dev/null || true

echo "🐳 Building and starting services..."
docker-compose up -d --build

echo "⏳ Waiting for PostgreSQL..."
sleep 8

echo "📊 Initializing database..."
docker exec fin_transactions python -c "
import sys
sys.path.append('/app')
from shared.init_db import init_db
import asyncio
asyncio.run(init_db())
" 2>/dev/null || echo "⚠️  DB already initialized"

echo "🌱 Seeding test data..."
docker exec fin_transactions python -c "
import sys
sys.path.append('/app')
from shared.seed_db import seed
import asyncio
asyncio.run(seed())
" 2>/dev/null || echo "⚠️  Data already seeded"

echo ""
echo "✅ All services running!"
echo ""
echo "📍 Services:"
echo "   Gateway:      http://localhost:8000"
echo "   Transactions: http://localhost:8001"
echo "   AI Service:   http://localhost:8002"
echo "   PostgreSQL:   localhost:5432"
echo "   Redis:        localhost:6379"
echo ""
echo "🧪 Test:"
echo "   curl http://localhost:8000/health"
echo "   curl http://localhost:8000/api/dashboard/1"
echo ""
echo "📝 Commands:"
echo "   Logs:  docker-compose logs -f"
echo "   Stop:  docker-compose down"
echo ""
