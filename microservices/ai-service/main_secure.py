"""
SECURE AI SERVICE - Prompt injection protection
"""

import sys
import time
import os
from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel
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


def get_inflation_snapshot() -> dict:
    """Return the latest known inflation snapshot for AI responses."""
    country = os.getenv("FIN_COUNTRY_NAME", "Кыргызстан")
    rate = os.getenv("FIN_COUNTRY_INFLATION_RATE", "9.6")
    as_of = os.getenv("FIN_COUNTRY_INFLATION_AS_OF", "2026-02-13")
    label = os.getenv("FIN_COUNTRY_INFLATION_LABEL", "последние доступные данные")
    return {
        "country": country,
        "rate": rate,
        "as_of": as_of,
        "label": label,
    }


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


class ChatRequest(BaseModel):
    message: str
    user_id: int


@app.post("/chat")
async def ai_chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """AI financial chat - uses LLM cascade for real responses"""
    user_message = req.message.strip()
    if not user_message or len(user_message) > 1000:
        raise HTTPException(400, "Invalid message")

    # Get user context for personalized advice
    user_context = ""
    try:
        result = await db.execute(select(User).where(User.id == req.user_id))
        user = result.scalar_one_or_none()
        if user:
            txn_result = await db.execute(
                select(Transaction)
                .where(Transaction.user_id == req.user_id)
                .order_by(Transaction.timestamp.desc())
                .limit(10)
            )
            transactions = txn_result.scalars().all()
            total_expense = sum(t.amount for t in transactions if t.type.value == "expense")
            total_income = sum(t.amount for t in transactions if t.type.value == "income")
            user_context = (
                f"\nUser context: balance={user.balance:.0f}, "
                f"recent_expenses={total_expense:.0f}, recent_income={total_income:.0f}, "
                f"transaction_count={len(transactions)}"
            )
    except Exception as e:
        logger.warning(f"Failed to get user context: {e}")

    inflation = get_inflation_snapshot()
    inflation_context = (
        f"\nMacro context: country={inflation['country']}, "
        f"inflation_rate={inflation['rate']}%, as_of={inflation['as_of']}, "
        f"note={inflation['label']}"
    )

    # Try LLM providers in cascade
    from openai import AsyncOpenAI

    providers = []
    if engine.groq and engine.groq.client:
        providers.append(("Groq", engine.groq.client, engine.groq.model))
    if engine.openrouter and engine.openrouter.client:
        providers.append(("OpenRouter", engine.openrouter.client, engine.openrouter.model))

    for provider_name, client, model in providers:
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ты — финансовый AI-советник в приложении FinFuture. "
                            "Отвечай на русском языке. Давай конкретные, полезные советы по финансам. "
                            "Будь дружелюбным и профессиональным. Отвечай кратко (2-4 предложения). "
                            "Если это уместно, учитывай инфляцию в стране пользователя. "
                            "Если пользователь спрашивает не о финансах, мягко направь разговор к финансовой теме."
                            + user_context
                            + inflation_context
                        ),
                    },
                    {"role": "user", "content": user_message},
                ],
                temperature=0.7,
                max_tokens=300,
                timeout=10.0,
            )
            ai_text = response.choices[0].message.content
            logger.info(f"Chat response via {provider_name}")
            return {"response": ai_text, "provider": provider_name.lower()}
        except Exception as e:
            logger.warning(f"Chat via {provider_name} failed: {e}")
            continue

    # Fallback — contextual responses
    fallback_responses = {
        "расход": "Проанализируй свои траты по категориям. Часто до 30% бюджета уходит на импульсные покупки. Попробуй правило 24 часов — подожди день перед крупной покупкой.",
        "доход": "Для увеличения дохода рассмотри фриланс в своей области или инвестиции. Начни с подушки безопасности — 3-6 месячных расходов, затем инвестируй от 10% дохода.",
        "сохран": "Автоматизируй сбережения — настрой автоперевод 10-20% зарплаты на накопительный счёт в день получки. Так ты не заметишь 'потерю', но накопишь значительную сумму.",
        "инвест": "Начни с простых инструментов: облигации или индексные фонды. Главное правило — диверсификация. Не вкладывай больше 5% в один актив.",
        "бюджет": "Попробуй метод 50/30/20: 50% на необходимое, 30% на желания, 20% на сбережения. Записывай траты каждый день — это дисциплинирует.",
        "кредит": "Старайся не брать кредиты на потребление. Если есть кредит — гаси в первую очередь самый дорогой по процентам. Используй метод снежного кома.",
        "инфляц": f"По {get_inflation_snapshot()['country']} инфляция сейчас около {get_inflation_snapshot()['rate']}% ({get_inflation_snapshot()['label']}, {get_inflation_snapshot()['as_of']}). Держи часть сбережений в инструментах, которые хотя бы перекрывают рост цен.",
    }

    lower_msg = user_message.lower()
    for keyword, response in fallback_responses.items():
        if keyword in lower_msg:
            return {"response": response, "provider": "fallback"}

    return {
        "response": "Хороший вопрос! Я анализирую твои финансы и могу помочь с бюджетом, расходами, сбережениями и инвестициями. Задай более конкретный вопрос — например, 'как сэкономить на еде?' или 'куда инвестировать?'",
        "provider": "fallback",
    }


@app.get("/ai-advice/{user_id}")
async def get_ai_advice(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get AI tips for user based on their transactions"""
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return {"tips": []}

        txn_result = await db.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.timestamp.desc())
            .limit(20)
        )
        transactions = txn_result.scalars().all()

        tips = []
        if not transactions:
            tips.append({"icon": "📝", "text": "Добавь первую транзакцию, чтобы я начал анализировать твои финансы"})
            return {"tips": tips}

        total_expense = sum(t.amount for t in transactions if t.type.value == "expense")
        total_income = sum(t.amount for t in transactions if t.type.value == "income")
        inflation = get_inflation_snapshot()

        if total_expense > total_income * 0.8:
            tips.append({"icon": "⚠️", "text": f"Расходы ({total_expense:.0f}с) близки к доходам. Сократи траты на 15-20%"})
        elif total_income > 0:
            savings_rate = ((total_income - total_expense) / total_income) * 100
            tips.append({"icon": "✅", "text": f"Норма сбережений {savings_rate:.0f}%. {'Отлично!' if savings_rate > 20 else 'Старайся довести до 20%'}"})

        if user.balance > 0:
            tips.append({"icon": "💰", "text": f"Баланс: {user.balance:.0f}с. Рассмотри инвестирование свободных средств"})

        tips.append({
            "icon": "📈",
            "text": f"Инфляция в {inflation['country']}: около {inflation['rate']}% ({inflation['label']}, {inflation['as_of']})",
        })
        tips.append({"icon": "💡", "text": "Записывай все расходы — даже маленькие. Они часто составляют до 20% бюджета"})

        return {"tips": tips, "inflation": inflation}
    except Exception as e:
        logger.error(f"AI advice error: {e}")
        return {"tips": [{"icon": "💡", "text": "Веди учёт расходов ежедневно для лучшего контроля финансов"}]}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
