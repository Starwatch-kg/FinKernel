"""
PRODUCTION-GRADE TRANSACTION SERVICE - SECURITY HARDENED
Race condition protection with database-level locking.
Atomic financial operations.
"""
from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
import sys
sys.path.append('/app')

from shared.db import get_db
from shared.models import User, Transaction, TransactionType
from shared.redis import publish_event, delete_cache
from shared.schemas import TransactionCreate, TransactionResponse
from shared.startup import validate_startup
from shared.logger import setup_logger
from shared.security_hardening import RequestIDMiddleware, validate_amount

# Import route modules
from portfolio_routes_secure import router as portfolio_router
from learning_routes import router as learning_router
from adaptive_routes import router as adaptive_router
from market_routes import router as market_router
from onboarding_routes import router as onboarding_router

config = validate_startup()
logger = setup_logger("transaction_service_secure")

app = FastAPI(title="Transaction Service - Production", version="2.0.0")

# Add request ID middleware
app.add_middleware(RequestIDMiddleware)

# Include routers
app.include_router(portfolio_router, tags=["portfolio"])
app.include_router(learning_router, tags=["learning"])
app.include_router(adaptive_router, tags=["adaptive"])
app.include_router(market_router, tags=["market"])
app.include_router(onboarding_router, tags=["onboarding"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "transaction-service", "version": "2.0.0"}


@app.post("/transactions", response_model=TransactionResponse)
async def create_transaction(
    request: Request,
    txn: TransactionCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create transaction with ATOMIC balance update.
    Uses database transaction to prevent race conditions.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    # Validate amount
    try:
        validated_amount = validate_amount(txn.amount)
    except ValueError as e:
        logger.warning(f"[{request_id}] Invalid amount: {e}")
        raise HTTPException(400, str(e))

    # Start database transaction
    async with db.begin():
        # CRITICAL: Lock user row for update to prevent race conditions
        result = await db.execute(
            select(User)
            .where(User.id == txn.user_id)
            .with_for_update()  # DATABASE-LEVEL LOCK
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(404, "User not found")

        # Check balance for expenses
        if txn.type == TransactionType.expense:
            if user.balance < validated_amount:
                logger.warning(
                    f"[{request_id}] Insufficient funds: user {txn.user_id} "
                    f"has {user.balance}, needs {validated_amount}"
                )
                raise HTTPException(400, "Insufficient funds")

        # Create transaction record
        db_txn = Transaction(
            user_id=txn.user_id,
            amount=validated_amount,
            type=txn.type.value,
            category=txn.category.value,
            description=txn.description,
            timestamp=datetime.utcnow()
        )
        db.add(db_txn)

        # Update balance ATOMICALLY
        if txn.type == TransactionType.income:
            user.balance += validated_amount
            logger.info(f"[{request_id}] Income: user {txn.user_id} +{validated_amount}")
        else:
            user.balance -= validated_amount
            logger.info(f"[{request_id}] Expense: user {txn.user_id} -{validated_amount}")

        # Commit transaction (releases lock)
        await db.commit()
        await db.refresh(db_txn)

    # Publish event (after commit)
    await publish_event("transaction.created", {
        "user_id": txn.user_id,
        "transaction_id": db_txn.id,
        "amount": validated_amount,
        "type": txn.type.value
    })

    # Invalidate cache
    await delete_cache(f"dashboard:{txn.user_id}")

    return db_txn


@app.get("/transactions/{user_id}", response_model=list[TransactionResponse])
async def get_transactions(
    user_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Get transactions for user - pagination enforced"""
    # Enforce max limit
    limit = min(limit, 100)

    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.timestamp.desc())
        .limit(limit)
    )
    return result.scalars().all()


@app.get("/balance/{user_id}")
async def get_balance(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get user balance and statistics"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(404, "User not found")

    # Calculate totals
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
        "balance": round(user.balance, 2),
        "total_income": round(income.scalar(), 2),
        "total_expenses": round(expenses.scalar(), 2),
        "transaction_count": count.scalar()
    }


@app.delete("/transactions/{transaction_id}")
async def delete_transaction(
    request: Request,
    transaction_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete transaction with ATOMIC balance reversal.
    Verifies ownership.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    async with db.begin():
        # Get transaction with lock
        result = await db.execute(
            select(Transaction)
            .where(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id  # OWNERSHIP CHECK
            )
            .with_for_update()
        )
        txn = result.scalar_one_or_none()

        if not txn:
            raise HTTPException(404, "Transaction not found or access denied")

        # Lock user for balance update
        user_result = await db.execute(
            select(User).where(User.id == user_id).with_for_update()
        )
        user = user_result.scalar_one_or_none()

        if user:
            # Reverse balance change
            if txn.type == TransactionType.income:
                user.balance -= txn.amount
            else:
                user.balance += txn.amount

            logger.info(
                f"[{request_id}] Deleted transaction {transaction_id} "
                f"for user {user_id}, reversed {txn.amount}"
            )

        # Delete transaction
        await db.delete(txn)
        await db.commit()

    await delete_cache(f"dashboard:{user_id}")

    return {"status": "deleted", "id": transaction_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
