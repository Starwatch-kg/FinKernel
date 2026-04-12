"""Seed test data"""

import asyncio
import random
import sys
from datetime import datetime, timedelta

sys.path.append("/app")

from shared.db import async_session
from shared.models import Transaction, User


async def seed():
    print("🌱 Seeding database...")
    async with async_session() as session:
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="hashed",
            balance=5000.0,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        now = datetime.utcnow()
        transactions = []

        transactions.append(
            Transaction(
                user_id=user.id,
                amount=10000.0,
                type="income",
                category="salary",
                description="Monthly salary",
                timestamp=now - timedelta(days=30),
            )
        )

        for i in range(25):
            transactions.append(
                Transaction(
                    user_id=user.id,
                    amount=round(random.uniform(50, 500), 2),
                    type="expense",
                    category=random.choice(["food", "transport", "entertainment"]),
                    description=f"Expense {i+1}",
                    timestamp=now - timedelta(days=random.randint(0, 29)),
                )
            )

        session.add_all(transactions)
        await session.commit()

        print(f"✓ Created user: {user.username} (id={user.id})")
        print(f"✓ Created {len(transactions)} transactions")

    print("✅ Database seeded")


if __name__ == "__main__":
    asyncio.run(seed())
