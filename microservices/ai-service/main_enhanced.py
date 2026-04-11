"""Enhanced AI Service with metrics and tracing"""
from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import sys
import time
sys.path.append('/app')

from shared.db import get_db
from shared.models import User, Transaction, Prediction, RiskLevel
from shared.redis import get_cache, set_cache
from shared.schemas import PredictionResponse
from shared.startup import validate_startup
from shared.logger import setup_logger
from shared.metrics import PrometheusMiddleware, metrics_endpoint, ai_requests_total, ai_request_duration_seconds, ai_failures_total, ai_cache_hits_total
from shared.tracing import setup_tracing
from engine import PredictionEngine

config = validate_startup()
logger = setup_logger("ai_service")

app = FastAPI(title="AI")

# Setup tracing
tracer = setup_tracing("ai-service", app)

# Add Prometheus middleware
app.add_middleware(PrometheusMiddleware)

engine = PredictionEngine()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ai-service"}


@app.get("/metrics")
async def metrics(request: Request):
    return await metrics_endpoint(request)


@app.post("/predict/{user_id}", response_model=PredictionResponse)
async def create_prediction(user_id: int, db: AsyncSession = Depends(get_db)):
    start_time = time.time()
    model_name = "openrouter"

    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            ai_requests_total.labels(model=model_name, status='error').inc()
            raise HTTPException(404, "User not found")

        txn_result = await db.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.timestamp.desc())
            .limit(100)
        )
        transactions = txn_result.scalars().all()

        txn_data = [
            {"amount": t.amount, "type": t.type.value, "timestamp": t.timestamp.isoformat()}
            for t in transactions
        ]

        features = engine.calculate_features(txn_data)
        days_left, confidence, risk_level, recommendation, ai_used = await engine.predict(
            user.balance, features, txn_data
        )

        predicted_date = None
        if days_left is not None:
            predicted_date = datetime.utcnow() + timedelta(days=days_left)

        old_preds = (await db.execute(
            select(Prediction).where(Prediction.user_id == user_id, Prediction.is_active == True)
        )).scalars().all()

        for p in old_preds:
            p.is_active = False

        prediction = Prediction(
            user_id=user_id,
            days_left=days_left,
            predicted_date=predicted_date,
            risk_level=risk_level,
            confidence=confidence,
            features=features,
            recommendation=recommendation,
            is_active=True
        )

        db.add(prediction)
        await db.commit()
        await db.refresh(prediction)

        response_data = {
            "id": prediction.id,
            "user_id": user_id,
            "days_left": days_left,
            "predicted_date": predicted_date.isoformat() if predicted_date else None,
            "risk_level": risk_level,
            "confidence": confidence,
            "recommendation": recommendation,
            "ai_used": ai_used,
            "created_at": prediction.created_at.isoformat()
        }

        await set_cache(f"prediction:{user_id}", response_data, ttl=3600)

        # Record metrics
        duration = time.time() - start_time
        ai_requests_total.labels(model=model_name, status='success').inc()
        ai_request_duration_seconds.labels(model=model_name).observe(duration)

        if not ai_used:
            ai_cache_hits_total.inc()

        return prediction

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction error for user {user_id}: {e}", exc_info=True)
        ai_requests_total.labels(model=model_name, status='error').inc()
        ai_failures_total.labels(model=model_name, error_type=type(e).__name__).inc()
        raise HTTPException(500, "Prediction failed")


@app.get("/predict/{user_id}", response_model=PredictionResponse)
async def get_prediction(user_id: int, db: AsyncSession = Depends(get_db)):
    cached = await get_cache(f"prediction:{user_id}")
    if cached:
        ai_cache_hits_total.inc()
        return PredictionResponse(**cached)

    result = await db.execute(
        select(Prediction)
        .where(Prediction.user_id == user_id, Prediction.is_active == True)
        .order_by(Prediction.created_at.desc())
        .limit(1)
    )
    prediction = result.scalar_one_or_none()

    if not prediction:
        raise HTTPException(404, "No prediction found")

    return prediction
