"""Portfolio Service - Integrated into Transaction Service"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
import sys
sys.path.append('/app')

from shared.db import get_db
from shared.models import User, Portfolio, Stock, TradeHistory
from shared.redis import publish_event, get_cache, set_cache, delete_cache
from shared.market_data import get_market_data_provider
from shared.logger import setup_logger
from pydantic import BaseModel

logger = setup_logger("portfolio")
market_data = get_market_data_provider()

router = APIRouter()


class TradeRequest(BaseModel):
    userId: str
    ticker: str
    shares: int
    action: str  # "buy" or "sell"
    idempotency_key: str = None  # Client-provided UUID for idempotency


# Initialize stock data
STOCK_DATA = [
    {"ticker": "AAPL", "name": "Apple Inc.", "price": 178.50, "sector": "Technology"},
    {"ticker": "GOOGL", "name": "Alphabet Inc.", "price": 142.30, "sector": "Technology"},
    {"ticker": "MSFT", "name": "Microsoft Corp.", "price": 415.20, "sector": "Technology"},
    {"ticker": "TSLA", "name": "Tesla Inc.", "price": 248.90, "sector": "Automotive"},
    {"ticker": "AMZN", "name": "Amazon.com Inc.", "price": 178.25, "sector": "E-commerce"},
    {"ticker": "NVDA", "name": "NVIDIA Corp.", "price": 875.40, "sector": "Technology"},
    {"ticker": "META", "name": "Meta Platforms", "price": 485.60, "sector": "Technology"},
    {"ticker": "JPM", "name": "JPMorgan Chase", "price": 195.80, "sector": "Finance"},
    {"ticker": "V", "name": "Visa Inc.", "price": 278.30, "sector": "Finance"},
    {"ticker": "WMT", "name": "Walmart Inc.", "price": 165.40, "sector": "Retail"}
]


async def init_stocks(db: AsyncSession):
    """Initialize stock data if not exists - uses deterministic market data"""
    all_stocks = market_data.get_all_stocks()

    for stock_data in all_stocks:
        result = await db.execute(select(Stock).where(Stock.ticker == stock_data["ticker"]))
        if not result.scalar_one_or_none():
            stock = Stock(
                ticker=stock_data["ticker"],
                name=stock_data["name"],
                price=stock_data["price"],
                change_percent=stock_data["change_percent"],
                volume=stock_data["volume"],
                market_cap=stock_data["market_cap"],
                sector=stock_data["sector"]
            )
            db.add(stock)
            logger.info(f"Initialized stock: {stock_data['ticker']}")
    await db.commit()


@router.get("/portfolio")
async def get_portfolio(userId: str, db: AsyncSession = Depends(get_db)):
    user_id = int(userId) if userId.isdigit() else 1

    cache_key = f"portfolio:{user_id}"
    cached = await get_cache(cache_key)
    if cached:
        return cached

    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user_id)
    )
    positions = result.scalars().all()

    # Get current stock prices
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

            portfolio_data.append({
                "ticker": pos.ticker,
                "name": stock.name,
                "shares": pos.shares,
                "avg_price": pos.avg_price,
                "current_price": stock.price,
                "current_value": current_value,
                "profit_loss": profit_loss,
                "profit_loss_pct": profit_loss_pct,
                "sector": stock.sector
            })

            total_value += current_value
            total_cost += cost_basis

    total_profit_loss = total_value - total_cost
    total_profit_loss_pct = (total_profit_loss / total_cost * 100) if total_cost > 0 else 0

    response = {
        "positions": portfolio_data,
        "total_value": total_value,
        "total_cost": total_cost,
        "total_profit_loss": total_profit_loss,
        "total_profit_loss_pct": total_profit_loss_pct,
        "cash": 0  # Will be fetched from user balance
    }

    await set_cache(cache_key, response, ttl=60)
    return response


@router.post("/trade")
async def execute_trade(trade: TradeRequest, db: AsyncSession = Depends(get_db)):
    user_id = int(trade.userId) if trade.userId.isdigit() else 1

    # Check for idempotency key - if provided, check if trade already executed
    if trade.idempotency_key:
        result = await db.execute(
            select(TradeHistory).where(TradeHistory.idempotency_key == trade.idempotency_key)
        )
        existing_trade = result.scalar_one_or_none()
        if existing_trade:
            # Return existing trade result (idempotent response)
            return {
                "status": "success",
                "action": existing_trade.action,
                "ticker": existing_trade.ticker,
                "shares": existing_trade.shares,
                "price": existing_trade.price,
                "total": existing_trade.total_cost,
                "new_balance": None,  # Don't recalculate, just acknowledge
                "idempotent": True
            }

    async with db.begin():
        # Lock user row first to prevent concurrent balance modifications
        user_result = await db.execute(
            select(User).where(User.id == user_id).with_for_update()
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(404, "User not found")

        # Get stock (read-only, no lock needed)
        stock_result = await db.execute(select(Stock).where(Stock.ticker == trade.ticker))
        stock = stock_result.scalar_one_or_none()
        if not stock:
            raise HTTPException(404, "Stock not found")

        # Update stock price with deterministic market data
        current_price = market_data.get_current_price(trade.ticker)
        change_pct = market_data.get_change_percent(trade.ticker)
        stock.price = current_price
        stock.change_percent = change_pct

        # Calculate cost AFTER getting current price
        total_cost = stock.price * trade.shares

        if trade.action == "buy":
            # Check balance INSIDE lock
            if user.balance < total_cost:
                raise HTTPException(400, "Insufficient funds")

            user.balance -= total_cost

            # Lock portfolio position if exists
            pos_result = await db.execute(
                select(Portfolio).where(
                    Portfolio.user_id == user_id,
                    Portfolio.ticker == trade.ticker
                ).with_for_update()
            )
            position = pos_result.scalar_one_or_none()

            if position:
                # Update average price
                total_shares = position.shares + trade.shares
                total_value = (position.avg_price * position.shares) + (stock.price * trade.shares)
                position.avg_price = total_value / total_shares
                position.shares = total_shares
                position.updated_at = datetime.utcnow()
            else:
                position = Portfolio(
                    user_id=user_id,
                    ticker=trade.ticker,
                    shares=trade.shares,
                    avg_price=stock.price
                )
                db.add(position)

        elif trade.action == "sell":
            # Lock portfolio position
            pos_result = await db.execute(
                select(Portfolio).where(
                    Portfolio.user_id == user_id,
                    Portfolio.ticker == trade.ticker
                ).with_for_update()
            )
            position = pos_result.scalar_one_or_none()

            # Check shares INSIDE lock
            if not position or position.shares < trade.shares:
                raise HTTPException(400, "Insufficient shares")

            user.balance += total_cost
            position.shares -= trade.shares

            if position.shares == 0:
                await db.delete(position)

        else:
            raise HTTPException(400, "Invalid action")

        # Record trade in history for idempotency
        trade_record = TradeHistory(
            user_id=user_id,
            ticker=trade.ticker,
            shares=trade.shares,
            action=trade.action,
            price=stock.price,
            total_cost=total_cost,
            idempotency_key=trade.idempotency_key
        )
        db.add(trade_record)

        await db.flush()

    # Publish event AFTER successful commit
    await publish_event("portfolio.updated", {
        "user_id": user_id,
        "ticker": trade.ticker,
        "action": trade.action,
        "shares": trade.shares,
        "price": stock.price
    })

    # Invalidate cache
    from shared.redis import delete_cache
    await delete_cache(f"portfolio:{user_id}")

    return {
        "status": "success",
        "action": trade.action,
        "ticker": trade.ticker,
        "shares": trade.shares,
        "price": stock.price,
        "total": total_cost,
        "new_balance": user.balance
    }


@router.get("/stocks")
async def get_stocks(userId: str, db: AsyncSession = Depends(get_db)):
    await init_stocks(db)

    cache_key = "stocks:all"
    cached = await get_cache(cache_key)
    if cached:
        return cached

    result = await db.execute(select(Stock))
    stocks = result.scalars().all()

    # Update prices with deterministic market data
    stock_list = []
    for stock in stocks:
        try:
            current_price = market_data.get_current_price(stock.ticker)
            change_pct = market_data.get_change_percent(stock.ticker)
            stock.price = current_price
            stock.change_percent = change_pct

            # Get deterministic volume
            all_stocks_data = market_data.get_all_stocks()
            stock_data = next((s for s in all_stocks_data if s["ticker"] == stock.ticker), None)
            if stock_data:
                stock.volume = stock_data["volume"]

            stock_list.append({
                "ticker": stock.ticker,
                "name": stock.name,
                "price": round(stock.price, 2),
                "change_percent": round(stock.change_percent, 2),
                "volume": stock.volume,
                "market_cap": stock.market_cap,
                "sector": stock.sector
            })
        except ValueError as e:
            logger.warning(f"Skipping unknown ticker {stock.ticker}: {e}")
            continue

    await db.commit()
    await set_cache(cache_key, stock_list, ttl=30)

    return stock_list


@router.get("/stock/{ticker}")
async def get_stock_detail(ticker: str, userId: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Stock).where(Stock.ticker == ticker))
    stock = result.scalar_one_or_none()

    if not stock:
        raise HTTPException(404, "Stock not found")

    # Get deterministic historical data
    history = market_data.get_historical_prices(ticker, days=30)

    # Get deterministic metrics
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
        "52w_low": metrics["52w_low"]
    }


@router.post("/check-portfolio")
async def check_portfolio(userId: str, db: AsyncSession = Depends(get_db)):
    """Check portfolio performance and trigger achievements"""
    user_id = int(userId) if userId.isdigit() else 1

    portfolio = await get_portfolio(userId, db)

    # Simple performance check
    performance = {
        "total_value": portfolio["total_value"],
        "profit_loss": portfolio["total_profit_loss"],
        "profit_loss_pct": portfolio["total_profit_loss_pct"],
        "status": "profitable" if portfolio["total_profit_loss"] > 0 else "loss"
    }

    return performance


@router.post("/reset-portfolio")
async def reset_portfolio(userId: str, db: AsyncSession = Depends(get_db)):
    """Reset user portfolio (sell all positions)"""
    user_id = int(userId) if userId.isdigit() else 1

    async with db.begin():
        # Lock user row first
        user_result = await db.execute(
            select(User).where(User.id == user_id).with_for_update()
        )
        user = user_result.scalar_one_or_none()

        if not user:
            raise HTTPException(404, "User not found")

        # Lock all portfolio positions
        result = await db.execute(
            select(Portfolio).where(Portfolio.user_id == user_id).with_for_update()
        )
        positions = result.scalars().all()

        total_value = 0
        for pos in positions:
            stock_result = await db.execute(select(Stock).where(Stock.ticker == pos.ticker))
            stock = stock_result.scalar_one_or_none()
            if stock:
                total_value += stock.price * pos.shares
            await db.delete(pos)

        # Update balance atomically
        user.balance += total_value
        await db.flush()

    from shared.redis import delete_cache
    await delete_cache(f"portfolio:{user_id}")

    return {
        "status": "reset",
        "cash_returned": total_value,
        "new_balance": user.balance
    }


@router.get("/recommendations")
async def get_recommendations(userId: str, db: AsyncSession = Depends(get_db)):
    """Get deterministic stock recommendations based on market data"""
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
