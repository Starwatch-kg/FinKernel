#!/bin/bash
# Quick Start Script for Production Deployment

set -e

echo "=========================================="
echo "AI Financial App - Production Setup"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo ""
    echo "Please create .env file:"
    echo "  1. Copy template: cp .env.example .env"
    echo "  2. Generate JWT secret: openssl rand -hex 32"
    echo "  3. Edit .env and set JWT_SECRET_KEY"
    echo "  4. Set ADMIN_EMAILS to your admin email addresses"
    echo ""
    exit 1
fi

# Check if JWT_SECRET_KEY is set
if ! grep -q "^JWT_SECRET_KEY=.\{32,\}" .env; then
    echo "❌ JWT_SECRET_KEY not properly configured!"
    echo ""
    echo "Generate a secure secret:"
    echo "  openssl rand -hex 32"
    echo ""
    echo "Then add it to .env file:"
    echo "  JWT_SECRET_KEY=<your-generated-secret>"
    echo ""
    exit 1
fi

# Check if ADMIN_EMAILS is set
if ! grep -q "^ADMIN_EMAILS=.@." .env; then
    echo "⚠️  Warning: ADMIN_EMAILS not configured"
    echo "   No admin access will be available"
    echo ""
fi

echo "✓ Configuration validated"
echo ""

# Start services
echo "Starting services..."
docker-compose up -d

echo ""
echo "Waiting for services to be healthy..."
sleep 5

# Check service health
echo ""
echo "Checking service health..."

if curl -s http://localhost:8000/health > /dev/null; then
    echo "✓ Gateway (8000) - healthy"
else
    echo "✗ Gateway (8000) - not responding"
fi

if curl -s http://localhost:8001/health > /dev/null; then
    echo "✓ Transaction Service (8001) - healthy"
else
    echo "✗ Transaction Service (8001) - not responding"
fi

if curl -s http://localhost:8002/health > /dev/null; then
    echo "✓ AI Service (8002) - healthy"
else
    echo "✗ AI Service (8002) - not responding"
fi

echo ""
echo "=========================================="
echo "Services started successfully!"
echo "=========================================="
echo ""
echo "API Gateway: http://localhost:8000"
echo "Frontend: http://localhost"
echo ""
echo "View logs: docker-compose logs -f"
echo "Stop services: docker-compose down"
echo ""
