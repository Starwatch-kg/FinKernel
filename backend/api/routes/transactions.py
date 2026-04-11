"""
Роутер для транзакций и чата
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timedelta
import logging

from backend.core import get_db
from backend.models import User, Transaction, TransactionCategory
from backend.schemas import (
    AddTransactionRequest,
    ChatRequest,
    ChatResponse,
    PurchaseEvaluationRequest,
    PurchaseEvaluationResponse,
)
from backend.services import parse_transaction_with_llm, evaluate_purchase_with_llm

router = APIRouter(prefix="/api", tags=["transactions"])
logger = logging.getLogger(__name__)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Чат с AI для парсинга транзакций"""
    result = await db.execute(select(User).where(User.id == request.user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        parsed = await parse_transaction_with_llm(request.message)
    except Exception as e:
        logger.error(f"LLM parsing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")

    amount = float(parsed.get("amount", 0))
    category = parsed.get("category", "other")

    if amount <= 0:
        return ChatResponse(
            success=False,
            message="Не удалось определить сумму транзакции"
        )

    transaction = Transaction(
        user_id=user.id,
        amount=amount,
        category=TransactionCategory[category]
    )
    db.add(transaction)

    user.current_balance -= amount

    if user.current_balance < 0:
        user.financial_score = max(0, user.financial_score - 50)
    else:
        user.financial_score = min(1000, user.financial_score + 10)

    await db.commit()
    await db.refresh(transaction)

    return ChatResponse(
        success=True,
        message=f"Транзакция записана: -{amount} руб. в категории {category}. Баланс: {user.current_balance:.2f} руб.",
        transaction={
            "id": transaction.id,
            "amount": transaction.amount,
            "category": transaction.category.value,
            "timestamp": transaction.timestamp.isoformat()
        }
    )


@router.get("/dashboard")
async def get_dashboard(userId: str, db: AsyncSession = Depends(get_db)):
    """Дашборд с полной статистикой"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user.id)
        .where(Transaction.timestamp >= thirty_days_ago)
        .order_by(desc(Transaction.timestamp))
    )
    all_transactions = result.scalars().all()

    recent_transactions = all_transactions[:10]
    total_expenses = sum(t.amount for t in all_transactions)

    if total_expenses > 0:
        daily_avg = total_expenses / 30
        days_left = int(user.current_balance / daily_avg) if daily_avg > 0 else 999
    else:
        days_left = 999

    spending_by_category = {}
    for t in all_transactions:
        cat = t.category.value
        spending_by_category[cat] = spending_by_category.get(cat, 0) + t.amount

    ai_tips = []
    if user.current_balance < 1000:
        ai_tips.append("⚠️ Баланс критически низкий! Сократите расходы.")
    elif total_expenses > user.current_balance * 0.5:
        ai_tips.append("💡 Вы тратите больше половины баланса в месяц. Будьте осторожнее!")
    else:
        ai_tips.append("✅ Отличная работа! Ваши траты под контролем.")

    ai_tips.append(f"📊 Финансовый скоринг: {user.financial_score}/1000")

    if spending_by_category.get("food", 0) > total_expenses * 0.4:
        ai_tips.append("🍔 Расходы на еду составляют более 40%. Попробуйте готовить дома!")

    return {
        "balance": user.current_balance,
        "income": 0,
        "expenses": total_expenses,
        "transactions": [
            {
                "id": t.id,
                "amount": -t.amount,
                "category": t.category.value,
                "timestamp": t.timestamp.isoformat(),
                "description": t.description or f"Покупка в категории {t.category.value}"
            }
            for t in recent_transactions
        ],
        "forecast": {
            "days_left": days_left,
            "message": f"При текущих тратах денег хватит на {days_left} дней" if days_left < 999 else "Отличный баланс!"
        },
        "ai_tips": ai_tips,
        "spending_chart": [
            {"category": cat, "amount": amount}
            for cat, amount in spending_by_category.items()
        ],
        "stats": {
            "level": user.level,
            "xp": user.xp,
            "streak": user.streak
        }
    }


@router.get("/transactions")
async def get_transactions(userId: str, limit: int = 30, db: AsyncSession = Depends(get_db)):
    """Список транзакций"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user.id)
        .order_by(desc(Transaction.timestamp))
        .limit(limit)
    )
    transactions = result.scalars().all()

    return [
        {
            "id": t.id,
            "amount": -t.amount,
            "category": t.category.value,
            "timestamp": t.timestamp.isoformat(),
            "description": t.description or f"Покупка в категории {t.category.value}"
        }
        for t in transactions
    ]


@router.post("/transactions")
async def add_transaction(request: AddTransactionRequest, db: AsyncSession = Depends(get_db)):
    """Добавить транзакцию"""
    result = await db.execute(select(User).where(User.username == request.userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        cat = TransactionCategory[request.category]
    except KeyError:
        cat = TransactionCategory.other

    transaction = Transaction(
        user_id=user.id,
        amount=abs(request.amount),
        category=cat,
        description=request.description
    )
    db.add(transaction)

    user.current_balance -= abs(request.amount)
    user.xp += 5
    user.last_activity = datetime.utcnow()

    if user.xp >= 100:
        user.level += 1
        user.xp = 0

    await db.commit()
    await db.refresh(transaction)

    return {
        "id": transaction.id,
        "amount": -transaction.amount,
        "category": transaction.category.value,
        "timestamp": transaction.timestamp.isoformat(),
        "description": transaction.description
    }


@router.delete("/transactions/{transactionId}")
async def delete_transaction(transactionId: int, userId: str, db: AsyncSession = Depends(get_db)):
    """Удалить транзакцию"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(Transaction)
        .where(Transaction.id == transactionId)
        .where(Transaction.user_id == user.id)
    )
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    user.current_balance += transaction.amount

    await db.delete(transaction)
    await db.commit()

    return {"status": "deleted"}


@router.post("/evaluate-purchase", response_model=PurchaseEvaluationResponse)
async def evaluate_purchase(request: PurchaseEvaluationRequest, db: AsyncSession = Depends(get_db)):
    """Оценка импульсивной покупки"""
    result = await db.execute(select(User).where(User.id == request.user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    evaluation = await evaluate_purchase_with_llm(request.wish, user.current_balance)

    return PurchaseEvaluationResponse(
        necessity_score=evaluation.get("necessity_score", 5),
        verdict=evaluation.get("verdict", "Подумай еще раз"),
        reasoning=evaluation.get("reasoning", "Нужно больше данных для оценки"),
        current_balance=user.current_balance
    )


@router.get("/user/{user_id}/dashboard")
async def get_user_dashboard(user_id: int, db: AsyncSession = Depends(get_db)):
    """Legacy dashboard endpoint"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(desc(Transaction.timestamp))
        .limit(10)
    )
    transactions = result.scalars().all()

    return {
        "user_id": user.id,
        "username": user.username,
        "current_balance": user.current_balance,
        "financial_score": user.financial_score,
        "recent_transactions": [
            {
                "id": t.id,
                "amount": t.amount,
                "category": t.category.value,
                "timestamp": t.timestamp.isoformat()
            }
            for t in transactions
        ]
    }
