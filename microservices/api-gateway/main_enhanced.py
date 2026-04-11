"""Enhanced API Gateway with full observability and security"""
from fastapi import FastAPI, HTTPException, Header, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, EmailStr, constr, validator
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
import sys
import uuid
import os
sys.path.append('/app')

from shared.redis import get_cache, set_cache, delete_cache, client as redis_client
from shared.schemas import TransactionCreate, TransactionResponse, PredictionResponse, DashboardResponse
from shared.db import get_db
from shared.models import User
from shared.startup import validate_startup
from shared.logger import setup_logger
from shared.auth import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    decode_token, store_refresh_token, validate_refresh_token, revoke_refresh_token,
    blacklist_token, is_token_blacklisted, is_admin_email
)
from shared.security import sanitize_string, sanitize_dict
from shared.rate_limiter import SlidingWindowRateLimiter, get_rate_limit_config
from shared.circuit_breaker import get_circuit_breaker, CircuitBreakerError
from shared.retry import retry_with_backoff
from shared.metrics import PrometheusMiddleware, metrics_endpoint
from shared.tracing import setup_tracing

config = validate_startup()
logger = setup_logger("gateway")

app = FastAPI(title="Gateway")

# Setup tracing
tracer = setup_tracing("api-gateway", app)

# Add Prometheus middleware
app.add_middleware(PrometheusMiddleware)

# Request ID Middleware
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        return response

app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# CORS
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost,http://localhost:80,http://localhost:3000,http://localhost:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Rate limiter
rate_limiter = SlidingWindowRateLimiter(redis_client)

# Circuit breakers
ai_circuit_breaker = get_circuit_breaker("ai-service", failure_threshold=5, recovery_timeout=60.0)
txn_circuit_breaker = get_circuit_breaker("transaction-service", failure_threshold=5, recovery_timeout=30.0)

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Invalid request data",
            "details": exc.errors(),
            "request_id": getattr(request.state, "request_id", None)
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "message": exc.detail,
            "request_id": getattr(request.state, "request_id", None)
        }
    )

@app.exception_handler(CircuitBreakerError)
async def circuit_breaker_exception_handler(request: Request, exc: CircuitBreakerError):
    return JSONResponse(
        status_code=503,
        content={
            "error": "service_unavailable",
            "message": str(exc),
            "request_id": getattr(request.state, "request_id", None)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "An internal error occurred",
            "request_id": getattr(request.state, "request_id", None)
        }
    )

TRANSACTIONS_URL = os.getenv("TRANSACTIONS_URL", "http://transactions:8001")
AI_URL = os.getenv("AI_URL", "http://ai:8002")

CATEGORY_MAP = {
    "food": "Еда",
    "transport": "Транспорт",
    "entertainment": "Развлечения",
    "education": "Образование",
    "salary": "Зарплата",
    "other": "Другое"
}

CATEGORY_ICONS = {
    "food": "🍔",
    "transport": "🚗",
    "entertainment": "🎮",
    "education": "📚",
    "salary": "💰",
    "other": "💸"
}

# Auth schemas
class RegisterRequest(BaseModel):
    email: EmailStr
    name: constr(min_length=2, max_length=100)
    password: constr(min_length=8, max_length=128)

    @validator('password')
    def password_strength(cls, v):
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c.isalpha() for c in v):
            raise ValueError('Password must contain at least one letter')
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    is_admin: bool = False

class RefreshRequest(BaseModel):
    refresh_token: str

@app.get("/health")
async def health():
    return {"status": "ok", "service": "api-gateway"}

@app.get("/metrics")
async def metrics(request: Request):
    return await metrics_endpoint(request)

# Auth endpoints
@app.post("/api/register", response_model=AuthResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    config = get_rate_limit_config("auth:register")
    allowed, info = await rate_limiter.check_rate_limit("auth:register", config["max_requests"], config["window"], req.email)
    if not allowed:
        raise HTTPException(429, f"Too many registration attempts. Try again in {info['retry_after']}s")

    # Sanitize inputs
    email = sanitize_string(req.email, 255)
    name = sanitize_string(req.name, 100)

    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(400, "User already exists")

    password_hash = hash_password(req.password)
    user = User(email=email, username=name, password_hash=password_hash, balance=5000.0)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    is_admin = is_admin_email(email)
    access_token = create_access_token(user.id, email, is_admin)
    refresh_token = create_refresh_token(user.id, email)

    await store_refresh_token(redis_client, user.id, refresh_token)

    return {"access_token": access_token, "refresh_token": refresh_token, "is_admin": is_admin}

@app.post("/api/login", response_model=AuthResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    config = get_rate_limit_config("auth:login")
    allowed, info = await rate_limiter.check_rate_limit("auth:login", config["max_requests"], config["window"], req.email)
    if not allowed:
        raise HTTPException(429, f"Too many login attempts. Try again in {info['retry_after']}s")

    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")

    is_admin = is_admin_email(req.email)
    access_token = create_access_token(user.id, req.email, is_admin)
    refresh_token = create_refresh_token(user.id, req.email)

    await store_refresh_token(redis_client, user.id, refresh_token)

    return {"access_token": access_token, "refresh_token": refresh_token, "is_admin": is_admin}

@app.post("/api/refresh", response_model=AuthResponse)
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    config = get_rate_limit_config("auth:refresh")
    allowed, info = await rate_limiter.check_rate_limit("auth:refresh", config["max_requests"], config["window"])
    if not allowed:
        raise HTTPException(429, f"Too many refresh attempts. Try again in {info['retry_after']}s")

    payload = decode_token(req.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid refresh token")

    user_id = payload.get("user_id")
    email = payload.get("email")

    if not await validate_refresh_token(redis_client, user_id, req.refresh_token):
        raise HTTPException(401, "Refresh token revoked or expired")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    is_admin = is_admin_email(email)
    new_access_token = create_access_token(user_id, email, is_admin)
    new_refresh_token = create_refresh_token(user_id, email)

    await revoke_refresh_token(redis_client, user_id, req.refresh_token)
    await store_refresh_token(redis_client, user_id, new_refresh_token)

    return {"access_token": new_access_token, "refresh_token": new_refresh_token, "is_admin": is_admin}

@app.post("/api/logout")
async def logout(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid authorization header")

    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Invalid token")

    user_id = payload.get("user_id")
    exp = payload.get("exp")
    ttl = max(exp - int(datetime.utcnow().timestamp()), 0) if exp else 900

    await blacklist_token(redis_client, token, ttl)

    return {"message": "Logged out successfully"}

# Proxy endpoints with circuit breaker
async def call_service_with_protection(url: str, circuit_breaker, timeout: float = 5.0, method: str = "GET", **kwargs):
    """Call service with circuit breaker and retry"""
    async def make_request():
        async with httpx.AsyncClient(timeout=timeout) as client:
            if method == "GET":
                resp = await client.get(url, **kwargs)
            elif method == "POST":
                resp = await client.post(url, **kwargs)
            elif method == "DELETE":
                resp = await client.delete(url, **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")
            resp.raise_for_status()
            return resp

    return await circuit_breaker.call(
        retry_with_backoff,
        make_request,
        max_retries=2,
        base_delay=0.5,
        exceptions=(httpx.HTTPError,)
    )

@app.post("/api/transactions")
async def create_transaction(txn: TransactionCreate):
    config = get_rate_limit_config("api:transaction")
    allowed, info = await rate_limiter.check_rate_limit("api:transaction", config["max_requests"], config["window"], str(txn.user_id))
    if not allowed:
        raise HTTPException(429, f"Rate limit exceeded. Try again in {info['retry_after']}s")

    resp = await call_service_with_protection(
        f"{TRANSACTIONS_URL}/transactions",
        txn_circuit_breaker,
        method="POST",
        json=txn.model_dump(mode='json')
    )
    result = resp.json()

    if result.get("category"):
        result["category"] = CATEGORY_MAP.get(result["category"], result["category"])
        result["category_icon"] = CATEGORY_ICONS.get(result.get("category", "").lower(), "💰")
    result["comment"] = result.get("description", "")
    result["date"] = result.get("timestamp", "")

    await delete_cache(f"dashboard:{txn.user_id}")
    return result

@app.get("/api/dashboard/{user_id}")
async def get_dashboard(user_id: int):
    cache_key = f"dashboard:{user_id}"
    cached = await get_cache(cache_key)
    if cached:
        return cached

    balance_resp = await call_service_with_protection(f"{TRANSACTIONS_URL}/balance/{user_id}", txn_circuit_breaker)
    txns_resp = await call_service_with_protection(f"{TRANSACTIONS_URL}/transactions/{user_id}?limit=10", txn_circuit_breaker)

    try:
        pred_resp = await call_service_with_protection(f"{AI_URL}/predict/{user_id}", ai_circuit_breaker, timeout=10.0)
        prediction = pred_resp.json()
    except Exception as e:
        logger.warning(f"AI prediction unavailable: {e}")
        prediction = None

    balance_data = balance_resp.json()
    transactions = txns_resp.json()

    spending_chart = []
    category_totals = {}
    for txn in transactions:
        if txn.get("type") == "expense":
            cat = txn.get("category", "other")
            category_totals[cat] = category_totals.get(cat, 0) + txn.get("amount", 0)

    for cat, amount in category_totals.items():
        spending_chart.append({
            "category": CATEGORY_MAP.get(cat, cat),
            "amount": amount,
            "icon": CATEGORY_ICONS.get(cat, "💸")
        })

    ai_tips = []
    if prediction:
        risk = prediction.get("risk_level", "safe")
        if risk == "critical":
            ai_tips.extend(["🚨 Срочно сократите расходы!", "💡 Пересмотрите ежедневные траты"])
        elif risk == "danger":
            ai_tips.extend(["⚠️ Контролируйте бюджет внимательнее", "📊 Проанализируйте крупные расходы"])
        else:
            ai_tips.extend(["✅ Финансы под контролем", "💰 Продолжайте откладывать"])

    categories_used = len(set(txn.get("category") for txn in transactions if txn.get("type") == "expense"))
    savings_rate = 0
    if balance_data.get("total_income", 0) > 0:
        savings = balance_data.get("total_income", 0) - balance_data.get("total_expenses", 0)
        savings_rate = int((savings / balance_data.get("total_income", 1)) * 100)

    dashboard = {
        "balance": {"current": balance_data.get("balance", 0)},
        "income": {"month": balance_data.get("total_income", 0)},
        "expenses": {"month": balance_data.get("total_expenses", 0)},
        "transactions": transactions,
        "forecast": None,
        "ai_tips": ai_tips,
        "spending_chart": spending_chart,
        "stats": {
            "transactions_count": balance_data.get("transaction_count", 0),
            "savings_rate": savings_rate,
            "categories_used": categories_used,
            "achievements": 0
        }
    }

    if prediction and prediction.get("days_left"):
        days_left = int(prediction["days_left"])
        daily_avg = int(balance_data.get("balance", 0) / days_left) if days_left > 0 else 0
        dashboard["forecast"] = {"days_left": days_left, "daily_avg": daily_avg}

    await set_cache(cache_key, dashboard, ttl=60)
    return dashboard

# Keep all other proxy endpoints...
@app.get("/api/transactions")
async def get_transactions(userId: str, limit: int = 30):
    user_id = int(userId) if userId.isdigit() else 1
    resp = await call_service_with_protection(f"{TRANSACTIONS_URL}/transactions/{user_id}?limit={limit}", txn_circuit_breaker)
    transactions = resp.json()
    for txn in transactions:
        if txn.get("category"):
            eng_cat = txn["category"]
            txn["category"] = CATEGORY_MAP.get(eng_cat, eng_cat)
            txn["category_icon"] = CATEGORY_ICONS.get(eng_cat, "💰")
        txn["comment"] = txn.get("description", "")
        txn["date"] = txn.get("timestamp", "")
    return transactions

@app.delete("/api/transactions/{transaction_id}")
async def delete_transaction(transaction_id: int, userId: str):
    user_id = int(userId) if userId.isdigit() else 1
    resp = await call_service_with_protection(
        f"{TRANSACTIONS_URL}/transactions/{transaction_id}?userId={user_id}",
        txn_circuit_breaker,
        method="DELETE"
    )
    await delete_cache(f"dashboard:{user_id}")
    return resp.json()

# Additional proxy endpoints (abbreviated for space)
@app.post("/api/predict/{user_id}", response_model=PredictionResponse)
async def trigger_prediction(user_id: int):
    resp = await call_service_with_protection(f"{AI_URL}/predict/{user_id}", ai_circuit_breaker, timeout=10.0, method="POST")
    return resp.json()

@app.get("/api/predict/{user_id}", response_model=PredictionResponse)
async def get_prediction(user_id: int):
    resp = await call_service_with_protection(f"{AI_URL}/predict/{user_id}", ai_circuit_breaker)
    return resp.json()
