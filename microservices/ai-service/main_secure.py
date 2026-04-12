"""
SECURE AI SERVICE - Prompt injection protection
"""

import sys
import time
from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.append("/app")

from engine_secure import PredictionEngine
from shared.db import get_db
from shared.logger import setup_logger
from shared.models import Prediction, RiskLevel, Transaction, User
from shared.redis import get_cache, set_cache
from shared.schemas import PredictionResponse
from shared.security_hardening import RequestIDMiddleware, sanitize_for_llm
from shared.startup import validate_startup

config = validate_startup()
logger = setup_logger("ai_service_secure")

app = FastAPI(title="AI Service - Production", version="2.0.0")

# Add request ID middleware
app.add_middleware(RequestIDMiddleware)

engine = PredictionEngine()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ai-service", "version": "2.0.0"}


@app.post("/predict/{user_id}", response_model=PredictionResponse)
async def create_prediction(
    request: Request, user_id: int, db: AsyncSession = Depends(get_db)
):
    """
    Create AI prediction with SANITIZED inputs.
    All user data is sanitized before sending to LLM.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    start_time = time.time()

    try:
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

        # CRITICAL: Sanitize ALL transaction data before sending to LLM
        txn_data = []
        for t in transactions:
            # Sanitize description to prevent prompt injection
            safe_description = sanitize_for_llm(t.description or "", max_length=100)

            txn_data.append(
                {
                    "amount": round(t.amount, 2),
                    "type": t.type.value,
                    "timestamp": t.timestamp.isoformat(),
                    "description": safe_description,  # SANITIZED
                }
            )

        features = engine.calculate_features(txn_data)

        # Call prediction engine with sanitized data
        days_left, confidence, risk_level, recommendation, ai_used = (
            await engine.predict(user.balance, features, txn_data)
        )

        predicted_date = None
        if days_left is not None:
            predicted_date = datetime.utcnow() + timedelta(days=days_left)

        # Deactivate old predictions
        old_preds = (
            (
                await db.execute(
                    select(Prediction).where(
                        Prediction.user_id == user_id, Prediction.is_active == True
                    )
                )
            )
            .scalars()
            .all()
        )

        for p in old_preds:
            p.is_active = False

        # Create new prediction
        prediction = Prediction(
            user_id=user_id,
            days_left=days_left,
            predicted_date=predicted_date,
            risk_level=risk_level,
            confidence=confidence,
            features=features,
            recommendation=recommendation,
            is_active=True,
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
            "created_at": prediction.created_at.isoformat(),
        }

        await set_cache(f"prediction:{user_id}", response_data, ttl=3600)

        duration = time.time() - start_time
        logger.info(
            f"[{request_id}] Prediction created for user {user_id} "
            f"in {duration:.2f}s (AI: {ai_used})"
        )

        return prediction

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[{request_id}] Prediction error for user {user_id}: {e}", exc_info=True
        )
        raise HTTPException(500, "Prediction failed")


@app.get("/predict/{user_id}", response_model=PredictionResponse)
async def get_prediction(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get latest prediction for user"""
    cached = await get_cache(f"prediction:{user_id}")
    if cached:
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
