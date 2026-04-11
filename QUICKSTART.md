# Quick Start Guide

## 1. Setup (First Time)

```bash
# Copy environment template
cp .env.example .env

# Generate secure JWT secret
openssl rand -hex 32

# Edit .env and paste the JWT secret
nano .env  # or vim, code, etc.
```

## 2. Start System

```bash
# Make script executable
chmod +x start-production-enhanced.sh

# Start everything
./start-production-enhanced.sh
```

## 3. Access Services

- **Frontend**: http://localhost
- **API Docs**: http://localhost:8000/docs
- **Jaeger (Tracing)**: http://localhost:16686
- **Prometheus (Metrics)**: http://localhost:9090
- **Grafana (Dashboards)**: http://localhost:3000 (admin/admin)

## 4. Test the System

```bash
# Register a user
curl -X POST http://localhost:8000/api/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","name":"Test User","password":"password123"}'

# Login
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Check metrics
curl http://localhost:8000/metrics
```

## 5. View Traces

1. Open http://localhost:16686
2. Select service: "api-gateway"
3. Click "Find Traces"
4. See full request flow across services

## 6. View Metrics

1. Open http://localhost:9090
2. Try queries:
   - `http_requests_total`
   - `http_request_duration_seconds`
   - `rate(http_requests_total[5m])`

## 7. Stop System

```bash
docker-compose down
```

## Key Features Enabled

✅ Distributed tracing across all services
✅ Prometheus metrics on all endpoints
✅ JWT refresh tokens (15min access, 7day refresh)
✅ Rate limiting (per-endpoint, per-user)
✅ Circuit breakers (AI + Transaction services)
✅ Retry with exponential backoff
✅ Security headers (CSP, HSTS, etc.)
✅ Input sanitization
✅ Request ID tracking
✅ Structured JSON logging

## Troubleshooting

**Services not starting?**
```bash
docker-compose logs -f
```

**Database issues?**
```bash
docker-compose exec postgres psql -U finuser -d financedb
```

**Redis issues?**
```bash
docker-compose exec redis redis-cli ping
```

**Reset everything?**
```bash
docker-compose down -v
docker-compose up -d
```
