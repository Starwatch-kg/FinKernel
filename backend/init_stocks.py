"""
Скрипт для инициализации акций и рыночных событий
"""
import asyncio
from datetime import datetime, timedelta
from models import (
    Stock, MarketEvent, DailyMission, AdaptiveQuestion,
    async_session_maker, init_db
)

async def init_stocks_and_events():
    """Инициализация акций, событий и вопросов"""
    await init_db()

    async with async_session_maker() as session:
        # Проверяем, есть ли уже акции
        from sqlalchemy import select
        result = await session.execute(select(Stock))
        existing_stocks = result.scalars().all()

        if len(existing_stocks) > 0:
            print(f"✅ Акции уже существуют ({len(existing_stocks)} шт.)")
        else:
            # Создаем акции
            stocks_data = [
                {
                    "ticker": "AAPL",
                    "name": "Apple Inc.",
                    "current_price": 150.0,
                    "change_percent": 2.5,
                    "sector": "Technology",
                    "description": "Производитель iPhone, iPad и Mac"
                },
                {
                    "ticker": "GOOGL",
                    "name": "Alphabet Inc.",
                    "current_price": 120.0,
                    "change_percent": 1.8,
                    "sector": "Technology",
                    "description": "Компания Google и YouTube"
                },
                {
                    "ticker": "MSFT",
                    "name": "Microsoft Corporation",
                    "current_price": 300.0,
                    "change_percent": -0.5,
                    "sector": "Technology",
                    "description": "Разработчик Windows и Office"
                },
                {
                    "ticker": "TSLA",
                    "name": "Tesla Inc.",
                    "current_price": 200.0,
                    "change_percent": 5.2,
                    "sector": "Automotive",
                    "description": "Производитель электромобилей"
                },
                {
                    "ticker": "AMZN",
                    "name": "Amazon.com Inc.",
                    "current_price": 130.0,
                    "change_percent": 1.2,
                    "sector": "E-commerce",
                    "description": "Крупнейший интернет-магазин"
                },
                {
                    "ticker": "NVDA",
                    "name": "NVIDIA Corporation",
                    "current_price": 450.0,
                    "change_percent": 3.7,
                    "sector": "Technology",
                    "description": "Производитель видеокарт и AI-чипов"
                }
            ]

            for stock_data in stocks_data:
                stock = Stock(**stock_data)
                session.add(stock)

            await session.commit()
            print(f"✅ Создано {len(stocks_data)} акций")

        # Создаем рыночное событие
        result = await session.execute(select(MarketEvent))
        existing_events = result.scalars().all()

        if len(existing_events) > 0:
            print(f"✅ События уже существуют ({len(existing_events)} шт.)")
        else:
            event = MarketEvent(
                title="📈 Рост технологического сектора",
                description="Акции технологических компаний растут на фоне новостей об AI. Что вы будете делать?",
                event_type="boom",
                impact="positive",
                ticker="NVDA",
                options=[
                    {"action": "buy", "label": "Купить акции NVIDIA"},
                    {"action": "sell", "label": "Продать акции"},
                    {"action": "hold", "label": "Ничего не делать"}
                ],
                expires_at=datetime.utcnow() + timedelta(hours=24),
                active=True
            )
            session.add(event)
            await session.commit()
            print("✅ Создано рыночное событие")

        # Создаем адаптивные вопросы
        result = await session.execute(select(AdaptiveQuestion))
        existing_questions = result.scalars().all()

        if len(existing_questions) > 0:
            print(f"✅ Вопросы уже существуют ({len(existing_questions)} шт.)")
        else:
            questions_data = [
                {
                    "topic": "Бюджетирование",
                    "question_text": "Что такое правило 50/30/20?",
                    "options": [
                        "50% на нужды, 30% на желания, 20% на сбережения",
                        "50% на сбережения, 30% на нужды, 20% на желания",
                        "50% на желания, 30% на сбережения, 20% на нужды",
                        "50% на инвестиции, 30% на нужды, 20% на желания"
                    ],
                    "correct_answer": 0,
                    "difficulty": 0.3
                },
                {
                    "topic": "Инвестиции",
                    "question_text": "Что такое диверсификация портфеля?",
                    "options": [
                        "Распределение инвестиций между разными активами",
                        "Покупка только одной акции",
                        "Продажа всех активов",
                        "Инвестирование только в криптовалюту"
                    ],
                    "correct_answer": 0,
                    "difficulty": 0.5
                },
                {
                    "topic": "Сбережения",
                    "question_text": "Что такое 'подушка безопасности'?",
                    "options": [
                        "Резервный фонд на 3-6 месяцев расходов",
                        "Страховка на автомобиль",
                        "Кредитная карта",
                        "Инвестиции в акции"
                    ],
                    "correct_answer": 0,
                    "difficulty": 0.4
                },
                {
                    "topic": "Кредиты",
                    "question_text": "Что такое процентная ставка по кредиту?",
                    "options": [
                        "Плата за использование заемных денег",
                        "Сумма кредита",
                        "Срок кредита",
                        "Первоначальный взнос"
                    ],
                    "correct_answer": 0,
                    "difficulty": 0.3
                },
                {
                    "topic": "Инвестиции",
                    "question_text": "Что такое акция?",
                    "options": [
                        "Доля в компании",
                        "Долговая расписка",
                        "Банковский вклад",
                        "Кредитная карта"
                    ],
                    "correct_answer": 0,
                    "difficulty": 0.2
                }
            ]

            for q_data in questions_data:
                question = AdaptiveQuestion(**q_data)
                session.add(question)

            await session.commit()
            print(f"✅ Создано {len(questions_data)} адаптивных вопросов")

        print("\n🎉 Инициализация завершена!")

if __name__ == "__main__":
    asyncio.run(init_stocks_and_events())
