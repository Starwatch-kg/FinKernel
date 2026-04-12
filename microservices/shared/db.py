"""Shared database connection"""

import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://finuser:finpass123@postgres:5432/financedb"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=20,  # Max 20 connections in pool
    max_overflow=10,  # Allow 10 overflow connections
    pool_timeout=30,  # 30 second timeout to get connection
    pool_recycle=3600,  # Recycle connections after 1 hour
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with async_session() as session:
        yield session
