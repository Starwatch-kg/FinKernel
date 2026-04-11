"""Transaction Service - Port 8001"""
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
import sys
sys.path.append('/app')

from shared.db import get_db
from shared.models import User, Transaction, TransactionType, Base
from shared.redis import publish_event, delete_cache
from shared.schemas import TransactionCreate, TransactionResponse

app = FastAPI(title="Transactions")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/transactions", response_model=TransactionResponse)
async def create_transaction(txn: TransactionCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == txn.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    db_txn = Transaction(
        user_id=txn.user_id,
        amount=txn.amount,
        type=txn.type.value,
        category=txn.category.value,
        description=txn.description,
        timestamp=datetime.utcnow()
    )
    db.add(db_txn)

    if txn.type == TransactionType.income:
        user.balance += txn.amount
    else:
        user.balance -= txn.amount

    await db.commit()
    await db.refresh(db_txn)

    await publish_event("transaction.created", {
        "user_id": txn.user_id,
        "transaction_id": db_txn.id,
        "amount": txn.amount,
        "type": txn.type.value
    })

    await delete_cache(f"dashboard:{txn.user_id}")

    return db_txn


@app.get("/transactions/{user_id}", response_model=list[TransactionResponse])
async def get_transactions(user_id: int, limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.timestamp.desc())
        .limit(limit)
    )
    return result.scalars().all()


@app.get("/balance/{user_id}")
async def get_balance(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    income = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(Transaction.user_id == user_id, Transaction.type == "income")
    )

    expenses = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(Transaction.user_id == user_id, Transaction.type == "expense")
    )

    count = await db.execute(
        select(func.count(Transaction.id)).where(Transaction.user_id == user_id)
    )

    return {
        "user_id": user_id,
        "balance": user.balance,
        "total_income": income.scalar(),
        "total_expenses": expenses.scalar(),
        "transaction_count": count.scalar()
    }
