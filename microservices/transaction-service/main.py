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
from shared.startup import validate_startup
from shared.logger import setup_logger

# Import route modules
from portfolio_routes import router as portfolio_router
from learning_routes import router as learning_router
from adaptive_routes import router as adaptive_router
from market_routes import router as market_router
from onboarding_routes import router as onboarding_router

# Validate configuration on startup
config = validate_startup()
logger = setup_logger("transaction_service")

app = FastAPI(title="Transactions")

# Include routers
app.include_router(portfolio_router, tags=["portfolio"])
app.include_router(learning_router, tags=["learning"])
app.include_router(adaptive_router, tags=["adaptive"])
app.include_router(market_router, tags=["market"])
app.include_router(onboarding_router, tags=["onboarding"])


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/transactions", response_model=TransactionResponse)
async def create_transaction(txn: TransactionCreate, db: AsyncSession = Depends(get_db)):
    # Check for idempotency key - if provided, check if transaction already exists
    if txn.idempotency_key:
        result = await db.execute(
            select(Transaction).where(Transaction.idempotency_key == txn.idempotency_key)
        )
        existing_txn = result.scalar_one_or_none()
        if existing_txn:
            # Return existing transaction (idempotent response)
            return existing_txn

    async with db.begin():
        # Lock user row to prevent concurrent balance modifications
        result = await db.execute(
            select(User).where(User.id == txn.user_id).with_for_update()
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(404, "User not found")

        # Check balance BEFORE modification for expenses
        if txn.type == TransactionType.expense:
            if user.balance < txn.amount:
                raise HTTPException(400, "Insufficient funds")
            user.balance -= txn.amount
        else:
            user.balance += txn.amount

        # Create transaction record with idempotency key
        db_txn = Transaction(
            user_id=txn.user_id,
            amount=txn.amount,
            type=txn.type.value,
            category=txn.category.value,
            description=txn.description,
            timestamp=datetime.utcnow(),
            idempotency_key=txn.idempotency_key
        )
        db.add(db_txn)
        await db.flush()  # Get transaction ID before commit

    # Refresh to get all fields after commit
    await db.refresh(db_txn)

    # Publish event AFTER successful commit
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


@app.delete("/transactions/{transaction_id}")
async def delete_transaction(transaction_id: int, userId: str, db: AsyncSession = Depends(get_db)):
    user_id = int(userId) if userId.isdigit() else 1

    async with db.begin():
        # Lock user row first to prevent concurrent balance modifications
        user_result = await db.execute(
            select(User).where(User.id == user_id).with_for_update()
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(404, "User not found")

        # Lock and get transaction
        result = await db.execute(
            select(Transaction).where(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id
            ).with_for_update()
        )
        txn = result.scalar_one_or_none()

        if not txn:
            raise HTTPException(404, "Transaction not found")

        # Reverse balance change atomically
        if txn.type == TransactionType.income:
            user.balance -= txn.amount
        else:
            user.balance += txn.amount

        # Delete transaction
        await db.delete(txn)
        await db.flush()

    await delete_cache(f"dashboard:{user_id}")

    return {"status": "deleted", "id": transaction_id}
