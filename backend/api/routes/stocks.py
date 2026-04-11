"""
Роутер для акций и торговли
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime
import logging

from backend.core import get_db
from backend.models import User, Stock, UserStock, MarketEvent, UserMarketEventAction
from backend.schemas import (
    TradeRequest,
    StockResponse,
    PortfolioResponse,
    MarketEventActionRequest,
    MarketEventResponse,
)

router = APIRouter(prefix="/api", tags=["stocks"])
logger = logging.getLogger(__name__)


@router.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio(userId: str, db: AsyncSession = Depends(get_db)):
    """Портфолио пользователя"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(UserStock, Stock)
        .join(Stock)
        .where(UserStock.user_id == user.id)
        .where(UserStock.shares > 0)
    )
    user_stocks = result.all()

    stocks_list = []
    total_stocks_value = 0.0

    for user_stock, stock in user_stocks:
        current_value = stock.current_price * user_stock.shares
        profit = (stock.current_price - user_stock.avg_buy_price) * user_stock.shares
        profit_percent = ((stock.current_price - user_stock.avg_buy_price) / user_stock.avg_buy_price * 100) if user_stock.avg_buy_price > 0 else 0

        stocks_list.append({
            "ticker": stock.ticker,
            "name": stock.name,
            "shares": user_stock.shares,
            "avg_price": user_stock.avg_buy_price,
            "current_price": stock.current_price,
            "value": current_value,
            "profit": profit,
            "profit_percent": profit_percent
        })
        total_stocks_value += current_value

    total_value = user.current_balance + total_stocks_value

    return PortfolioResponse(
        cash=user.current_balance,
        stocks=stocks_list,
        total_value=total_value
    )


@router.post("/check-portfolio")
async def check_portfolio(userId: str, db: AsyncSession = Depends(get_db)):
    """Проверить портфолио"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"status": "ok", "user_id": user.id}


@router.get("/stocks")
async def get_stocks(userId: str, db: AsyncSession = Depends(get_db)):
    """Список акций"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(select(Stock))
    stocks = result.scalars().all()

    stocks_list = []
    for stock in stocks:
        stocks_list.append({
            "ticker": stock.ticker,
            "name": stock.name,
            "price": stock.current_price,
            "change": stock.change_percent,
            "sector": stock.sector
        })

    return stocks_list


@router.get("/stock/{ticker}")
async def get_stock_detail(ticker: str, userId: str, db: AsyncSession = Depends(get_db)):
    """Детали акции"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(select(Stock).where(Stock.ticker == ticker))
    stock = result.scalar_one_or_none()

    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    result = await db.execute(
        select(UserStock)
        .where(UserStock.user_id == user.id)
        .where(UserStock.stock_id == stock.id)
    )
    user_stock = result.scalar_one_or_none()

    return {
        "ticker": stock.ticker,
        "name": stock.name,
        "price": stock.current_price,
        "change": stock.change_percent,
        "sector": stock.sector,
        "description": stock.description,
        "user_shares": user_stock.shares if user_stock else 0,
        "user_avg_price": user_stock.avg_buy_price if user_stock else 0
    }


@router.post("/trade")
async def trade(request: TradeRequest, db: AsyncSession = Depends(get_db)):
    """Торговля акциями"""
    result = await db.execute(select(User).where(User.username == request.userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(select(Stock).where(Stock.ticker == request.ticker))
    stock = result.scalar_one_or_none()

    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    if request.action == "buy":
        total_cost = stock.current_price * request.shares

        if user.current_balance < total_cost:
            raise HTTPException(status_code=400, detail="Insufficient funds")

        user.current_balance -= total_cost

        result = await db.execute(
            select(UserStock)
            .where(UserStock.user_id == user.id)
            .where(UserStock.stock_id == stock.id)
        )
        user_stock = result.scalar_one_or_none()

        if user_stock:
            total_shares = user_stock.shares + request.shares
            total_value = (user_stock.avg_buy_price * user_stock.shares) + (stock.current_price * request.shares)
            user_stock.avg_buy_price = total_value / total_shares
            user_stock.shares = total_shares
        else:
            user_stock = UserStock(
                user_id=user.id,
                stock_id=stock.id,
                shares=request.shares,
                avg_buy_price=stock.current_price
            )
            db.add(user_stock)

        user.xp += 10
        user.last_activity = datetime.utcnow()

        await db.commit()

        logger.info(f"User {user.username} bought {request.shares} shares of {stock.ticker} for {total_cost}")

        return {
            "success": True,
            "message": f"Куплено {request.shares} акций {stock.ticker}",
            "new_balance": user.current_balance,
            "total_cost": total_cost
        }

    elif request.action == "sell":
        result = await db.execute(
            select(UserStock)
            .where(UserStock.user_id == user.id)
            .where(UserStock.stock_id == stock.id)
        )
        user_stock = result.scalar_one_or_none()

        if not user_stock or user_stock.shares < request.shares:
            raise HTTPException(status_code=400, detail="Insufficient shares")

        total_revenue = stock.current_price * request.shares
        user.current_balance += total_revenue
        user_stock.shares -= request.shares

        user.xp += 10
        user.last_activity = datetime.utcnow()

        await db.commit()

        logger.info(f"User {user.username} sold {request.shares} shares of {stock.ticker} for {total_revenue}")

        return {
            "success": True,
            "message": f"Продано {request.shares} акций {stock.ticker}",
            "new_balance": user.current_balance,
            "total_revenue": total_revenue
        }

    else:
        raise HTTPException(status_code=400, detail="Invalid action")


@router.post("/reset-portfolio")
async def reset_portfolio(userId: str, db: AsyncSession = Depends(get_db)):
    """Сброс портфолио"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(UserStock).where(UserStock.user_id == user.id)
    )
    user_stocks = result.scalars().all()

    for user_stock in user_stocks:
        await db.delete(user_stock)

    user.current_balance = 10000.0

    await db.commit()

    logger.info(f"Portfolio reset for user {user.username}")

    return {"success": True, "message": "Portfolio reset successfully"}


@router.get("/market-event")
async def get_market_event(userId: str, db: AsyncSession = Depends(get_db)):
    """Рыночные события"""
    result = await db.execute(select(User).where(User.username == userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.utcnow()
    result = await db.execute(
        select(MarketEvent)
        .where(MarketEvent.active == True)
        .where(MarketEvent.expires_at > now)
        .order_by(desc(MarketEvent.created_at))
        .limit(1)
    )
    event = result.scalar_one_or_none()

    if not event:
        return None

    result = await db.execute(
        select(UserMarketEventAction)
        .where(UserMarketEventAction.user_id == user.id)
        .where(UserMarketEventAction.event_id == event.id)
    )
    user_action = result.scalar_one_or_none()

    if user_action:
        return None

    return {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "event_type": event.event_type,
        "impact": event.impact,
        "ticker": event.ticker,
        "options": event.options,
        "expires_at": event.expires_at.isoformat()
    }


@router.post("/market-event/action")
async def market_event_action(request: MarketEventActionRequest, db: AsyncSession = Depends(get_db)):
    """Действие на событие"""
    result = await db.execute(select(User).where(User.username == request.userId))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(select(MarketEvent).where(MarketEvent.id == request.eventId))
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Event expired")

    result = await db.execute(
        select(UserMarketEventAction)
        .where(UserMarketEventAction.user_id == user.id)
        .where(UserMarketEventAction.event_id == event.id)
    )
    existing_action = result.scalar_one_or_none()

    if existing_action:
        raise HTTPException(status_code=400, detail="Already responded to this event")

    result_data = {}
    xp_earned = 0

    if request.action == "buy":
        if event.ticker:
            result = await db.execute(select(Stock).where(Stock.ticker == event.ticker))
            stock = result.scalar_one_or_none()

            if stock and user.current_balance >= stock.current_price:
                user.current_balance -= stock.current_price

                result = await db.execute(
                    select(UserStock)
                    .where(UserStock.user_id == user.id)
                    .where(UserStock.stock_id == stock.id)
                )
                user_stock = result.scalar_one_or_none()

                if user_stock:
                    total_shares = user_stock.shares + 1
                    total_value = (user_stock.avg_buy_price * user_stock.shares) + stock.current_price
                    user_stock.avg_buy_price = total_value / total_shares
                    user_stock.shares = total_shares
                else:
                    user_stock = UserStock(
                        user_id=user.id,
                        stock_id=stock.id,
                        shares=1,
                        avg_buy_price=stock.current_price
                    )
                    db.add(user_stock)

                result_data = {"action": "bought", "ticker": stock.ticker, "shares": 1}
                xp_earned = 50

    elif request.action == "sell":
        if event.ticker:
            result = await db.execute(select(Stock).where(Stock.ticker == event.ticker))
            stock = result.scalar_one_or_none()

            if stock:
                result = await db.execute(
                    select(UserStock)
                    .where(UserStock.user_id == user.id)
                    .where(UserStock.stock_id == stock.id)
                )
                user_stock = result.scalar_one_or_none()

                if user_stock and user_stock.shares > 0:
                    user.current_balance += stock.current_price
                    user_stock.shares -= 1
                    result_data = {"action": "sold", "ticker": stock.ticker, "shares": 1}
                    xp_earned = 50

    elif request.action == "hold":
        result_data = {"action": "hold"}
        xp_earned = 20

    user_action = UserMarketEventAction(
        user_id=user.id,
        event_id=event.id,
        action=request.action,
        result=result_data
    )
    db.add(user_action)

    user.xp += xp_earned
    user.last_activity = datetime.utcnow()

    await db.commit()

    logger.info(f"User {user.username} responded to market event {event.id} with action {request.action}")

    return {
        "success": True,
        "result": result_data,
        "xp_earned": xp_earned
    }
