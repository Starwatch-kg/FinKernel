"""Database configuration with enhanced security"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://finuser:finpass123@postgres:5432/financedb")

# Enhanced engine configuration
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,
    # Security: Set transaction isolation level
    isolation_level="REPEATABLE READ",
    # Connection arguments for security
    connect_args={
        "server_settings": {
            "application_name": "fintech_backend",
            "jit": "off"  # Disable JIT for consistent performance
        },
        "command_timeout": 60,
        "timeout": 10
    }
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)


async def get_db():
    """Get database session with automatic cleanup"""
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
