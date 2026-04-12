"""
SECURE PORTFOLIO ROUTES - Race condition protection
CRITICAL: All routes require authentication via gateway
"""

import sys
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.append("/app")

from pydantic import BaseModel, Field
from shared.audit_logger import audit_logger
from shared.db import get_db
from shared.logger import setup_logger
from shared.market_data import get_market_data_provider
from shared.models import Portfolio, Stock, TradeHistory, User
from shared.redis import delete_cache, get_cache, publish_event, set_cache
from shared.security_hardening import validate_amount, validate_shares

logger = setup_logger("portfolio_secure")
market_data = get_market_data_provider()

router = APIRouter()


class TradeRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=10)
    shares: int = Field(gt=0, le=1_000_000)
    action: str = Field(pattern="^(buy|sell)$")
    idempotency_key: str = Field(None, min_length=1, max_length=255)


async def init_stocks(db: AsyncSession):
    """Initialize stock data if not exists"""
    all_stocks = market_data.get_all_stocks()

    for stock_data in all_stocks:
        result = await db.execute(
            select(Stock).where(Stock.ticker == stock_data["ticker"])
        )
        if not result.scalar_one_or_none():
            stock = Stock(
                ticker=stock_data["ticker"],
                name=stock_data["name"],
                price=stock_data["price"],
                change_percent=stock_data["change_percent"],
                volume=stock_data["volume"],
                market_cap=stock_data["market_cap"],
                sector=stock_data["sector"],
            )
            db.add(stock)
            logger.info(f"Initialized stock: {stock_data['ticker']}")
    await db.commit()


@router.get("/portfolio/{user_id}")
async def get_portfolio(user_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get user portfolio.
    SECURITY: user_id must be verified by gateway before calling this endpoint.
    Gateway extracts user_id from JWT token, not from request.
    """
    cache_key = f"portfolio:{user_id}"
    cached = await get_cache(cache_key)
    if cached:
        return cached

    result = await db.execute(select(Portfolio).where(Portfolio.user_id == user_id))
    positions = result.scalars().all()

    portfolio_data = []
    total_value = 0
    total_cost = 0

    for pos in positions:
        stock_result = await db.execute(select(Stock).where(Stock.ticker == pos.ticker))
        stock = stock_result.scalar_one_or_none()

        if stock:
            current_value = stock.price * pos.shares
            cost_basis = pos.avg_price * pos.shares
            profit_loss = current_value - cost_basis
            profit_loss_pct = (profit_loss / cost_basis * 100) if cost_basis > 0 else 0

            portfolio_data.append(
                {
                    "ticker": pos.ticker,
                    "name": stock.name,
                    "shares": pos.shares,
                    "avg_price": round(pos.avg_price, 2),
                    "current_price": round(stock.price, 2),
                    "current_value": round(current_value, 2),
                    "profit_loss": round(profit_loss, 2),
                    "profit_loss_pct": round(profit_loss_pct, 2),
                    "sector": stock.sector,
                }
            )

            total_value += current_value
            total_cost += cost_basis

    total_profit_loss = total_value - total_cost
    total_profit_loss_pct = (
        (total_profit_loss / total_cost * 100) if total_cost > 0 else 0
    )

    response = {
        "positions": portfolio_data,
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_profit_loss": round(total_profit_loss, 2),
        "total_profit_loss_pct": round(total_profit_loss_pct, 2),
        "cash": 0,
    }

    await set_cache(cache_key, response, ttl=60)
    return response


@router.post("/trade/{user_id}")
async def execute_trade(
    request: Request,
    user_id: int,
    trade: TradeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Execute trade with ATOMIC balance and position updates.
    CRITICAL: Uses database-level locking to prevent race conditions.
    IDEMPOTENT: Same idempotency_key returns same trade result.
    SECURITY: user_id must be verified by gateway (from JWT token).
    """
    request_id = getattr(request.state, "request_id", "unknown")

    # Validate inputs
    try:
        validated_shares = validate_shares(trade.shares)
    except ValueError as e:
        raise HTTPException(400, str(e))

    # CRITICAL: Check idempotency key to prevent duplicate trades
    if trade.idempotency_key:
        existing_result = await db.execute(
            select(TradeHistory).where(
                TradeHistory.idempotency_key == trade.idempotency_key,
                TradeHistory.user_id == user_id,
            )
        )
        existing_trade = existing_result.scalar_one_or_none()
        if existing_trade:
            logger.info(
                f"[{request_id}] Idempotent trade request: returning existing trade "
                f"{existing_trade.id} for key {trade.idempotency_key}"
            )
            return {
                "status": "success",
                "action": existing_trade.action,
                "ticker": existing_trade.ticker,
                "shares": existing_trade.shares,
                "price": round(existing_trade.price, 2),
                "total": round(existing_trade.total_cost, 2),
                "idempotent": True,
            }

    # Start atomic transaction
    async with db.begin():
        # LOCK user row to prevent concurrent trades
        user_result = await db.execute(
            select(User).where(User.id == user_id).with_for_update()
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(404, "User not found")

        # Get stock with current price
        stock_result = await db.execute(
            select(Stock).where(Stock.ticker == trade.ticker).with_for_update()
        )
        stock = stock_result.scalar_one_or_none()
        if not stock:
            raise HTTPException(404, "Stock not found")

        # Update stock price with deterministic market data
        current_price = market_data.get_current_price(trade.ticker)
        change_pct = market_data.get_change_percent(trade.ticker)
        stock.price = current_price
        stock.change_percent = change_pct

        total_cost = round(stock.price * validated_shares, 2)

        if trade.action == "buy":
            # Check sufficient funds
            if user.balance < total_cost:
                logger.warning(
                    f"[{request_id}] Insufficient funds for trade: "
                    f"user {user_id} has {user.balance}, needs {total_cost}"
                )
                raise HTTPException(
                    400, f"Insufficient funds. Need ${total_cost}, have ${user.balance}"
                )

            # Deduct balance
            user.balance -= total_cost

            # Update or create portfolio position
            pos_result = await db.execute(
                select(Portfolio)
                .where(Portfolio.user_id == user_id, Portfolio.ticker == trade.ticker)
                .with_for_update()
            )
            position = pos_result.scalar_one_or_none()

            if position:
                # Update average price
                total_shares = position.shares + validated_shares
                total_value = (position.avg_price * position.shares) + (
                    stock.price * validated_shares
                )
                position.avg_price = total_value / total_shares
                position.shares = total_shares
                position.updated_at = datetime.utcnow()
            else:
                position = Portfolio(
                    user_id=user_id,
                    ticker=trade.ticker,
                    shares=validated_shares,
                    avg_price=stock.price,
                )
                db.add(position)

            logger.info(
                f"[{request_id}] BUY: user {user_id} bought {validated_shares} "
                f"{trade.ticker} @ ${stock.price} = ${total_cost}"
            )

            # Record trade in history
            trade_record = TradeHistory(
                user_id=user_id,
                ticker=trade.ticker,
                shares=validated_shares,
                action="buy",
                price=stock.price,
                total_cost=total_cost,
                idempotency_key=trade.idempotency_key,
            )
            db.add(trade_record)

        elif trade.action == "sell":
            # Get position with lock
            pos_result = await db.execute(
                select(Portfolio)
                .where(Portfolio.user_id == user_id, Portfolio.ticker == trade.ticker)
                .with_for_update()
            )
            position = pos_result.scalar_one_or_none()

            if not position or position.shares < validated_shares:
                raise HTTPException(
                    400,
                    f"Insufficient shares. Have {position.shares if position else 0}, need {validated_shares}",
                )

            # Add balance
            user.balance += total_cost

            # Update position
            position.shares -= validated_shares
            position.updated_at = datetime.utcnow()

            if position.shares == 0:
                await db.delete(position)

            logger.info(
                f"[{request_id}] SELL: user {user_id} sold {validated_shares} "
                f"{trade.ticker} @ ${stock.price} = ${total_cost}"
            )

            # Record trade in history
            trade_record = TradeHistory(
                user_id=user_id,
                ticker=trade.ticker,
                shares=validated_shares,
                action="sell",
                price=stock.price,
                total_cost=total_cost,
                idempotency_key=trade.idempotency_key,
            )
            db.add(trade_record)

        # Commit transaction (releases all locks)
        await db.commit()

    # Audit log trade execution
    await audit_logger.log_trade_executed(
        user_id=user_id,
        ticker=trade.ticker,
        action=trade.action,
        shares=validated_shares,
        price=stock.price,
        total_cost=total_cost,
        request_id=request_id,
        idempotency_key=trade.idempotency_key,
    )

    # Publish event
    await publish_event(
        "portfolio.updated",
        {
            "user_id": user_id,
            "ticker": trade.ticker,
            "action": trade.action,
            "shares": validated_shares,
            "price": stock.price,
        },
    )

    # Invalidate cache
    await delete_cache(f"portfolio:{user_id}")

    return {
        "status": "success",
        "action": trade.action,
        "ticker": trade.ticker,
        "shares": validated_shares,
        "price": round(stock.price, 2),
        "total": round(total_cost, 2),
        "new_balance": round(user.balance, 2),
    }


@router.get("/stocks")
async def get_stocks(db: AsyncSession = Depends(get_db)):
    """Get all available stocks"""
    await init_stocks(db)

    cache_key = "stocks:all"
    cached = await get_cache(cache_key)
    if cached:
        return cached

    result = await db.execute(select(Stock))
    stocks = result.scalars().all()

    stock_list = []
    for stock in stocks:
        try:
            current_price = market_data.get_current_price(stock.ticker)
            change_pct = market_data.get_change_percent(stock.ticker)
            stock.price = current_price
            stock.change_percent = change_pct

            all_stocks_data = market_data.get_all_stocks()
            stock_data = next(
                (s for s in all_stocks_data if s["ticker"] == stock.ticker), None
            )
            if stock_data:
                stock.volume = stock_data["volume"]

            stock_list.append(
                {
                    "ticker": stock.ticker,
                    "name": stock.name,
                    "price": round(stock.price, 2),
                    "change_percent": round(stock.change_percent, 2),
                    "volume": stock.volume,
                    "market_cap": stock.market_cap,
                    "sector": stock.sector,
                }
            )
        except ValueError as e:
            logger.warning(f"Skipping unknown ticker {stock.ticker}: {e}")
            continue

    await db.commit()
    await set_cache(cache_key, stock_list, ttl=30)

    return stock_list


@router.get("/stock/{ticker}")
async def get_stock_detail(ticker: str, db: AsyncSession = Depends(get_db)):
    """Get detailed stock information"""
    result = await db.execute(select(Stock).where(Stock.ticker == ticker))
    stock = result.scalar_one_or_none()

    if not stock:
        raise HTTPException(404, "Stock not found")

    history = market_data.get_historical_prices(ticker, days=30)
    metrics = market_data.get_stock_metrics(ticker)

    return {
        "ticker": stock.ticker,
        "name": stock.name,
        "price": round(stock.price, 2),
        "change_percent": round(stock.change_percent, 2),
        "volume": stock.volume,
        "market_cap": stock.market_cap,
        "sector": stock.sector,
        "history": history,
        "pe_ratio": metrics["pe_ratio"],
        "dividend_yield": metrics["dividend_yield"],
        "52w_high": metrics["52w_high"],
        "52w_low": metrics["52w_low"],
    }


@router.get("/recommendations")
async def get_recommendations(db: AsyncSession = Depends(get_db)):
    """Get stock recommendations"""
    await init_stocks(db)

    result = await db.execute(select(Stock).limit(5))
    stocks = result.scalars().all()

    recommendations = []
    for stock in stocks:
        try:
            recommendation = market_data.get_stock_recommendation(stock.ticker)
            recommendations.append(recommendation)
        except ValueError as e:
            logger.warning(f"Could not get recommendation for {stock.ticker}: {e}")
            continue

    return recommendations
