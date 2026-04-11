"""API Gateway - Enterprise Security Hardened Version"""
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

from shared.redis import get_cache, set_cache, delete_cache
from shared.db import get_db, async_session
from shared.models import User
from shared.startup import validate_startup
from shared.logger import setup_logger
from shared.auth_v2 import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    decode_token, store_refresh_token, rotate_refresh_token, blacklist_token,
    determine_role, is_token_blacklisted
)
from shared.rbac import extract_and_validate_token, verify_resource_ownership, Role
from shared.audit import audit_logger, get_client_ip, get_request_id
from shared.anti_abuse import AnomalyDetector
from shared.network_security import HTTPSRedirectMiddleware, get_trusted_hosts
from shared.request_validation import RequestSizeLimitMiddleware, ContentTypeValidationMiddleware
from shared.redis import client as redis_client

config = validate_startup()
logger = setup_logger("gateway_hardened")

# Middleware classes
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        request.state.redis = redis_client
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


app = FastAPI(title="Gateway-Hardened")

# Add security middleware (order matters!)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_size=1_048_576)
app.add_middleware(ContentTypeValidationMiddleware)

# HTTPS redirect in production
if os.getenv("ENVIRONMENT") == "production":
    app.add_middleware(HTTPSRedirectMiddleware, enabled=True)

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
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes


class RefreshRequest(BaseModel):
    refresh_token: str


# CORS configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-Request-ID"]
)

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


TRANSACTIONS_URL = "http://transactions:8001"
AI_URL = "http://ai:8002"
INTERNAL_SERVICE_KEY = os.getenv("INTERNAL_SERVICE_KEY", "")


@app.on_event("startup")
async def startup_event():
    """Start audit logger worker"""
    import asyncio
    asyncio.create_task(audit_logger.start_worker(async_session))
    logger.info("Audit logger worker started")


@app.get("/health")
async def health():
    return {"status": "ok"}


# Auth endpoints with V2 tokens
@app.post("/api/register", response_model=AuthResponse)
async def register(req: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ip_address = await get_client_ip(request)
    request_id = await get_request_id(request)

    # Rate limit registration
    detector = AnomalyDetector(redis_client)
    if not await detector.check_velocity(0, f"register:{req.email}", max_per_minute=3):
        await audit_logger.log_auth("register", "rate_limited", email=req.email, ip_address=ip_address, request_id=request_id)
        raise HTTPException(429, "Too many registration attempts")

    # Check if user exists
    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        await audit_logger.log_auth("register", "failed", email=req.email, ip_address=ip_address, request_id=request_id, reason="user_exists")
        raise HTTPException(400, "User already exists")

    # Create user
    password_hash = hash_password(req.password)
    user = User(
        email=req.email,
        username=req.name,
        password_hash=password_hash,
        balance=5000.0
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create tokens
    role = determine_role(req.email)
    access_token = create_access_token(user.id, req.email, role)
    refresh_token = create_refresh_token(user.id, req.email)

    # Store refresh token
    refresh_payload = decode_token(refresh_token)
    await store_refresh_token(redis_client, user.id, refresh_token, refresh_payload["jti"])

    await audit_logger.log_auth("register", "success", user_id=user.id, email=req.email, ip_address=ip_address, request_id=request_id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 900
    }


@app.post("/api/login", response_model=AuthResponse)
async def login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ip_address = await get_client_ip(request)
    request_id = await get_request_id(request)

    # Rate limit login attempts
    detector = AnomalyDetector(redis_client)
    if not await detector.check_velocity(0, f"login:{req.email}", max_per_minute=5):
        await audit_logger.log_auth("login", "rate_limited", email=req.email, ip_address=ip_address, request_id=request_id)
        raise HTTPException(429, "Too many login attempts")

    # Find user
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if not user:
        await detector.check_repeated_failures(0, f"login:{req.email}")
        await audit_logger.log_auth("login", "failed", email=req.email, ip_address=ip_address, request_id=request_id, reason="user_not_found")
        raise HTTPException(404, "User not found")

    # Check if user is blocked
    block_info = await detector.is_user_blocked(user.id)
    if block_info:
        await audit_logger.log_auth("login", "blocked", user_id=user.id, email=req.email, ip_address=ip_address, request_id=request_id)
        raise HTTPException(403, f"Account temporarily blocked: {block_info['reason']}")

    # Verify password
    if not verify_password(req.password, user.password_hash):
        await detector.check_repeated_failures(user.id, "login")
        await audit_logger.log_auth("login", "failed", user_id=user.id, email=req.email, ip_address=ip_address, request_id=request_id, reason="invalid_password")
        raise HTTPException(401, "Invalid password")

    # Create tokens
    role = determine_role(req.email)
    access_token = create_access_token(user.id, req.email, role)
    refresh_token = create_refresh_token(user.id, req.email)

    # Store refresh token
    refresh_payload = decode_token(refresh_token)
    await store_refresh_token(redis_client, user.id, refresh_token, refresh_payload["jti"])

    await audit_logger.log_auth("login", "success", user_id=user.id, email=req.email, ip_address=ip_address, request_id=request_id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 900
    }


@app.post("/api/refresh", response_model=AuthResponse)
async def refresh_token_endpoint(req: RefreshRequest, request: Request):
    """Rotate refresh token and issue new access token"""
    ip_address = await get_client_ip(request)
    request_id = await get_request_id(request)

    new_access, new_refresh = await rotate_refresh_token(redis_client, req.refresh_token)

    if not new_access or not new_refresh:
        await audit_logger.log_auth("refresh", "failed", ip_address=ip_address, request_id=request_id, reason="invalid_token")
        raise HTTPException(401, "Invalid or expired refresh token")

    payload = decode_token(new_access)
    await audit_logger.log_auth("refresh", "success", user_id=payload.get("user_id"), ip_address=ip_address, request_id=request_id)

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
        "expires_in": 900
    }


@app.post("/api/logout")
async def logout(request: Request, authorization: str = Header(None)):
    """Logout and blacklist tokens"""
    ip_address = await get_client_ip(request)
    request_id = await get_request_id(request)

    payload = await extract_and_validate_token(authorization, redis_client)
    user_id = payload.get("user_id")
    jti = payload.get("jti")

    # Blacklist access token
    if jti:
        await blacklist_token(redis_client, jti, 900)  # 15 min TTL

    # Revoke all refresh tokens for user
    from shared.auth_v2 import revoke_all_user_tokens
    await revoke_all_user_tokens(redis_client, user_id)

    await audit_logger.log_auth("logout", "success", user_id=user_id, ip_address=ip_address, request_id=request_id)

    return {"status": "logged_out"}


# Protected endpoint example
@app.get("/api/dashboard/{user_id}")
async def get_dashboard(
    user_id: int,
    request: Request,
    authorization: str = Header(None)
):
    """Get user dashboard with RBAC and audit logging"""
    ip_address = await get_client_ip(request)
    request_id = await get_request_id(request)

    # Validate token and check blacklist
    payload = await extract_and_validate_token(authorization, redis_client)
    token_user_id = payload.get("user_id")
    role = payload.get("role", Role.USER)

    # Verify resource ownership
    if not verify_resource_ownership(token_user_id, user_id, role):
        await audit_logger.log_data_access(token_user_id, "dashboard", str(user_id), "read", "forbidden", ip_address, request_id)
        raise HTTPException(403, "Access denied")

    # Check anti-abuse
    detector = AnomalyDetector(redis_client)
    if not await detector.check_velocity(user_id, "dashboard_access", max_per_minute=30):
        raise HTTPException(429, "Too many requests")

    # Log access
    await audit_logger.log_data_access(token_user_id, "dashboard", str(user_id), "read", "success", ip_address, request_id)

    # Check cache
    cache_key = f"dashboard:{user_id}"
    cached = await get_cache(cache_key)
    if cached:
        cached["ai_used"] = cached.get("ai_used", False)
        return cached

    # Fetch data with internal service auth
    headers = {"X-Internal-Service-Key": INTERNAL_SERVICE_KEY}

    async with httpx.AsyncClient(timeout=5.0) as client:
        balance_resp = await client.get(f"{TRANSACTIONS_URL}/balance/{user_id}", headers=headers)
        txns_resp = await client.get(f"{TRANSACTIONS_URL}/transactions/{user_id}?limit=10", headers=headers)

        try:
            pred_resp = await client.get(f"{AI_URL}/predict/{user_id}", headers=headers)
            prediction = pred_resp.json() if pred_resp.status_code == 200 else None
        except Exception as e:
            logger.warning(f"AI prediction unavailable: {e}")
            prediction = None

        balance_resp.raise_for_status()
        txns_resp.raise_for_status()

        balance_data = balance_resp.json()
        transactions = txns_resp.json()

        # Build dashboard response
        dashboard = {
            "balance": {"current": balance_data.get("balance", 0)},
            "income": {"month": balance_data.get("total_income", 0)},
            "expenses": {"month": balance_data.get("total_expenses", 0)},
            "transactions": transactions,
            "ai_used": prediction.get("ai_used", False) if prediction else False,
            "ai_confidence": prediction.get("confidence") if prediction else None
        }

        await set_cache(cache_key, dashboard, ttl=60)
        return dashboard


# Service health with internal auth
@app.get("/internal/health")
async def internal_health(x_internal_service_key: str = Header(None)):
    """Internal health check with service auth"""
    if x_internal_service_key != INTERNAL_SERVICE_KEY:
        raise HTTPException(403, "Invalid service key")
    return {"status": "ok", "service": "gateway"}
