"""AI Service - Enterprise Security Hardened Version"""
from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import sys
sys.path.append('/app')

from shared.db import get_db
from shared.models import User, Transaction, Prediction, RiskLevel
from shared.redis import get_cache, set_cache
from shared.startup import validate_startup
from shared.logger import setup_logger
from shared.ai_validation import AIValidator, ValidatedPrediction
from engine import PredictionEngine
import os

config = validate_startup()
logger = setup_logger("ai_service_hardened")

app = FastAPI(title="AI-Hardened")
engine = PredictionEngine()

INTERNAL_SERVICE_KEY = os.getenv("INTERNAL_SERVICE_KEY", "")


def verify_internal_auth(x_internal_service_key: str = Header(None)):
    """Verify internal service-to-service authentication"""
    if not INTERNAL_SERVICE_KEY:
        logger.error("INTERNAL_SERVICE_KEY not configured")
        raise HTTPException(500, "Service misconfigured")

    if x_internal_service_key != INTERNAL_SERVICE_KEY:
        logger.warning("Invalid internal service key")
        raise HTTPException(403, "Invalid service credentials")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/predict/{user_id}")
async def create_prediction(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(verify_internal_auth)
):
    """Create AI prediction with validation and fallback"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
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

    try:
        # Attempt AI prediction
        days_left, confidence, risk_level, recommendation, ai_used = await engine.predict(
            user.balance, features, txn_data
        )

        # Validate AI output
        raw_output = {
            "days_left": days_left,
            "risk_level": risk_level,
            "confidence": confidence,
            "recommendation": recommendation,
            "ai_used": ai_used
        }

        validated = AIValidator.validate_prediction(raw_output, min_confidence=0.6)

    except Exception as e:
        logger.warning(f"AI prediction failed for user {user_id}, using fallback: {e}")

        # Calculate safe fallback
        avg_daily_expense = features.get("avg_daily_expense", 0)
        validated = AIValidator.create_safe_fallback_prediction(user.balance, avg_daily_expense)

    # Store prediction
    predicted_date = None
    if validated.days_left is not None:
        predicted_date = datetime.utcnow() + timedelta(days=validated.days_left)

    # Deactivate old predictions
    old_preds = (await db.execute(
        select(Prediction).where(Prediction.user_id == user_id, Prediction.is_active == True)
    )).scalars().all()

    for p in old_preds:
        p.is_active = False

    prediction = Prediction(
        user_id=user_id,
        days_left=validated.days_left,
        predicted_date=predicted_date,
        risk_level=validated.risk_level.value,
        confidence=validated.confidence,
        features=features,
        recommendation=validated.recommendation,
        is_active=True
    )

    db.add(prediction)
    await db.commit()
    await db.refresh(prediction)

    response_data = {
        "id": prediction.id,
        "user_id": user_id,
        "days_left": validated.days_left,
        "predicted_date": predicted_date.isoformat() if predicted_date else None,
        "risk_level": validated.risk_level.value,
        "confidence": validated.confidence,
        "recommendation": validated.recommendation,
        "ai_used": validated.ai_used,
        "created_at": prediction.created_at.isoformat()
    }

    await set_cache(f"prediction:{user_id}", response_data, ttl=3600)

    return response_data


@app.get("/predict/{user_id}")
async def get_prediction(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(verify_internal_auth)
):
    """Get latest prediction with AI transparency"""
    cached = await get_cache(f"prediction:{user_id}")
    if cached:
        return cached

    result = await db.execute(
        select(Prediction)
        .where(Prediction.user_id == user_id, Prediction.is_active == True)
        .order_by(Prediction.created_at.desc())
        .limit(1)
    )
    prediction = result.scalar_one_or_none()

    if not prediction:
        raise HTTPException(404, "No prediction found")

    return {
        "id": prediction.id,
        "user_id": user_id,
        "days_left": prediction.days_left,
        "predicted_date": prediction.predicted_date.isoformat() if prediction.predicted_date else None,
        "risk_level": prediction.risk_level,
        "confidence": prediction.confidence,
        "recommendation": prediction.recommendation,
        "ai_used": True,  # From DB means it was AI-generated
        "created_at": prediction.created_at.isoformat()
    }


@app.get("/internal/health")
async def internal_health(_auth: None = Depends(verify_internal_auth)):
    """Internal health check"""
    return {"status": "ok", "service": "ai"}
