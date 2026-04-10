from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean, Text, JSON
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import enum
import os

Base = declarative_base()

class TransactionCategory(enum.Enum):
    food = "food"
    transport = "transport"
    entertainment = "entertainment"
    education = "education"
    other = "other"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    name = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)
    current_balance = Column(Float, default=10000.0)
    financial_score = Column(Integer, default=500)
    level = Column(Integer, default=1)
    xp = Column(Integer, default=0)
    streak = Column(Integer, default=0)
    last_activity = Column(DateTime, default=datetime.utcnow)
    onboarding_completed = Column(Boolean, default=False)
    onboarding_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    transactions = relationship("Transaction", back_populates="user")
    achievements = relationship("UserAchievement", back_populates="user")
    lesson_progress = relationship("LessonProgress", back_populates="user")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float)
    category = Column(Enum(TransactionCategory))
    description = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="transactions")

class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    icon = Column(String)
    xp_reward = Column(Integer, default=0)
    condition_type = Column(String)  # transaction_count, balance_reached, streak, etc.
    condition_value = Column(Integer)

class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    achievement_id = Column(Integer, ForeignKey("achievements.id"))
    unlocked_at = Column(DateTime, default=datetime.utcnow)
    progress = Column(Integer, default=0)

    user = relationship("User", back_populates="achievements")
    achievement = relationship("Achievement")

class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    icon = Column(String)
    order = Column(Integer)
    required_level = Column(Integer, default=1)

    lessons = relationship("Lesson", back_populates="module")

class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id"))
    title = Column(String)
    description = Column(String)
    content = Column(Text)
    questions = Column(JSON)  # Список вопросов с вариантами ответов
    xp_reward = Column(Integer, default=50)
    order = Column(Integer)
    required_level = Column(Integer, default=1)

    module = relationship("Module", back_populates="lessons")
    progress = relationship("LessonProgress", back_populates="lesson")

class LessonProgress(Base):
    __tablename__ = "lesson_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    lesson_id = Column(Integer, ForeignKey("lessons.id"))
    completed = Column(Boolean, default=False)
    score = Column(Integer, default=0)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="lesson_progress")
    lesson = relationship("Lesson", back_populates="progress")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://finuser:finpass123@localhost:5432/financedb")

engine = create_async_engine(DATABASE_URL, echo=True)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with async_session_maker() as session:
        yield session
