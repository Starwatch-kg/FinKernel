"""
Pydantic схемы для транзакций
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AddTransactionRequest(BaseModel):
    userId: str
    amount: float
    category: str
    description: Optional[str] = None


class TransactionResponse(BaseModel):
    id: int
    amount: float
    category: str
    timestamp: datetime


class ChatRequest(BaseModel):
    user_id: int
    message: str


class ChatResponse(BaseModel):
    success: bool
    message: str
    transaction: dict = None


class PurchaseEvaluationRequest(BaseModel):
    user_id: int
    wish: str


class PurchaseEvaluationResponse(BaseModel):
    necessity_score: int
    verdict: str
    reasoning: str
    current_balance: float
