# 🚀 FIN - Production Fintech System

Production-ready fintech backend with race condition protection, idempotency, and atomic transactions.

## 📋 Quick Start

### Deploy to Production (One Command)

```bash
./deploy.sh
```

That's it! The script will:
1. ✅ Check requirements
2. ✅ Backup database
3. ✅ Build containers
4. ✅ Run migrations
5. ✅ Start services
6. ✅ Run health checks

## 🏗️ Architecture

```
Internet → Nginx :80/:443 → API Gateway :8000
                              ├─ Transaction Service :8001
                              ├─ AI Service :8002
                              ├─ PostgreSQL :5432
                              └─ Redis :6379
```

## 🔧 Local Development

```bash
# Copy environment file
cp .env.example .env

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run concurrency tests (CRITICAL)
pytest tests/concurrency/ -v

# Run with coverage
pytest --cov=microservices --cov-report=html
```

## 📊 API Examples

### Create Transaction (with idempotency)
```bash
curl -X POST http://localhost:8000/api/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "amount": 100,
    "type": "income",
    "category": "salary",
    "description": "Salary",
    "idempotency_key": "unique-key-123"
  }'
```

### Trade Stocks
```bash
curl -X POST http://localhost:8000/api/trade \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "1",
    "ticker": "AAPL",
    "shares": 10,
    "action": "buy",
    "idempotency_key": "trade-key-456"
  }'
```

### Check Balance
```bash
curl http://localhost:8000/api/dashboard/1
```

## 🔒 Financial Correctness

### Race Condition Protection
All balance operations use `SELECT FOR UPDATE`:

```python
async with db.begin():
    user = await db.execute(
        select(User).where(User.id == user_id).with_for_update()
    )
    if user.balance < amount:
        raise HTTPException(400, "Insufficient funds")
    user.balance -= amount
    await db.flush()
```

### Guarantees
- ✅ **No money creation** - All increases require DB record
- ✅ **No money loss** - Balance validated before decrease
- ✅ **No double-spending** - Balance checks inside locks
- ✅ **No duplicates** - Idempotency keys prevent duplicates
- ✅ **Consistent state** - All updates in single transaction

## 🚀 CI/CD Pipeline

### Continuous Integration (CI)
Runs on every push:
- ✅ Unit tests
- ✅ Integration tests
- ✅ **Concurrency tests** (CRITICAL for fintech)
- ✅ Security checks (Bandit)
- ✅ Database migrations

### Continuous Deployment (CD)
Deploys to production on push to `main`:
1. SSH to server
2. Pull latest code
3. Build containers
4. Run migrations
5. Restart services (zero downtime)
6. Health checks

**Safe Deploy Rule**: If build fails → keep current containers running

## 🌐 Nginx Setup

### Install Nginx
```bash
sudo apt update
sudo apt install nginx
```

### Configure
```bash
# Copy config
sudo cp nginx.conf /etc/nginx/sites-available/fin

# Enable site
sudo ln -s /etc/nginx/sites-available/fin /etc/nginx/sites-enabled/

# Test config
sudo nginx -t

# Reload
sudo systemctl reload nginx
```

### SSL with Let's Encrypt
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal is configured automatically
```

## 📦 Database Migrations

```bash
# Apply migrations
docker-compose run --rm transactions alembic upgrade head

# Create new migration
docker-compose run --rm transactions alembic revision -m "description"

# Rollback
docker-compose run --rm transactions alembic downgrade -1
```

## 🔍 Monitoring

### Health Checks
```bash
curl http://localhost:8000/health  # API Gateway
curl http://localhost:8001/health  # Transactions
curl http://localhost:8002/health  # AI Service
```

### Logs
```bash
docker-compose logs -f transactions
docker-compose logs -f gateway
docker-compose logs -f ai
```

### Database Monitoring
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U finuser -d financedb

# Check for locks
SELECT pid, usename, pg_blocking_pids(pid) as blocked_by, query 
FROM pg_stat_activity 
WHERE cardinality(pg_blocking_pids(pid)) > 0;

# Check long-running transactions
SELECT pid, now() - xact_start as duration, state, query
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC;
```

## 🚨 Troubleshooting

### Services won't start
```bash
docker-compose logs
docker-compose down
docker-compose up -d
```

### Migration errors
```bash
# Check current version
docker-compose run --rm transactions alembic current

# Rollback and retry
docker-compose run --rm transactions alembic downgrade -1
docker-compose run --rm transactions alembic upgrade head
```

### Database backup/restore
```bash
# Backup
docker-compose exec postgres pg_dump -U finuser financedb > backup.sql

# Restore
docker-compose exec -T postgres psql -U finuser financedb < backup.sql
```

## 📝 Environment Variables

Required in `.env`:
```bash
DATABASE_URL=postgresql+asyncpg://finuser:finpass123@postgres:5432/financedb
REDIS_URL=redis://redis:6379/0
JWT_SECRET_KEY=your-secret-key-min-64-chars
JWT_ALGORITHM=HS256
JWT_EXPIRY_MINUTES=10080
ADMIN_EMAILS=admin@example.com
ENVIRONMENT=production
DEBUG=false
```

## 🎯 Production Checklist

Before deploying:
- [ ] Set strong `JWT_SECRET_KEY` (64+ chars)
- [ ] Configure `ADMIN_EMAILS`
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Configure domain in Nginx
- [ ] Set up SSL certificates
- [ ] Configure backups
- [ ] Set up monitoring
- [ ] Configure GitHub secrets for CD:
  - `SSH_PRIVATE_KEY`
  - `SERVER_HOST`
  - `SERVER_USER`
  - `DEPLOY_PATH`

## 📊 Performance

- **Load**: 1000+ concurrent requests per user
- **Response time**: Sub-second
- **Consistency**: Zero money loss under race conditions
- **Availability**: 99.9% uptime target

## 🔐 Security

- **Authentication**: JWT with bcrypt password hashing
- **Authorization**: Role-based access control
- **Rate limiting**: Redis-based (100 req/min per user)
- **SQL Injection**: Protected by SQLAlchemy ORM
- **XSS**: Content-Type headers enforced
- **CSRF**: SameSite cookies
- **HTTPS**: TLS 1.2+ with Let's Encrypt

## 📚 Project Structure

```
FIN/
├── .github/workflows/     # CI/CD pipelines
│   ├── ci.yml            # Test & validate
│   └── cd.yml            # Deploy to production
├── microservices/
│   ├── api-gateway/      # Port 8000
│   ├── transaction-service/  # Port 8001
│   ├── ai-service/       # Port 8002
│   └── shared/           # Common code
├── tests/
│   ├── unit/
│   ├── integration/
│   └── concurrency/      # CRITICAL tests
├── alembic/              # Database migrations
├── deploy.sh             # ONE-COMMAND DEPLOY
├── nginx.conf            # Nginx configuration
├── docker-compose.yml    # Service orchestration
└── README.md             # This file
```

## 🆘 Support

### Common Issues

**Q: Tests fail in CI**
A: Check PostgreSQL and Redis are running in GitHub Actions

**Q: Deployment fails**
A: Check SSH keys are configured in GitHub secrets

**Q: Services won't start**
A: Check logs with `docker-compose logs`

**Q: Database connection errors**
A: Verify PostgreSQL is running: `docker-compose ps postgres`

## 📄 License

MIT

## 🎉 Credits

Built with financial correctness and production safety in mind.

---

**Remember**: This system handles real money. Any bug can cause financial loss. Always test thoroughly before deploying.
