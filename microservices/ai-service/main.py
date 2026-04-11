"""AI Service - Port 8002"""
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import sys
sys.path.append('/app')

from shared.db import get_db
from shared.models import User, Transaction, Prediction, RiskLevel, Base
from shared.redis import get_cache, set_cache
from shared.schemas import PredictionResponse
from engine import PredictionEngine

app = FastAPI(title="AI")
engine = PredictionEngine()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/predict/{user_id}", response_model=PredictionResponse)
async def create_prediction(user_id: int, db: AsyncSession = Depends(get_db)):
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
        {"amount": t.amount, "type": t.type, "timestamp": t.timestamp}
        for t in transactions
    ]

    features = engine.calculate_features(txn_data)
    days_left, confidence, risk_level, recommendation = engine.predict(user.balance, features)

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

    await set_cache(f"prediction:{user_id}", {
        "id": prediction.id,
        "user_id": user_id,
        "days_left": days_left,
        "predicted_date": predicted_date.isoformat() if predicted_date else None,
        "risk_level": risk_level,
        "confidence": confidence,
        "recommendation": recommendation,
        "created_at": prediction.created_at.isoformat()
    }, ttl=3600)

    return prediction


@app.get("/predict/{user_id}", response_model=PredictionResponse)
async def get_prediction(user_id: int, db: AsyncSession = Depends(get_db)):
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
