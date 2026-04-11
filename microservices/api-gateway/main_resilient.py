"""Resilient API Gateway with all production hardening"""
from fastapi import FastAPI, HTTPException, Header, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
import sys
import os
sys.path.append('/app')

from shared.redis import client as redis_client
from shared.db import get_db, async_session
from shared.models import User
from shared.startup import validate_startup
from shared.logger import setup_logger
from shared.auth_v2 import create_access_token, create_refresh_token, decode_token, store_refresh_token, rotate_refresh_token, blacklist_token, determine_role, hash_password, verify_password
from shared.rbac import extract_and_validate_token, verify_resource_ownership, Role
from shared.audit import audit_logger, get_client_ip, get_request_id
from shared.anti_abuse import AnomalyDetector
from shared.fraud_detection import FraudDetector
from shared.circuit_breaker_v2 import circuit_breaker_manager, CircuitBreakerOpenError
from shared.retry_v2 import retry_with_policy
from shared.alerting import alerting_system, AlertRules, AlertSeverity
from shared.health_check import health_check_system, HealthStatus
from shared.observability import metrics_collector, get_metrics_response
from shared.fallback_rate_limiter import fallback_rate_limiter
from shared.secrets_manager import secrets_manager
from shared.key_rotation import KeyRotationManager
import asyncio

config = validate_startup()
logger = setup_logger("gateway_resilient")

app = FastAPI(title="Gateway-Resilient")

# Initialize systems
key_rotation_manager = KeyRotationManager(redis_client)
alert_rules = AlertRules(alerting_system, redis_client)
fraud_detector = FraudDetector(redis_client)

TRANSACTIONS_URL = "http://transactions:8001"
AI_URL = "http://ai:8002"


@app.on_event("startup")
async def startup_event():
    """Initialize resilience systems"""
    # Initialize secrets manager
    await secrets_manager.get_secret("JWT_SECRET_KEY")

    # Initialize key rotation
    await key_rotation_manager.initialize()

    # Start audit logger
    asyncio.create_task(audit_logger.start_worker(async_session))

    # Start alerting system
    alerting_system.redis = redis_client
    asyncio.create_task(alerting_system.process_alerts())

    # Configure alerting
    webhook_url = os.getenv("ALERT_WEBHOOK_URL")
    if webhook_url:
        alerting_system.configure(webhook_url=webhook_url)

    logger.info("Resilience systems initialized")


@app.get("/health")
async def health():
    """Enhanced health check with component status"""
    try:
        # Check database
        db_healthy = await health_check_system.check_database(async_session)

        # Check Redis
        redis_healthy = await health_check_system.check_redis(redis_client)

        # Get overall status
        report = health_check_system.get_health_report()

        status_code = 200
        if report["status"] == "unhealthy":
            status_code = 503
        elif report["status"] == "degraded":
            status_code = 200  # Still serving requests

        return JSONResponse(content=report, status_code=status_code)

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            content={"status": "unhealthy", "error": str(e)},
            status_code=503
        )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return get_metrics_response()


@app.post("/api/register")
async def register(req: dict, request: Request, db: AsyncSession = Depends(get_db)):
    """Register with fraud detection"""
    ip_address = await get_client_ip(request)
    request_id = await get_request_id(request)

    email = req.get("email")
    password = req.get("password")
    name = req.get("name")

    # Rate limiting with fallback
    try:
        rate_ok = await redis_client.incr(f"rate:register:{email}")
        if rate_ok > 5:
            raise HTTPException(429, "Too many registration attempts")
    except Exception:
        # Fallback to in-memory
        if not fallback_rate_limiter.check_rate_limit(f"register:{email}", max_requests=5, window=300):
            raise HTTPException(429, "Too many registration attempts")

    # Check if user exists
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        await audit_logger.log_auth("register", "failed", email=email, ip_address=ip_address, request_id=request_id, reason="user_exists")
        raise HTTPException(400, "User already exists")

    # Create user
    password_hash = hash_password(password)
    user = User(email=email, username=name, password_hash=password_hash, balance=5000.0)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create tokens
    role = determine_role(email)
    access_token = create_access_token(user.id, email, role)
    refresh_token = create_refresh_token(user.id, email)

    # Store refresh token
    refresh_payload = decode_token(refresh_token)
    await store_refresh_token(redis_client, user.id, refresh_token, refresh_payload["jti"])

    await audit_logger.log_auth("register", "success", user_id=user.id, email=email, ip_address=ip_address, request_id=request_id)
    metrics_collector.record_auth_attempt("register", True)

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "expires_in": 900}


@app.get("/api/dashboard/{user_id}")
async def get_dashboard(user_id: int, request: Request, authorization: str = Header(None)):
    """Dashboard with circuit breaker and fraud detection"""
    ip_address = await get_client_ip(request)
    request_id = await get_request_id(request)

    # Validate token
    payload = await extract_and_validate_token(authorization, redis_client)
    token_user_id = payload.get("user_id")
    role = payload.get("role", Role.USER)

    # Verify ownership
    if not verify_resource_ownership(token_user_id, user_id, role):
        await audit_logger.log_data_access(token_user_id, "dashboard", str(user_id), "read", "forbidden", ip_address, request_id)
        raise HTTPException(403, "Access denied")

    # Check fraud score
    risk_score = await fraud_detector.get_cached_risk_score(user_id)
    if not risk_score:
        # Calculate in background
        asyncio.create_task(fraud_detector.calculate_risk_score(user_id, get_db()))
    elif risk_score.score > 0.8:
        await alerting_system.send_alert(
            "High-Risk User Access",
            f"User {user_id} with risk score {risk_score.score:.2f} accessed dashboard",
            AlertSeverity.WARNING,
            "fraud_detection",
            {"user_id": user_id, "risk_score": risk_score.score}
        )

    # Get data with circuit breakers
    headers = {"X-Internal-Service-Key": os.getenv("INTERNAL_SERVICE_KEY", "")}

    try:
        # Transaction service with circuit breaker
        txn_breaker = circuit_breaker_manager.get_breaker("transactions", failure_threshold=5, recovery_timeout=30)

        async def fetch_transactions():
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{TRANSACTIONS_URL}/balance/{user_id}", headers=headers)
                resp.raise_for_status()
                return resp.json()

        balance_data = await txn_breaker.call(fetch_transactions)

    except CircuitBreakerOpenError:
        logger.warning("Transaction service circuit breaker open")
        balance_data = {"balance": 0, "total_income": 0, "total_expenses": 0}
        await alerting_system.send_alert(
            "Circuit Breaker Open",
            "Transaction service circuit breaker is open",
            AlertSeverity.ERROR,
            "circuit_breaker",
            {"service": "transactions"}
        )
    except Exception as e:
        logger.error(f"Transaction service error: {e}")
        balance_data = {"balance": 0, "total_income": 0, "total_expenses": 0}

    # AI service with circuit breaker and fallback
    try:
        ai_breaker = circuit_breaker_manager.get_breaker("ai", failure_threshold=3, recovery_timeout=60)

        async def fetch_prediction():
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{AI_URL}/predict/{user_id}", headers=headers)
                resp.raise_for_status()
                return resp.json()

        prediction = await ai_breaker.call(fetch_prediction)

    except CircuitBreakerOpenError:
        logger.warning("AI service circuit breaker open")
        prediction = {"ai_used": False, "confidence": 0.0}
    except Exception as e:
        logger.warning(f"AI service unavailable: {e}")
        prediction = {"ai_used": False, "confidence": 0.0}

    # Build response
    dashboard = {
        "balance": {"current": balance_data.get("balance", 0)},
        "income": {"month": balance_data.get("total_income", 0)},
        "expenses": {"month": balance_data.get("total_expenses", 0)},
        "ai_used": prediction.get("ai_used", False),
        "ai_confidence": prediction.get("confidence"),
        "risk_score": risk_score.score if risk_score else None
    }

    await audit_logger.log_data_access(token_user_id, "dashboard", str(user_id), "read", "success", ip_address, request_id)

    return dashboard


@app.get("/admin/circuit-breakers")
async def get_circuit_breakers(authorization: str = Header(None)):
    """Admin endpoint to view circuit breaker states"""
    payload = await extract_and_validate_token(authorization, redis_client)

    if payload.get("role") != Role.ADMIN:
        raise HTTPException(403, "Admin access required")

    return circuit_breaker_manager.get_all_states()


@app.post("/admin/circuit-breakers/{name}/reset")
async def reset_circuit_breaker(name: str, authorization: str = Header(None)):
    """Admin endpoint to reset circuit breaker"""
    payload = await extract_and_validate_token(authorization, redis_client)

    if payload.get("role") != Role.ADMIN:
        raise HTTPException(403, "Admin access required")

    breaker = circuit_breaker_manager.get_breaker(name)
    breaker.reset()

    return {"status": "reset", "breaker": name}


@app.get("/admin/fraud/high-risk-users")
async def get_high_risk_users(authorization: str = Header(None)):
    """Admin endpoint to view high-risk users"""
    payload = await extract_and_validate_token(authorization, redis_client)

    if payload.get("role") != Role.ADMIN:
        raise HTTPException(403, "Admin access required")

    high_risk_users = await fraud_detector.get_high_risk_users()

    return {"high_risk_users": high_risk_users, "count": len(high_risk_users)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
