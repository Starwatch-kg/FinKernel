"""Shared Pydantic schemas"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TransactionType(str, Enum):
    income = "income"
    expense = "expense"


class TransactionCategory(str, Enum):
    food = "food"
    transport = "transport"
    entertainment = "entertainment"
    education = "education"
    salary = "salary"
    other = "other"


class RiskLevel(str, Enum):
    safe = "safe"
    warning = "warning"
    danger = "danger"
    critical = "critical"


class TransactionCreate(BaseModel):
    user_id: int
    amount: float = Field(gt=0)
    type: TransactionType
    category: TransactionCategory
    description: Optional[str] = None
    idempotency_key: Optional[str] = None  # Client-provided UUID for idempotency


class TransactionResponse(BaseModel):
    id: int
    user_id: int
    amount: float
    type: str
    category: str
    description: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True


class PredictionResponse(BaseModel):
    id: int
    user_id: int
    days_left: Optional[float]
    predicted_date: Optional[datetime]
    risk_level: str
    confidence: float
    recommendation: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class DashboardResponse(BaseModel):
    user_id: int
    balance: float
    total_income: float
    total_expenses: float
    transaction_count: int
    prediction: Optional[PredictionResponse]
    recent_transactions: list[TransactionResponse]
