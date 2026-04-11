"""Database models with security constraints"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean, JSON, CheckConstraint, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

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
    email = Column(String, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    balance = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    transactions = relationship("Transaction", back_populates="user")
    predictions = relationship("Prediction", back_populates="user")

    __table_args__ = (
        CheckConstraint('balance >= 0', name='check_balance_non_negative'),
        CheckConstraint('length(password_hash) > 0', name='check_password_hash_not_empty'),
    )


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    category = Column(Enum(TransactionCategory), nullable=False)
    description = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    user = relationship("User", back_populates="transactions")

    __table_args__ = (
        CheckConstraint('amount > 0', name='check_amount_positive'),
        Index('idx_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_user_type', 'user_id', 'type'),
    )


class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    days_left = Column(Float, nullable=True)
    predicted_date = Column(DateTime, nullable=True)
    risk_level = Column(Enum(RiskLevel), nullable=False)
    confidence = Column(Float, nullable=False)
    features = Column(JSON)
    recommendation = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    user = relationship("User", back_populates="predictions")

    __table_args__ = (
        CheckConstraint('confidence >= 0 AND confidence <= 1', name='check_confidence_range'),
        CheckConstraint('days_left IS NULL OR days_left >= 0', name='check_days_left_non_negative'),
        Index('idx_user_active', 'user_id', 'is_active'),
    )


class Stock(Base):
    __tablename__ = "stocks"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    change_percent = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    market_cap = Column(Float, nullable=True)
    sector = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint('price > 0', name='check_price_positive'),
        CheckConstraint('volume >= 0', name='check_volume_non_negative'),
    )


class Portfolio(Base):
    __tablename__ = "portfolios"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    ticker = Column(String, index=True, nullable=False)
    shares = Column(Integer, nullable=False)
    avg_price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint('shares > 0', name='check_shares_positive'),
        CheckConstraint('avg_price > 0', name='check_avg_price_positive'),
        Index('idx_user_ticker', 'user_id', 'ticker'),
    )


class Module(Base):
    __tablename__ = "modules"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    icon = Column(String, nullable=True)
    order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, index=True)


class Lesson(Base):
    __tablename__ = "lessons"
    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), index=True, nullable=False)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    duration_minutes = Column(Integer, default=5, nullable=False)
    xp_reward = Column(Integer, default=10, nullable=False)
    order = Column(Integer, default=0, nullable=False)
    questions = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, index=True)

    __table_args__ = (
        CheckConstraint('duration_minutes > 0', name='check_duration_positive'),
        CheckConstraint('xp_reward >= 0', name='check_xp_non_negative'),
    )


class UserProgress(Base):
    __tablename__ = "user_progress"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), index=True, nullable=False)
    completed = Column(Boolean, default=False, nullable=False)
    score = Column(Integer, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint('score IS NULL OR (score >= 0 AND score <= 100)', name='check_score_range'),
        Index('idx_user_lesson', 'user_id', 'lesson_id'),
    )


class Achievement(Base):
    __tablename__ = "achievements"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    icon = Column(String, nullable=True)
    xp_reward = Column(Integer, default=0, nullable=False)
    unlocked_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint('xp_reward >= 0', name='check_achievement_xp_non_negative'),
    )


class DailyMission(Base):
    __tablename__ = "daily_missions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    progress = Column(Integer, default=0, nullable=False)
    target = Column(Integer, nullable=False)
    xp_reward = Column(Integer, default=5, nullable=False)
    completed = Column(Boolean, default=False, nullable=False)
    date = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)

    __table_args__ = (
        CheckConstraint('progress >= 0', name='check_progress_non_negative'),
        CheckConstraint('target > 0', name='check_target_positive'),
        CheckConstraint('xp_reward >= 0', name='check_mission_xp_non_negative'),
    )


class MarketEvent(Base):
    __tablename__ = "market_events"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    impact = Column(String, nullable=False)
    options = Column(JSON, nullable=False)
    correct_option = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, index=True)


class UserMarketResponse(Base):
    __tablename__ = "user_market_responses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    event_id = Column(Integer, ForeignKey("market_events.id", ondelete="CASCADE"), index=True, nullable=False)
    action = Column(String, nullable=False)
    is_correct = Column(Boolean, nullable=True)
    xp_earned = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint('xp_earned >= 0', name='check_response_xp_non_negative'),
    )


class AdaptiveProfile(Base):
    __tablename__ = "adaptive_profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    mastery_scores = Column(JSON, default={})
    learning_velocity = Column(Float, default=1.0, nullable=False)
    preferred_difficulty = Column(String, default="medium", nullable=False)
    weak_topics = Column(JSON, default=[])
    strong_topics = Column(JSON, default=[])
    total_questions = Column(Integer, default=0, nullable=False)
    correct_answers = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint('learning_velocity > 0', name='check_velocity_positive'),
        CheckConstraint('total_questions >= 0', name='check_total_questions_non_negative'),
        CheckConstraint('correct_answers >= 0', name='check_correct_answers_non_negative'),
        CheckConstraint('correct_answers <= total_questions', name='check_correct_lte_total'),
    )


class AdaptiveAnswer(Base):
    __tablename__ = "adaptive_answers"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    topic = Column(String, index=True, nullable=False)
    question_id = Column(String, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    time_ms = Column(Integer, default=0, nullable=False)
    source = Column(String, default="lesson", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)

    __table_args__ = (
        CheckConstraint('time_ms >= 0', name='check_time_non_negative'),
        Index('idx_user_topic', 'user_id', 'topic'),
    )


class DiaryEntry(Base):
    __tablename__ = "diary_entries"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    content = Column(String, nullable=False)
    mood = Column(String, nullable=True)
    tags = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
