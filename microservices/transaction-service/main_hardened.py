"""Transaction Service - Enterprise Security Hardened Version"""
from fastapi import FastAPI, Depends, HTTPException, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
import sys
sys.path.append('/app')

from shared.db import get_db
from shared.models import User, Transaction, TransactionType
from shared.redis import publish_event, delete_cache, client as redis_client
from shared.schemas import TransactionCreate, TransactionResponse
from shared.startup import validate_startup
from shared.logger import setup_logger
from shared.audit import audit_logger, get_client_ip, get_request_id
from shared.anti_abuse import AnomalyDetector
import os

config = validate_startup()
logger = setup_logger("transaction_service_hardened")

app = FastAPI(title="Transactions-Hardened")

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


@app.post("/transactions", response_model=TransactionResponse)
async def create_transaction(
    txn: TransactionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(verify_internal_auth)
):
    """Create transaction with anti-abuse checks"""
    ip_address = await get_client_ip(request)
    request_id = await get_request_id(request)

    # Anti-abuse checks
    detector = AnomalyDetector(redis_client)

    # Check if user is blocked
    block_info = await detector.is_user_blocked(txn.user_id)
    if block_info:
        await audit_logger.log_data_access(
            txn.user_id, "transaction", "new", "create", "blocked",
            ip_address, request_id
        )
        raise HTTPException(403, f"Account temporarily blocked: {block_info['reason']}")

    # Check velocity
    if not await detector.check_velocity(txn.user_id, "transaction", max_per_minute=20):
        await audit_logger.log_data_access(
            txn.user_id, "transaction", "new", "create", "rate_limited",
            ip_address, request_id
        )
        raise HTTPException(429, "Too many transactions")

    # Get user with row lock
    result = await db.execute(
        select(User).where(User.id == txn.user_id).with_for_update()
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    # Validate transaction
    if txn.amount <= 0:
        raise HTTPException(400, "Amount must be positive")

    if txn.type == TransactionType.expense and user.balance < txn.amount:
        await audit_logger.log_data_access(
            txn.user_id, "transaction", "new", "create", "insufficient_funds",
            ip_address, request_id
        )
        raise HTTPException(400, "Insufficient balance")

    # Check for abnormal patterns
    avg_result = await db.execute(
        select(func.avg(Transaction.amount), func.stddev(Transaction.amount))
        .where(Transaction.user_id == txn.user_id, Transaction.type == txn.type)
    )
    avg_amount, std_dev = avg_result.first()

    if avg_amount and std_dev:
        await detector.check_abnormal_transaction_pattern(
            txn.user_id, txn.amount, float(avg_amount), float(std_dev)
        )

    # Create transaction
    db_txn = Transaction(
        user_id=txn.user_id,
        amount=txn.amount,
        type=txn.type.value,
        category=txn.category.value,
        description=txn.description,
        timestamp=datetime.utcnow()
    )
    db.add(db_txn)

    # Update balance
    if txn.type == TransactionType.income:
        user.balance += txn.amount
    else:
        user.balance -= txn.amount

    await db.commit()
    await db.refresh(db_txn)

    # Publish event
    await publish_event("transaction.created", {
        "user_id": txn.user_id,
        "transaction_id": db_txn.id,
        "amount": txn.amount,
        "type": txn.type.value
    })

    # Invalidate cache
    await delete_cache(f"dashboard:{txn.user_id}")

    # Audit log
    await audit_logger.log_data_access(
        txn.user_id, "transaction", str(db_txn.id), "create", "success",
        ip_address, request_id
    )

    # Record action
    await detector.record_action(txn.user_id, f"transaction_{txn.type.value}")

    return db_txn


@app.get("/transactions/{user_id}", response_model=list[TransactionResponse])
async def get_transactions(
    user_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(verify_internal_auth)
):
    """Get user transactions with limit"""
    if limit > 100:
        limit = 100

    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.timestamp.desc())
        .limit(limit)
    )
    return result.scalars().all()


@app.get("/balance/{user_id}")
async def get_balance(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(verify_internal_auth)
):
    """Get user balance and statistics"""
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
async def delete_transaction(
    transaction_id: int,
    userId: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(verify_internal_auth)
):
    """Delete transaction with ownership verification"""
    user_id = int(userId) if userId.isdigit() else 1
    ip_address = await get_client_ip(request)
    request_id = await get_request_id(request)

    # Get transaction with lock
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id
        ).with_for_update()
    )
    txn = result.scalar_one_or_none()

    if not txn:
        await audit_logger.log_data_access(
            user_id, "transaction", str(transaction_id), "delete", "not_found",
            ip_address, request_id
        )
        raise HTTPException(404, "Transaction not found")

    # Update user balance
    user_result = await db.execute(
        select(User).where(User.id == user_id).with_for_update()
    )
    user = user_result.scalar_one_or_none()

    if user:
        if txn.type == TransactionType.income:
            user.balance -= txn.amount
        else:
            user.balance += txn.amount

    # Delete transaction
    await db.delete(txn)
    await db.commit()

    await delete_cache(f"dashboard:{user_id}")

    await audit_logger.log_data_access(
        user_id, "transaction", str(transaction_id), "delete", "success",
        ip_address, request_id
    )

    return {"status": "deleted", "id": transaction_id}


@app.get("/internal/health")
async def internal_health(_auth: None = Depends(verify_internal_auth)):
    """Internal health check"""
    return {"status": "ok", "service": "transactions"}
