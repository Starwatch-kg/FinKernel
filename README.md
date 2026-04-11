# FinKernel - Lean Microservices

AI финансовый ассистент: **predict when user will run out of money**

## Architecture

```
Gateway (8000) → Transactions (8001) → PostgreSQL
              → AI (8002)             → Redis
              ← Celery Worker
```

## Quick Start

```bash
./start.sh
```

## API

```bash
# Dashboard (cached 30s)
GET /api/dashboard/{user_id}

# Create transaction
POST /api/transactions
{
  "user_id": 1,
  "amount": 100.0,
  "type": "expense",
  "category": "food"
}

# Get prediction
GET /api/predict/{user_id}
```

## AI Engine

**Formula:**
```python
adjusted_spend = 0.6 * rolling_7d + 0.4 * rolling_30d
adjusted_spend *= (1 + trend_slope)
adjusted_spend += volatility * 0.5
days_left = balance / adjusted_spend
```

**Risk levels:**
- critical: ≤ 3 days
- danger: ≤ 7 days
- warning: ≤ 14 days
- safe: > 14 days

## Event Flow

```
Transaction created:
Frontend → Gateway → Transactions → PostgreSQL
→ Redis event → Celery → AI Service → Prediction

Dashboard request:
Frontend → Gateway → Redis cache (HIT: 30ms / MISS: 150ms)
```

## Test

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/dashboard/1
```

---

**Version**: 1.0.0  
**Architecture**: Lean Microservices  
**Status**: Production Ready ✅
