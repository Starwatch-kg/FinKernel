"""Database initialization"""

import asyncio
import sys

sys.path.append("/app")

from shared.db import engine
from shared.models import Base


async def init_db():
    print("🔧 Initializing database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database initialized")


if __name__ == "__main__":
    asyncio.run(init_db())
