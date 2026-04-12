"""
PRODUCTION-GRADE API GATEWAY - SECURITY HARDENED
Zero tolerance for vulnerabilities.
All endpoints require authentication.
No IDOR vulnerabilities.
"""

import os
import sys
from typing import Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, constr, validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.append("/app")

from shared.audit_logger import audit_logger
from shared.auth_secure import (
    UserContext,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_admin,
    get_current_user,
    hash_password,
    is_admin_email,
    verify_password,
    verify_resource_ownership,
)
from shared.db import get_db
from shared.http_client import default_client, long_timeout_client
from shared.logger import setup_logger
from shared.models import User
from shared.rate_limit_global import GlobalRateLimiter, apply_rate_limit
from shared.redis import client as redis_client
from shared.redis import delete_cache
from shared.schemas import PredictionResponse, TransactionCreate, TransactionResponse
from shared.security_hardening import (
    RateLimitExceeded,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    sanitize_string,
    validate_amount,
)
from shared.startup import validate_startup

# Validate configuration on startup
config = validate_startup()
logger = setup_logger("gateway_secure")

app = FastAPI(
    title="Financial API Gateway - Production",
    version="2.0.0",
    docs_url="/docs" if config.debug else None,  # Disable docs in production
    redoc_url=None,
)

# Add security middleware (ORDER MATTERS)
app.add_middleware(RequestIDMiddleware)  # First: add request ID
app.add_middleware(SecurityHeadersMiddleware)  # Second: add security headers

# CORS configuration - STRICT
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost,http://localhost:80"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
)

# Initialize rate limiter
rate_limiter = GlobalRateLimiter(redis_client)

# Service URLs
TRANSACTIONS_URL = os.getenv("TRANSACTIONS_URL", "http://transactions:8001")
AI_URL = os.getenv("AI_URL", "http://ai:8002")

# Category mapping
CATEGORY_MAP = {
    "food": "Еда",
    "transport": "Транспорт",
    "entertainment": "Развлечения",
    "education": "Образование",
    "salary": "Зарплата",
    "other": "Другое",
}

CATEGORY_ICONS = {
    "food": "🍔",
    "transport": "🚗",
    "entertainment": "🎮",
    "education": "📚",
    "salary": "💰",
    "other": "💸",
    # Russian mappings
    "еда": "🍔",
    "транспорт": "🚗",
    "развлечения": "🎮",
    "образование": "📚",
    "зарплата": "💰",
    "другое": "💸",
}

LEVEL_META = [
    {"name": "Новичок", "icon": "🌱"},
    {"name": "Практик", "icon": "📘"},
    {"name": "Аналитик", "icon": "📊"},
    {"name": "Стратег", "icon": "🧭"},
    {"name": "Эксперт", "icon": "🏆"},
]


def build_level_info(total_xp: int) -> dict:
    level = max(total_xp // 100 + 1, 1)
    current_index = min(level - 1, len(LEVEL_META) - 1)
    next_index = min(level, len(LEVEL_META) - 1)
    current = LEVEL_META[current_index]
    next_level = LEVEL_META[next_index]
    xp_from = max((level - 1) * 100, 0)
    xp_to = level * 100

    return {
        "current": {
            "level": level,
            "name": current["name"],
            "icon": current["icon"],
            "xp_from": xp_from,
            "xp_to": xp_to,
        },
        "next": {
            "level": level + 1,
            "name": next_level["name"],
            "icon": next_level["icon"],
            "xp_from": xp_to,
        },
    }


# ============================================================================
# EXCEPTION HANDLERS - STANDARDIZED ERROR RESPONSES
# ============================================================================


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(f"[{request_id}] Validation error: {exc.errors()}")

    # Convert errors to JSON-serializable format
    errors = []
    for error in exc.errors():
        error_dict = {
            "loc": error.get("loc", []),
            "msg": error.get("msg", ""),
            "type": error.get("type", ""),
        }
        # Handle ctx if present
        if "ctx" in error:
            ctx = error["ctx"]
            if isinstance(ctx, dict):
                error_dict["ctx"] = {k: str(v) for k, v in ctx.items()}
        errors.append(error_dict)

    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Invalid request data",
            "details": errors,
            "request_id": request_id,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "message": exc.detail,
            "request_id": request_id,
        },
        headers=exc.headers,
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": str(exc),
            "request_id": request_id,
        },
        headers={"Retry-After": str(exc.retry_after)},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"[{request_id}] Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "An internal error occurred",
            "request_id": request_id,
        },
    )


# ============================================================================
# PYDANTIC MODELS - INPUT VALIDATION
# ============================================================================


class RegisterRequest(BaseModel):
    email: EmailStr
    name: constr(min_length=2, max_length=100)
    password: constr(min_length=8, max_length=128)

    @validator("password")
    def password_strength(cls, v):
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 900  # 15 minutes
    is_admin: bool = False


class TransactionCreateRequest(BaseModel):
    amount: float = Field(gt=0, le=1_000_000)
    type: str = Field(pattern="^(income|expense)$")
    category: str
    description: Optional[str] = Field(None, max_length=500)
    idempotency_key: Optional[str] = Field(None, max_length=255)

    @validator("amount")
    def validate_amount_field(cls, v):
        return validate_amount(v)

    @validator("description")
    def sanitize_description(cls, v):
        if v:
            return sanitize_string(v, max_length=500)
        return v


# ============================================================================
# PUBLIC ENDPOINTS (NO AUTH REQUIRED)
# ============================================================================


@app.get("/health")
async def health():
    """Health check endpoint - no auth required"""
    return {"status": "ok", "service": "api-gateway", "version": "2.0.0"}


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================


@app.post("/api/auth/register", response_model=AuthResponse)
async def register(
    request: Request, req: RegisterRequest, db: AsyncSession = Depends(get_db)
):
    """Register new user - rate limited"""
    # Rate limit by IP address to prevent registration abuse
    client_ip = request.client.host if request.client else "unknown"
    await apply_rate_limit(request, rate_limiter, "auth:register", client_ip)

    # Sanitize inputs
    email = sanitize_string(req.email, 255).lower()
    name = sanitize_string(req.name, 100)

    # Check if user exists
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(400, "User already exists")

    # Create user with strong password hash
    password_hash = hash_password(req.password)
    user = User(email=email, username=name, password_hash=password_hash, balance=5000.0)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create tokens
    is_admin = is_admin_email(email)
    access_token = create_access_token(user.id, email, is_admin)
    refresh_token = create_refresh_token(user.id, email)

    logger.info(f"New user registered: {email} (id={user.id})")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": 900,
        "is_admin": is_admin,
    }


@app.post("/api/auth/login", response_model=AuthResponse)
async def login(
    request: Request, req: LoginRequest, db: AsyncSession = Depends(get_db)
):
    """Login user - rate limited"""
    await apply_rate_limit(request, rate_limiter, "auth:login", req.email)

    # Find user
    result = await db.execute(select(User).where(User.email == req.email.lower()))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        # Generic error message to prevent user enumeration
        logger.warning(f"Failed login attempt for: {req.email}")

        # Audit log failed login
        request_id = getattr(request.state, "request_id", "unknown")
        await audit_logger.log_auth_failure(
            email=req.email,
            reason="invalid_credentials",
            request_id=request_id,
            ip_address=request.client.host if request.client else None,
        )

        raise HTTPException(401, "Invalid credentials")

    # Create tokens
    is_admin = is_admin_email(user.email)
    access_token = create_access_token(user.id, user.email, is_admin)
    refresh_token = create_refresh_token(user.id, user.email)

    logger.info(f"User logged in: {user.email} (id={user.id})")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": 900,
        "is_admin": is_admin,
    }


@app.post("/api/auth/refresh", response_model=AuthResponse)
async def refresh_token(
    request: Request, req: RefreshRequest, db: AsyncSession = Depends(get_db)
):
    """Refresh access token - rate limited"""
    await apply_rate_limit(request, rate_limiter, "auth:refresh")

    # Decode refresh token
    payload = decode_token(req.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid refresh token")

    user_id = int(payload.get("sub"))
    email = payload.get("email")

    # Verify user still exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(401, "User not found")

    # Create new tokens
    is_admin = is_admin_email(email)
    new_access_token = create_access_token(user_id, email, is_admin)
    new_refresh_token = create_refresh_token(user_id, email)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "Bearer",
        "expires_in": 900,
        "is_admin": is_admin,
    }


# ============================================================================
# TRANSACTION ENDPOINTS - AUTHENTICATION REQUIRED
# ============================================================================


@app.post("/api/transactions")
async def create_transaction(
    request: Request,
    txn: TransactionCreateRequest,
    user: UserContext = Depends(get_current_user),
):
    """
    Create transaction for authenticated user.
    User ID comes from JWT token ONLY.
    """
    await apply_rate_limit(
        request, rate_limiter, "finance:transaction", str(user.user_id)
    )

    request_id = getattr(request.state, "request_id", "unknown")

    # Build transaction data with authenticated user ID
    transaction_data = {
        "user_id": user.user_id,  # FROM JWT, NOT REQUEST
        "amount": txn.amount,
        "type": txn.type,
        "category": txn.category,
        "description": txn.description,
        "idempotency_key": txn.idempotency_key,
    }

    # Use resilient HTTP client with retry
    resp = await default_client.post(
        f"{TRANSACTIONS_URL}/transactions", json=transaction_data, request_id=request_id
    )

    # Check for errors from transaction service
    if resp.status_code != 200:
        error_data = resp.json() if resp.content else {"detail": "Transaction failed"}
        raise HTTPException(
            resp.status_code, error_data.get("detail", "Transaction failed")
        )

    result = resp.json()

    # Map category
    if result.get("category"):
        result["category"] = CATEGORY_MAP.get(result["category"], result["category"])
        result["category_icon"] = CATEGORY_ICONS.get(
            result.get("category", "").lower(), "💰"
        )
    result["comment"] = result.get("description", "")
    result["date"] = result.get("timestamp", "")

    # Invalidate cache
    await delete_cache(f"dashboard:{user.user_id}")

    return result


@app.get("/api/transactions")
async def get_transactions(
    request: Request,
    limit: int = Query(30, ge=1, le=100),
    user: UserContext = Depends(get_current_user),
):
    """
    Get transactions for authenticated user.
    NO userId parameter - uses JWT token.
    """
    await apply_rate_limit(request, rate_limiter, "read:list", str(user.user_id))

    request_id = getattr(request.state, "request_id", "unknown")

    # Use resilient HTTP client with retry
    resp = await default_client.get(
        f"{TRANSACTIONS_URL}/transactions/{user.user_id}?limit={limit}",
        request_id=request_id,
    )
    transactions = resp.json()

    # Map categories
    for txn in transactions:
        if txn.get("category"):
            eng_cat = txn["category"]
            txn["category"] = CATEGORY_MAP.get(eng_cat, eng_cat)
            txn["category_icon"] = CATEGORY_ICONS.get(eng_cat, "💰")
        txn["comment"] = txn.get("description", "")
        txn["date"] = txn.get("timestamp", "")

    return transactions


@app.delete("/api/transactions/{transaction_id}")
async def delete_transaction(
    request: Request, transaction_id: int, user: UserContext = Depends(get_current_user)
):
    """
    Delete transaction - ownership verified by transaction service.
    """
    await apply_rate_limit(
        request, rate_limiter, "finance:transaction", str(user.user_id)
    )

    request_id = getattr(request.state, "request_id", "unknown")

    # Use resilient HTTP client with retry
    resp = await default_client.delete(
        f"{TRANSACTIONS_URL}/transactions/{transaction_id}?user_id={user.user_id}",
        request_id=request_id,
    )

    # Check for errors from transaction service
    if resp.status_code != 200:
        error_data = resp.json() if resp.content else {"detail": "Delete failed"}
        raise HTTPException(resp.status_code, error_data.get("detail", "Delete failed"))

    await delete_cache(f"dashboard:{user.user_id}")

    return resp.json()


# ============================================================================
# TRADE ENDPOINT - AUTHENTICATION REQUIRED
# ============================================================================


@app.post("/api/trade")
async def execute_trade(
    request: Request,
    trade: dict,
    user: UserContext = Depends(get_current_user),
):
    """
    Execute stock trade for authenticated user.
    User ID comes from JWT token ONLY.
    """
    await apply_rate_limit(request, rate_limiter, "finance:trade", str(user.user_id))

    request_id = getattr(request.state, "request_id", "unknown")

    # Forward trade request to transaction service with authenticated user ID
    resp = await default_client.post(
        f"{TRANSACTIONS_URL}/trade/{user.user_id}",
        json=trade,
        request_id=request_id,
    )

    if resp.status_code != 200:
        raise HTTPException(resp.status_code, resp.json().get("detail", "Trade failed"))

    return resp.json()


# ============================================================================
# DASHBOARD ENDPOINT - AUTHENTICATION REQUIRED
# ============================================================================


@app.get("/api/dashboard")
async def get_dashboard(
    request: Request, user: UserContext = Depends(get_current_user)
):
    """
    Get dashboard for authenticated user.
    NO user_id parameter - uses JWT token.
    OPTIMIZED: Parallel requests + caching
    """
    await apply_rate_limit(request, rate_limiter, "read:dashboard", str(user.user_id))

    request_id = getattr(request.state, "request_id", "unknown")

    # Check cache first (30 seconds TTL)
    cache_key = f"dashboard:{user.user_id}"
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            import json
            return json.loads(cached)
    except Exception:
        pass

    # Fetch data in parallel for better performance
    import asyncio
    balance_task = default_client.get(
        f"{TRANSACTIONS_URL}/balance/{user.user_id}", request_id=request_id
    )
    txns_task = default_client.get(
        f"{TRANSACTIONS_URL}/transactions/{user.user_id}?limit=10",
        request_id=request_id,
    )
    pred_task = default_client.get(
        f"{AI_URL}/predict/{user.user_id}", request_id=request_id
    )
    progress_task = default_client.get(
        f"{TRANSACTIONS_URL}/progress",
        params={"userId": str(user.user_id)},
        request_id=request_id,
    )
    achievements_task = default_client.get(
        f"{TRANSACTIONS_URL}/achievements",
        params={"userId": str(user.user_id)},
        request_id=request_id,
    )

    # Wait for all requests in parallel
    results = await asyncio.gather(
        balance_task,
        txns_task,
        pred_task,
        progress_task,
        achievements_task,
        return_exceptions=True,
    )
    balance_resp, txns_resp, pred_resp, progress_resp, achievements_resp = results

    # Handle prediction failure gracefully
    prediction = None
    if not isinstance(pred_resp, Exception):
        try:
            prediction = pred_resp.json()
        except Exception as e:
            logger.warning(f"AI prediction parse error for user {user.user_id}: {e}")

    progress_data = {}
    if not isinstance(progress_resp, Exception):
        try:
            progress_data = progress_resp.json()
        except Exception as e:
            logger.warning(f"Progress parse error for user {user.user_id}: {e}")

    achievements = []
    if not isinstance(achievements_resp, Exception):
        try:
            achievements = achievements_resp.json()
        except Exception as e:
            logger.warning(f"Achievements parse error for user {user.user_id}: {e}")

    balance_data = balance_resp.json()
    transactions = txns_resp.json()

    # FIRST: Map transaction categories to Russian BEFORE any processing
    for txn in transactions:
        if txn.get("category"):
            eng_cat = txn["category"]
            txn["category"] = CATEGORY_MAP.get(eng_cat, eng_cat)
            txn["category_icon"] = CATEGORY_ICONS.get(eng_cat, "💰")
        else:
            txn["category_icon"] = "💰"
        txn["comment"] = txn.get("description", "")
        txn["date"] = txn.get("timestamp", "")

    # NOW: Calculate spending by category (already in Russian)
    spending_chart = []
    category_totals = {}
    total_expenses = 0

    for txn in transactions:
        if txn.get("type") == "expense":
            cat = txn.get("category", "Другое")
            amount = txn.get("amount", 0)
            category_totals[cat] = category_totals.get(cat, 0) + amount
            total_expenses += amount

    for cat, amount in category_totals.items():
        percent = (amount / total_expenses * 100) if total_expenses > 0 else 0
        # Get icon from Russian category name
        icon = "💸"
        for eng, rus in CATEGORY_MAP.items():
            if rus == cat:
                icon = CATEGORY_ICONS.get(eng, "💸")
                break

        spending_chart.append(
            {
                "category": cat,
                "amount": amount,
                "percent": round(percent, 1),
                "icon": icon,
            }
        )

    # Generate AI tips
    ai_tips = []
    if prediction:
        risk = prediction.get("risk_level", "safe")
        if risk == "critical":
            ai_tips.extend(
                ["🚨 Срочно сократите расходы!", "💡 Пересмотрите ежедневные траты"]
            )
        elif risk == "danger":
            ai_tips.extend(
                [
                    "⚠️ Контролируйте бюджет внимательнее",
                    "📊 Проанализируйте крупные расходы",
                ]
            )
        else:
            ai_tips.extend(["✅ Финансы под контролем", "💰 Продолжайте откладывать"])

    # Calculate stats
    categories_used = len(
        set(txn.get("category") for txn in transactions if txn.get("type") == "expense")
    )
    savings_rate = 0
    if balance_data.get("total_income", 0) > 0:
        savings = balance_data.get("total_income", 0) - balance_data.get(
            "total_expenses", 0
        )
        savings_rate = int((savings / balance_data.get("total_income", 1)) * 100)

    unlocked_achievements = [
        achievement for achievement in achievements if achievement.get("unlocked")
    ]
    total_xp = int(progress_data.get("total_xp", 0) or 0)
    level_info = build_level_info(total_xp)

    dashboard = {
        "balance": {"current": balance_data.get("balance", 0)},
        "income": {"month": balance_data.get("total_income", 0)},
        "expenses": {"month": balance_data.get("total_expenses", 0)},
        "transactions": transactions,
        "forecast": None,
        "ai_tips": ai_tips,
        "spending_chart": spending_chart,
        "xp": total_xp,
        "streak": 0,
        "level_info": level_info,
        "stats": {
            "transactions_count": balance_data.get("transaction_count", 0),
            "savings_rate": savings_rate,
            "categories_used": categories_used,
            "achievements": len(unlocked_achievements),
        },
    }

    # Add forecast
    if prediction and prediction.get("days_left"):
        days_left = int(prediction["days_left"])
        daily_avg = (
            int(balance_data.get("balance", 0) / days_left) if days_left > 0 else 0
        )
        dashboard["forecast"] = {"days_left": days_left, "daily_avg": daily_avg}

    # Cache result for 30 seconds
    try:
        import json
        await redis_client.setex(cache_key, 30, json.dumps(dashboard))
    except Exception:
        pass

    return dashboard


# ============================================================================
# AI PREDICTION ENDPOINTS - AUTHENTICATION REQUIRED
# ============================================================================


@app.post("/api/predict")
async def trigger_prediction(
    request: Request, user: UserContext = Depends(get_current_user)
):
    """Trigger AI prediction for authenticated user"""
    await apply_rate_limit(request, rate_limiter, "ai:predict", str(user.user_id))

    request_id = getattr(request.state, "request_id", "unknown")

    resp = await long_timeout_client.post(
        f"{AI_URL}/predict/{user.user_id}", request_id=request_id
    )
    return resp.json()


@app.get("/api/predict")
async def get_prediction(
    request: Request, user: UserContext = Depends(get_current_user)
):
    """Get AI prediction for authenticated user"""
    await apply_rate_limit(request, rate_limiter, "read:dashboard", str(user.user_id))

    request_id = getattr(request.state, "request_id", "unknown")

    resp = await default_client.get(
        f"{AI_URL}/predict/{user.user_id}", request_id=request_id
    )
    if resp.status_code == 404:
        raise HTTPException(404, "No prediction found")
    return resp.json()


# ============================================================================
# ADMIN ENDPOINTS - ADMIN AUTHENTICATION REQUIRED
# ============================================================================


@app.get("/api/admin/users")
async def list_all_users(
    request: Request,
    admin: UserContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin only: List all users"""
    result = await db.execute(select(User).limit(100))
    users = result.scalars().all()

    return [
        {
            "id": u.id,
            "email": u.email,
            "username": u.username,
            "balance": u.balance,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


@app.get("/api/admin/user/{user_id}/dashboard")
async def admin_view_user_dashboard(
    request: Request, user_id: int, admin: UserContext = Depends(get_current_admin)
):
    """Admin only: View any user's dashboard"""
    request_id = getattr(request.state, "request_id", "unknown")

    balance_resp = await default_client.get(
        f"{TRANSACTIONS_URL}/balance/{user_id}", request_id=request_id
    )
    return balance_resp.json()


@app.get("/api/achievements")
async def get_achievements(
    request: Request, user: UserContext = Depends(get_current_user)
):
    """Get user achievements"""
    request_id = getattr(request.state, "request_id", "unknown")

    try:
        resp = await default_client.get(
            f"{TRANSACTIONS_URL}/achievements",
            params={"userId": str(user.user_id)},
            request_id=request_id
        )
        return resp.json()
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch achievements: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch achievements")


@app.get("/api/daily-missions")
async def get_daily_missions(
    request: Request, user: UserContext = Depends(get_current_user)
):
    """Get daily missions"""
    request_id = getattr(request.state, "request_id", "unknown")

    try:
        resp = await default_client.get(
            f"{TRANSACTIONS_URL}/daily-missions",
            params={"userId": str(user.user_id)},
            request_id=request_id
        )
        return resp.json()
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch daily missions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch daily missions")


@app.get("/api/progress")
async def get_progress(
    request: Request, user: UserContext = Depends(get_current_user)
):
    """Get user progress and level"""
    request_id = getattr(request.state, "request_id", "unknown")

    try:
        resp = await default_client.get(
            f"{TRANSACTIONS_URL}/progress",
            params={"userId": str(user.user_id)},
            request_id=request_id
        )
        return resp.json()
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch progress: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch progress")


@app.get("/api/onboarding/questions")
async def get_onboarding_questions(request: Request):
    """Get onboarding questions"""
    request_id = getattr(request.state, "request_id", "unknown")

    try:
        resp = await default_client.get(
            f"{TRANSACTIONS_URL}/onboarding/questions",
            request_id=request_id
        )
        return resp.json()
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch onboarding questions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch onboarding questions")


@app.get("/api/onboarding/status")
async def get_onboarding_status(
    request: Request, userId: str, user: UserContext = Depends(get_current_user)
):
    """Check onboarding status"""
    request_id = getattr(request.state, "request_id", "unknown")

    try:
        resp = await default_client.get(
            f"{TRANSACTIONS_URL}/onboarding/status",
            params={"userId": str(user.user_id)},
            request_id=request_id
        )
        return resp.json()
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch onboarding status: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch onboarding status")


@app.post("/api/onboarding/submit")
async def submit_onboarding(
    request: Request, data: dict, user: UserContext = Depends(get_current_user)
):
    """Submit onboarding answers"""
    request_id = getattr(request.state, "request_id", "unknown")

    try:
        resp = await default_client.post(
            f"{TRANSACTIONS_URL}/onboarding/submit",
            json={"userId": str(user.user_id), "answers": data.get("answers", {})},
            request_id=request_id
        )
        return resp.json()
    except httpx.HTTPError as e:
        logger.error(f"Failed to submit onboarding: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit onboarding")


class AIChatRequest(BaseModel):
    message: str


@app.post("/api/ai-chat")
async def ai_chat(
    request: Request,
    req: AIChatRequest,
    user: UserContext = Depends(get_current_user),
):
    """AI financial chat - proxies to AI service"""
    await apply_rate_limit(request, rate_limiter, "ai:chat", str(user.user_id))
    request_id = getattr(request.state, "request_id", "unknown")

    try:
        resp = await long_timeout_client.post(
            f"{AI_URL}/chat",
            json={"message": req.message, "user_id": user.user_id},
            request_id=request_id,
        )
        return resp.json()
    except httpx.HTTPError as e:
        logger.error(f"AI chat error: {e}")
        raise HTTPException(500, "AI chat unavailable")


@app.get("/api/v2/ai-advice")
async def get_ai_advice(
    request: Request,
    user: UserContext = Depends(get_current_user),
):
    """Get personalized AI advice"""
    request_id = getattr(request.state, "request_id", "unknown")

    try:
        resp = await default_client.get(
            f"{AI_URL}/ai-advice/{user.user_id}",
            request_id=request_id,
        )
        return resp.json()
    except httpx.HTTPError as e:
        logger.error(f"AI advice error: {e}")
        return {"tips": []}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
