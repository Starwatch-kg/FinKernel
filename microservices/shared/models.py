"""Shared SQLAlchemy models"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean, JSON
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
    email = Column(String, unique=True)
    password_hash = Column(String)
    balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    transactions = relationship("Transaction", back_populates="user")
    predictions = relationship("Prediction", back_populates="user")


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    amount = Column(Float)
    type = Column(Enum(TransactionType))
    category = Column(Enum(TransactionCategory))
    description = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
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
