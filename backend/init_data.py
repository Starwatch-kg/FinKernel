"""
Скрипт инициализации тестовых данных
"""
import asyncio
from sqlalchemy import select

from backend.core import get_db, init_db
from backend.models import (
    User, Module, Lesson, Achievement, Stock, DailyMission
)


async def init_test_data():
    """Инициализация тестовых данных"""
    await init_db()

    async for db in get_db():
        # Проверяем, есть ли уже данные
        result = await db.execute(select(User).limit(1))
        if result.scalar_one_or_none():
            print("✅ Данные уже инициализированы")
            return

        print("📊 Создание тестовых данных...")

        # Модули обучения
        modules_data = [
            {
                "title": "Основы финансов",
                "description": "Базовые понятия финансовой грамотности",
                "icon": "💰",
                "order": 1,
                "required_level": 1
            },
            {
                "title": "Бюджетирование",
                "description": "Учимся планировать расходы",
                "icon": "📊",
                "order": 2,
                "required_level": 1
            },
            {
                "title": "Инвестиции",
                "description": "Как заставить деньги работать",
                "icon": "📈",
                "order": 3,
                "required_level": 3
            }
        ]

        for mod_data in modules_data:
            module = Module(**mod_data)
            db.add(module)

        await db.commit()

        # Акции
        stocks_data = [
            {"ticker": "AAPL", "name": "Apple Inc.", "current_price": 150.0, "change_percent": 2.5, "sector": "Technology"},
            {"ticker": "GOOGL", "name": "Alphabet Inc.", "current_price": 120.0, "change_percent": -1.2, "sector": "Technology"},
            {"ticker": "TSLA", "name": "Tesla Inc.", "current_price": 200.0, "change_percent": 5.0, "sector": "Automotive"},
            {"ticker": "MSFT", "name": "Microsoft Corp.", "current_price": 300.0, "change_percent": 1.8, "sector": "Technology"},
        ]

        for stock_data in stocks_data:
            stock = Stock(**stock_data)
            db.add(stock)

        # Достижения
        achievements_data = [
            {
                "title": "Первые шаги",
                "description": "Добавьте первую транзакцию",
                "icon": "🎯",
                "xp_reward": 50,
                "condition_type": "transaction_count",
                "condition_value": 1
            },
            {
                "title": "Ученик",
                "description": "Пройдите первый урок",
                "icon": "📚",
                "xp_reward": 100,
                "condition_type": "lesson_completed",
                "condition_value": 1
            },
            {
                "title": "Инвестор",
                "description": "Купите первую акцию",
                "icon": "💼",
                "xp_reward": 150,
                "condition_type": "stock_purchased",
                "condition_value": 1
            }
        ]

        for ach_data in achievements_data:
            achievement = Achievement(**ach_data)
            db.add(achievement)

        await db.commit()
        print("✅ Тестовые данные созданы")


if __name__ == "__main__":
    asyncio.run(init_test_data())
