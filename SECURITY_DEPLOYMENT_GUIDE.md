# 🔒 ENTERPRISE SECURITY HARDENING - DEPLOYMENT GUIDE

## ⚠️ CRITICAL: Pre-Deployment Checklist

### 1. Generate Secure Secrets

```bash
# JWT Secret (minimum 64 characters)
openssl rand -hex 32

# Data Encryption Key
openssl rand -hex 32

# Internal Service Key
openssl rand -urlsafe 32
```

### 2. Update .env.production

Copy `.env.production` and fill in ALL `CHANGE_ME` values with generated secrets.

**NEVER commit .env.production to version control!**

### 3. Database Migration

```bash
# Backup database first!
pg_dump -U finuser financedb > backup_$(date +%Y%m%d).sql

# Run migration
alembic upgrade head
```

---

## 🚀 Deployment Steps

### Step 1: Update Service Files

Replace existing service files with hardened versions:

```bash
# API Gateway
cp microservices/api-gateway/main_hardened.py microservices/api-gateway/main.py

# Transaction Service
cp microservices/transaction-service/main_hardened.py microservices/transaction-service/main.py

# AI Service
cp microservices/ai-service/main_hardened.py microservices/ai-service/main.py

# Database models
cp microservices/shared/models_hardened.py microservices/shared/models.py

# Database config
cp microservices/shared/db_hardened.py microservices/shared/db.py
```

### Step 2: Install New Dependencies

```bash
# Add to requirements.txt
cryptography>=41.0.0
```

### Step 3: Restart Services

```bash
docker-compose down
docker-compose up -d --build
```

### Step 4: Verify Deployment

```bash
# Check health endpoints
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health

# Test authentication
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

---

## 🔐 Security Features Implemented

### 1. JWT V2 Authentication System ✅
- **Access tokens**: 15-minute expiry
- **Refresh tokens**: 7-day expiry with rotation
- **Token blacklisting**: Revoked tokens stored in Redis
- **Replay protection**: Unique JTI (JWT ID) per token
- **Token versioning**: v2 tokens with enhanced security

**Endpoints:**
- `POST /api/register` - Returns access + refresh tokens
- `POST /api/login` - Returns access + refresh tokens
- `POST /api/refresh` - Rotate refresh token, get new access token
- `POST /api/logout` - Blacklist tokens and revoke all refresh tokens

### 2. Role-Based Access Control (RBAC) ✅
- **Roles**: `user`, `admin`, `system`
- **Permissions**: Granular access control
- **Resource ownership verification**: Users can only access their own data
- **Admin privileges**: Configurable via `ADMIN_EMAILS` env var

### 3. Enterprise Audit Logging ✅
- **All events logged**: Auth, data access, trades, admin actions
- **Async logging**: Non-blocking, queued writes
- **Compliance-ready**: Includes IP, user agent, request ID, timestamps
- **Indexed**: Fast queries by user, action, resource, time

**Logged events:**
- Login attempts (success/failure)
- Registration
- Token refresh
- Data access (dashboard, transactions)
- Trades (buy/sell)
- Admin actions

### 4. Anti-Abuse System ✅
- **Rapid trade detection**: Flags burst trading patterns
- **Repeated failure tracking**: Detects brute force attempts
- **Abnormal transaction detection**: Statistical anomaly detection (z-score)
- **Velocity limiting**: Per-action rate limits
- **Temporary user blocking**: Auto-block on abuse detection
- **User flagging**: Mark suspicious accounts for review

### 5. Service-to-Service Authentication ✅
- **Internal API keys**: Each service validates `X-Internal-Service-Key` header
- **Zero-trust architecture**: No implicit trust between services
- **Enforced on all internal endpoints**

### 6. AI Output Validation ✅
- **Strict schema validation**: Pydantic models with constraints
- **Confidence thresholds**: Reject low-confidence predictions (< 0.6)
- **Prompt injection detection**: Scans for dangerous patterns
- **Safe fallback**: Statistical model when AI fails
- **Transparency flags**: `ai_used` and `ai_confidence` in responses

### 7. Network Security ✅
- **HTTPS redirect**: HTTP → HTTPS in production
- **Trusted hosts**: Whitelist valid domains
- **Security headers**: CSP, HSTS, X-Frame-Options, etc.
- **IP rate limiting**: Global rate limit per IP
- **Request size limits**: Max 1MB request body
- **Content-Type validation**: Only allow safe content types

### 8. Request Hardening ✅
- **Size limits**: 1MB max request body
- **Content-Type validation**: Strict whitelist
- **JSON validation**: Safe parsing with error handling
- **Early rejection**: Invalid requests fail fast

### 9. Database Security ✅
- **Check constraints**: Enforce data integrity
  - `balance >= 0`
  - `amount > 0`
  - `shares > 0`
  - `confidence BETWEEN 0 AND 1`
- **Row-level locking**: `with_for_update()` on critical operations
- **Transaction isolation**: `REPEATABLE READ` level
- **Cascade deletes**: Proper foreign key constraints
- **Optimized indexes**: Fast queries on user_id + timestamp

### 10. Data Encryption ✅
- **Application-level encryption**: Sensitive fields encrypted at rest
- **Fernet encryption**: Industry-standard symmetric encryption
- **Key derivation**: PBKDF2 with 100k iterations
- **Configurable**: `ENCRYPTION_KEY` environment variable

### 11. Anti-Replay Protection ✅
- **Unique JTI**: Every token has unique identifier
- **Blacklist checking**: All requests check token blacklist
- **Token rotation**: Refresh tokens invalidated on use

### 12. Fail-Safe Design ✅
- **AI failure → statistical fallback**: System continues with reduced functionality
- **Redis failure → logged, degraded mode**: Rate limiting fails open
- **DB failure → controlled shutdown**: Proper error handling
- **All failures audited**: Logged for investigation

---

## 🔍 Testing Security Features

### Test JWT V2 Flow

```bash
# 1. Register
RESPONSE=$(curl -s -X POST http://localhost:8000/api/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","name":"Test User","password":"Test123456"}')

ACCESS_TOKEN=$(echo $RESPONSE | jq -r '.access_token')
REFRESH_TOKEN=$(echo $RESPONSE | jq -r '.refresh_token')

# 2. Access protected endpoint
curl -H "Authorization: Bearer $ACCESS_TOKEN" \
  http://localhost:8000/api/dashboard/1

# 3. Refresh token
NEW_TOKENS=$(curl -s -X POST http://localhost:8000/api/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH_TOKEN\"}")

# 4. Logout (blacklist tokens)
curl -X POST http://localhost:8000/api/logout \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# 5. Try using old token (should fail)
curl -H "Authorization: Bearer $ACCESS_TOKEN" \
  http://localhost:8000/api/dashboard/1
```

### Test Rate Limiting

```bash
# Rapid requests should trigger rate limit
for i in {1..100}; do
  curl -s http://localhost:8000/api/dashboard/1 \
    -H "Authorization: Bearer $TOKEN" &
done
```

### Test RBAC

```bash
# User trying to access another user's data (should fail)
curl -H "Authorization: Bearer $USER_TOKEN" \
  http://localhost:8000/api/dashboard/999
```

### Query Audit Logs

```sql
-- Recent login attempts
SELECT user_id, email, status, ip_address, timestamp
FROM audit_logs
WHERE action = 'login'
ORDER BY timestamp DESC
LIMIT 10;

-- Failed auth attempts by IP
SELECT ip_address, COUNT(*) as attempts
FROM audit_logs
WHERE action = 'login' AND status = 'failed'
GROUP BY ip_address
HAVING COUNT(*) > 5;

-- User activity timeline
SELECT action, resource, status, timestamp
FROM audit_logs
WHERE user_id = 1
ORDER BY timestamp DESC;
```

---

## 📊 Monitoring & Alerts

### Key Metrics to Monitor

1. **Failed login rate**: Spike indicates brute force attack
2. **Token blacklist size**: Growing rapidly = potential issue
3. **Audit log volume**: Baseline for anomaly detection
4. **Rate limit hits**: High rate = potential DoS
5. **AI fallback rate**: High rate = AI service issues

### Redis Keys to Monitor

```bash
# Check blacklisted tokens
redis-cli KEYS "blacklist:*"

# Check blocked users
redis-cli KEYS "blocked_user:*"

# Check flagged users
redis-cli KEYS "flagged_user:*"

# Check rate limits
redis-cli KEYS "rate:*"
```

---

## 🚨 Incident Response

### Compromised Token

```bash
# Revoke all tokens for user
# (Implement admin endpoint or direct Redis access)
redis-cli KEYS "refresh_token:USER_ID:*" | xargs redis-cli DEL
```

### Suspicious Activity

```sql
-- Check audit logs
SELECT * FROM audit_logs
WHERE user_id = ? AND timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;
```

### Block User

```python
from shared.anti_abuse import AnomalyDetector
detector = AnomalyDetector(redis_client)
await detector.block_user_temporarily(user_id, duration=3600, reason="manual_block")
```

---

## 📝 Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET_KEY` | ✅ | - | JWT signing key (min 64 chars) |
| `ENCRYPTION_KEY` | ✅ | - | Data encryption key |
| `INTERNAL_SERVICE_KEY` | ✅ | - | Service-to-service auth |
| `ADMIN_EMAILS` | ✅ | - | Comma-separated admin emails |
| `ALLOWED_ORIGINS` | ✅ | - | CORS origins (no wildcards) |
| `TRUSTED_HOSTS` | ⚠️ | localhost | Trusted host domains |
| `HTTPS_REDIRECT_ENABLED` | ⚠️ | false | Enable HTTPS redirect |
| `ENVIRONMENT` | ⚠️ | development | production/development |

---

## ✅ Security Checklist

- [ ] All secrets generated and configured
- [ ] Database migration applied
- [ ] Audit logging verified
- [ ] HTTPS enabled in production
- [ ] CORS configured (no wildcards)
- [ ] Admin emails configured
- [ ] Internal service keys set
- [ ] Rate limits tested
- [ ] Token refresh flow tested
- [ ] Audit logs queryable
- [ ] Monitoring alerts configured
- [ ] Incident response plan documented
- [ ] Backup strategy in place

---

## 🎯 Attack Resistance

System now resists:

✅ **Token theft** - Short-lived tokens, rotation, blacklisting  
✅ **Replay attacks** - Unique JTI, blacklist checking  
✅ **IDOR** - Resource ownership verification  
✅ **Race conditions** - Row-level locking, transaction isolation  
✅ **Prompt injection** - AI output validation, pattern detection  
✅ **Brute force** - Rate limiting, repeated failure detection  
✅ **Internal service compromise** - Service-to-service auth  
✅ **SQL injection** - Parameterized queries, ORM  
✅ **XSS** - Security headers, CSP  
✅ **CSRF** - Token-based auth (no cookies)  
✅ **DoS** - Rate limiting, request size limits  
✅ **Data tampering** - Check constraints, validation  

---

## 📞 Support

For security issues, contact: security@yourdomain.com

**DO NOT** disclose security vulnerabilities publicly.
