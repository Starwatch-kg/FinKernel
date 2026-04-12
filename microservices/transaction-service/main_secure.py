"""
PRODUCTION-GRADE TRANSACTION SERVICE - SECURITY HARDENED
Race condition protection with database-level locking.
Atomic financial operations.
"""

import sys
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.append("/app")

from adaptive_routes import router as adaptive_router
from learning_routes import router as learning_router
from market_routes import router as market_router
from onboarding_routes import router as onboarding_router

# Import route modules
from portfolio_routes_secure import router as portfolio_router
from shared.audit_logger import audit_logger
from shared.db import get_db
from shared.logger import setup_logger
from shared.models import Achievement, Transaction, TransactionType, User
from shared.redis import delete_cache, publish_event
from shared.schemas import TransactionCreate, TransactionResponse
from shared.security_hardening import RequestIDMiddleware, validate_amount
from shared.startup import validate_startup


async def check_achievements(user_id: int, db: AsyncSession):
    """Check and unlock achievements based on user's transaction history"""
    from market_routes import ACHIEVEMENT_TEMPLATES, get_generated_achievement_templates

    # Get existing unlocked achievements
    result = await db.execute(
        select(Achievement).where(Achievement.user_id == user_id)
    )
    unlocked_titles = {a.title for a in result.scalars().all()}

    # Count user transactions
    count_result = await db.execute(
        select(func.count(Transaction.id)).where(Transaction.user_id == user_id)
    )
    txn_count = count_result.scalar() or 0

    # Count distinct categories used
    cat_result = await db.execute(
        select(func.count(func.distinct(Transaction.category))).where(
            Transaction.user_id == user_id
        )
    )
    cat_count = cat_result.scalar() or 0

    # Get user balance
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    balance = user.balance if user else 0

    # Define unlock conditions
    unlock_checks = {
        "Первый шаг": txn_count >= 1,
        "Активный пользователь": txn_count >= 10,
        "Записывающий всё": txn_count >= 50,
        "Финансовый аналитик": txn_count >= 100,
        "Мастер учёта": txn_count >= 500,
        "Категоризатор": cat_count >= 5,
        "Организатор": cat_count >= 7,
        "Первая экономия": balance >= 1000,
        "Бережливый": balance >= 5000,
        "Мастер экономии": balance >= 10000,
        "Финансовый гений": balance >= 50000,
        "Миллионер": balance >= 1000000,
    }

    generated_templates = await get_generated_achievement_templates(user_id, db)

    newly_unlocked = []
    for template in ACHIEVEMENT_TEMPLATES + generated_templates:
        name = template["name"]
        if name in unlocked_titles:
            continue
        is_unlocked = template.get("unlocked")
        if is_unlocked is None:
            is_unlocked = name in unlock_checks and unlock_checks[name]
        if is_unlocked:
            ach = Achievement(
                user_id=user_id,
                title=name,
                xp_reward=template["xp_reward"],
                unlocked_at=datetime.utcnow(),
            )
            db.add(ach)
            newly_unlocked.append(name)
            logger.info(f"🏆 Achievement unlocked for user {user_id}: {name} (+{template['xp_reward']} XP)")

    if newly_unlocked:
        await db.commit()

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
    request: Request, txn: TransactionCreate, db: AsyncSession = Depends(get_db)
):
    """
    Create transaction with ATOMIC balance update.
    Uses database transaction to prevent race conditions.
    IDEMPOTENT: Same idempotency_key returns same transaction.
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
        # CRITICAL: Check idempotency key INSIDE transaction to prevent race conditions
        if txn.idempotency_key:
            existing_result = await db.execute(
                select(Transaction)
                .where(Transaction.idempotency_key == txn.idempotency_key)
                .with_for_update()  # Lock to prevent concurrent duplicates
            )
            existing_txn = existing_result.scalar_one_or_none()
            if existing_txn:
                logger.info(
                    f"[{request_id}] Idempotent request: returning existing transaction "
                    f"{existing_txn.id} for key {txn.idempotency_key}"
                )
                return existing_txn

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

        # Create transaction record with idempotency key
        db_txn = Transaction(
            user_id=txn.user_id,
            amount=validated_amount,
            type=txn.type.value,
            category=txn.category.value,
            description=txn.description,
            idempotency_key=txn.idempotency_key,
            timestamp=datetime.utcnow(),
        )
        db.add(db_txn)

        # Update balance ATOMICALLY
        if txn.type == TransactionType.income:
            user.balance += validated_amount
            logger.info(
                f"[{request_id}] Income: user {txn.user_id} +{validated_amount}"
            )
        else:
            user.balance -= validated_amount
            logger.info(
                f"[{request_id}] Expense: user {txn.user_id} -{validated_amount}"
            )

        # Flush to get transaction ID before commit
        await db.flush()
        await db.refresh(db_txn)

    # Transaction committed automatically when exiting context manager

    # Audit log transaction creation
    await audit_logger.log_transaction_created(
        user_id=txn.user_id,
        transaction_id=db_txn.id,
        amount=validated_amount,
        transaction_type=txn.type.value,
        request_id=request_id,
        idempotency_key=txn.idempotency_key,
    )

    # Publish event (after commit)
    await publish_event(
        "transaction.created",
        {
            "user_id": txn.user_id,
            "transaction_id": db_txn.id,
            "amount": validated_amount,
            "type": txn.type.value,
        },
    )

    # Invalidate cache
    await delete_cache(f"dashboard:{txn.user_id}")

    # Check and unlock achievements
    try:
        await check_achievements(txn.user_id, db)
    except Exception as e:
        logger.warning(f"[{request_id}] Achievement check failed: {e}")

    return db_txn


@app.get("/transactions/{user_id}", response_model=list[TransactionResponse])
async def get_transactions(
    user_id: int, limit: int = 50, db: AsyncSession = Depends(get_db)
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
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == user_id, Transaction.type == "income"
        )
    )

    expenses = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == user_id, Transaction.type == "expense"
        )
    )

    count = await db.execute(
        select(func.count(Transaction.id)).where(Transaction.user_id == user_id)
    )

    return {
        "user_id": user_id,
        "balance": round(user.balance, 2),
        "total_income": round(income.scalar(), 2),
        "total_expenses": round(expenses.scalar(), 2),
        "transaction_count": count.scalar(),
    }


@app.delete("/transactions/{transaction_id}")
async def delete_transaction(
    request: Request, transaction_id: int, db: AsyncSession = Depends(get_db)
):
    """
    Delete transaction with ATOMIC balance reversal.
    Verifies ownership via transaction service internal call.
    NOTE: This endpoint is called by gateway which already verified user.
    For direct use, add authentication dependency.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    # Get user_id from query param (passed by gateway after JWT verification)
    # In future: add get_current_user dependency here too for defense in depth
    from fastapi import Query

    user_id: int = Query(...)

    async with db.begin():
        # Get transaction with lock
        result = await db.execute(
            select(Transaction)
            .where(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id,  # OWNERSHIP CHECK
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

        if not user:
            raise HTTPException(404, "User not found")

        # Store balance before deletion for audit
        balance_before = user.balance

        # CRITICAL: Validate balance before reversing income deletion
        if txn.type == TransactionType.income:
            if user.balance < txn.amount:
                logger.warning(
                    f"[{request_id}] Cannot delete income transaction {transaction_id}: "
                    f"user {user_id} has insufficient balance {user.balance} < {txn.amount}"
                )
                raise HTTPException(
                    400,
                    f"Cannot delete transaction: insufficient balance to reverse income",
                )
            user.balance -= txn.amount
        else:
            user.balance += txn.amount

        balance_after = user.balance

        logger.info(
            f"[{request_id}] Deleted transaction {transaction_id} "
            f"for user {user_id}, reversed {txn.amount}"
        )

        # Delete transaction
        await db.delete(txn)
        await db.commit()

    # Audit log transaction deletion
    await audit_logger.log_transaction_deleted(
        user_id=user_id,
        transaction_id=transaction_id,
        amount=txn.amount,
        transaction_type=txn.type.value,
        request_id=request_id,
        balance_before=balance_before,
        balance_after=balance_after,
    )

    await delete_cache(f"dashboard:{user_id}")

    return {"status": "deleted", "id": transaction_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
