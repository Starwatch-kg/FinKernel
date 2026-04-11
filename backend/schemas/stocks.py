"""
Pydantic схемы для акций и торговли
"""
from pydantic import BaseModel
from typing import List, Optional


class TradeRequest(BaseModel):
    userId: str
    ticker: str
    shares: int
    action: str  # buy or sell


class StockResponse(BaseModel):
    ticker: str
    name: str
    price: float
    change: float
    sector: Optional[str] = None


class PortfolioResponse(BaseModel):
    cash: float
    stocks: List[dict]
    total_value: float


class MarketEventActionRequest(BaseModel):
    userId: str
    eventId: int
    action: str


class MarketEventResponse(BaseModel):
    id: int
    title: str
    description: str
    event_type: str
    impact: str
    options: List[dict]
    expires_at: str
