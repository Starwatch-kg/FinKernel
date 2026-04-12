"""Shared SQLAlchemy models"""

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class TransactionType(str, enum.Enum):
    income = "income"
    expense = "expense"


class TransactionCategory(str, enum.Enum):
    food = "food"
    transport = "transport"
    entertainment = "entertainment"
    education = "education"
    salary = "salary"
    other = "other"


class RiskLevel(str, enum.Enum):
    safe = "safe"
    warning = "warning"
    danger = "danger"
    critical = "critical"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True)
    password_hash = Column(String)
    balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Onboarding profile fields
    monthly_income = Column(Float, nullable=True)
    financial_goal = Column(String, nullable=True)  # purchase, emergency, invest, debt, control
    savings_target_percent = Column(Float, nullable=True)
    income_frequency = Column(String, nullable=True)  # monthly, biweekly, weekly, irregular
    onboarding_completed = Column(Boolean, default=False)
    onboarding_completed_at = Column(DateTime, nullable=True)

    transactions = relationship("Transaction", back_populates="user")
    predictions = relationship("Prediction", back_populates="user")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        # Composite index for common queries (user_id + timestamp)
        Index('idx_user_timestamp', 'user_id', 'timestamp'),
    )
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    amount = Column(Float)
    type = Column(Enum(TransactionType))
    category = Column(Enum(TransactionCategory))
    description = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    idempotency_key = Column(
        String, unique=True, nullable=True, index=True
    )  # For idempotent operations
    user = relationship("User", back_populates="transactions")


class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    days_left = Column(Float, nullable=True)
    predicted_date = Column(DateTime, nullable=True)
    risk_level = Column(Enum(RiskLevel))
    confidence = Column(Float)
    features = Column(JSON)
    recommendation = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    is_active = Column(Boolean, default=True, index=True)
    user = relationship("User", back_populates="predictions")


class Stock(Base):
    __tablename__ = "stocks"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, unique=True, index=True)
    name = Column(String)
    price = Column(Float)
    change_percent = Column(Float)
    volume = Column(Integer)
    market_cap = Column(Float, nullable=True)
    sector = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Portfolio(Base):
    __tablename__ = "portfolios"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    ticker = Column(String, index=True)
    shares = Column(Integer)
    avg_price = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TradeHistory(Base):
    __tablename__ = "trade_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    ticker = Column(String, index=True)
    shares = Column(Integer)
    action = Column(String)  # "buy" or "sell"
    price = Column(Float)
    total_cost = Column(Float)
    idempotency_key = Column(
        String, unique=True, nullable=True, index=True
    )  # For idempotent operations
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class Module(Base):
    __tablename__ = "modules"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String, nullable=True)
    icon = Column(String, nullable=True)
    order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)


class Lesson(Base):
    __tablename__ = "lessons"
    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id"), index=True)
    title = Column(String)
    content = Column(String)
    duration_minutes = Column(Integer, default=5)
    xp_reward = Column(Integer, default=10)
    order = Column(Integer, default=0)
    questions = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)


class UserProgress(Base):
    __tablename__ = "user_progress"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), index=True)
    completed = Column(Boolean, default=False)
    score = Column(Integer, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Achievement(Base):
    __tablename__ = "achievements"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    title = Column(String)
    description = Column(String)
    icon = Column(String, nullable=True)
    xp_reward = Column(Integer, default=0)
    unlocked_at = Column(DateTime, default=datetime.utcnow)


class DailyMission(Base):
    __tablename__ = "daily_missions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    title = Column(String)
    description = Column(String)
    progress = Column(Integer, default=0)
    target = Column(Integer)
    xp_reward = Column(Integer, default=5)
    completed = Column(Boolean, default=False)
    date = Column(DateTime, default=datetime.utcnow, index=True)


class MarketEvent(Base):
    __tablename__ = "market_events"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    impact = Column(String)
    options = Column(JSON)
    correct_option = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)


class UserMarketResponse(Base):
    __tablename__ = "user_market_responses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    event_id = Column(Integer, ForeignKey("market_events.id"), index=True)
    action = Column(String)
    is_correct = Column(Boolean, nullable=True)
    xp_earned = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class AdaptiveProfile(Base):
    __tablename__ = "adaptive_profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True)
    mastery_scores = Column(JSON, default={})
    learning_velocity = Column(Float, default=1.0)
    preferred_difficulty = Column(String, default="medium")
    weak_topics = Column(JSON, default=[])
    strong_topics = Column(JSON, default=[])
    total_questions = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AdaptiveAnswer(Base):
    __tablename__ = "adaptive_answers"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    topic = Column(String, index=True)
    question_id = Column(String)
    is_correct = Column(Boolean)
    time_ms = Column(Integer, default=0)
    source = Column(String, default="lesson")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class DiaryEntry(Base):
    __tablename__ = "diary_entries"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    content = Column(String)
    mood = Column(String, nullable=True)
    tags = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
