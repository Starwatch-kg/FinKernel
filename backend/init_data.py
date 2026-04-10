"""
Скрипт для инициализации базы данных тестовыми данными
"""
import asyncio
from models import (
    User, Achievement, Module, Lesson,
    async_session_maker, init_db
)

async def init_test_data():
    """Создать тестовые данные"""
    await init_db()

    async with async_session_maker() as session:
        # Создаем достижения
        achievements = [
            Achievement(
                title="Первые шаги",
                description="Совершите первую транзакцию",
                icon="🎯",
                xp_reward=50,
                condition_type="transaction_count",
                condition_value=1
            ),
            Achievement(
                title="Экономный",
                description="Накопите 5000 рублей",
                icon="💰",
                xp_reward=100,
                condition_type="balance_reached",
                condition_value=5000
            ),
            Achievement(
                title="Финансовый гуру",
                description="Достигните 10 уровня",
                icon="🏆",
                xp_reward=500,
                condition_type="level_reached",
                condition_value=10
            ),
            Achievement(
                title="Постоянство",
                description="Поддерживайте серию 7 дней",
                icon="🔥",
                xp_reward=200,
                condition_type="streak",
                condition_value=7
            ),
            Achievement(
                title="Ученик",
                description="Завершите 5 уроков",
                icon="📚",
                xp_reward=150,
                condition_type="lessons_completed",
                condition_value=5
            )
        ]

        for achievement in achievements:
            session.add(achievement)

        # Создаем модули обучения
        module1 = Module(
            title="Основы финансовой грамотности",
            description="Изучите базовые принципы управления деньгами",
            icon="📖",
            order=1,
            required_level=1
        )
        session.add(module1)

        module2 = Module(
            title="Бюджетирование",
            description="Научитесь планировать свой бюджет",
            icon="📊",
            order=2,
            required_level=3
        )
        session.add(module2)

        module3 = Module(
            title="Инвестиции для начинающих",
            description="Первые шаги в мире инвестиций",
            icon="📈",
            order=3,
            required_level=5
        )
        session.add(module3)

        await session.commit()
        await session.refresh(module1)
        await session.refresh(module2)
        await session.refresh(module3)

        # Создаем уроки для модуля 1
        lessons_module1 = [
            Lesson(
                module_id=module1.id,
                title="Что такое финансовая грамотность?",
                description="Введение в основные понятия",
                content="Финансовая грамотность - это способность эффективно управлять своими деньгами...",
                questions=[
                    {
                        "question": "Что такое финансовая грамотность?",
                        "options": [
                            "Умение зарабатывать много денег",
                            "Способность управлять своими финансами",
                            "Знание всех банков",
                            "Умение считать деньги"
                        ],
                        "correct": 1
                    },
                    {
                        "question": "Зачем нужна финансовая грамотность?",
                        "options": [
                            "Чтобы стать богатым",
                            "Чтобы контролировать расходы и достигать целей",
                            "Чтобы работать в банке",
                            "Это не нужно"
                        ],
                        "correct": 1
                    }
                ],
                xp_reward=50,
                order=1,
                required_level=1
            ),
            Lesson(
                module_id=module1.id,
                title="Доходы и расходы",
                description="Учимся различать доходы и расходы",
                content="Доходы - это деньги, которые вы получаете. Расходы - деньги, которые вы тратите...",
                questions=[
                    {
                        "question": "Что является доходом?",
                        "options": [
                            "Покупка продуктов",
                            "Зарплата",
                            "Оплата счетов",
                            "Поход в кино"
                        ],
                        "correct": 1
                    },
                    {
                        "question": "Что является расходом?",
                        "options": [
                            "Подарок от друга",
                            "Зарплата",
                            "Покупка одежды",
                            "Возврат долга вам"
                        ],
                        "correct": 2
                    }
                ],
                xp_reward=50,
                order=2,
                required_level=1
            ),
            Lesson(
                module_id=module1.id,
                title="Личный бюджет",
                description="Как составить свой первый бюджет",
                content="Личный бюджет помогает планировать доходы и расходы...",
                questions=[
                    {
                        "question": "Что такое бюджет?",
                        "options": [
                            "Список желаний",
                            "План доходов и расходов",
                            "Банковский счет",
                            "Кредитная карта"
                        ],
                        "correct": 1
                    }
                ],
                xp_reward=75,
                order=3,
                required_level=2
            )
        ]

        for lesson in lessons_module1:
            session.add(lesson)

        # Создаем уроки для модуля 2
        lessons_module2 = [
            Lesson(
                module_id=module2.id,
                title="Правило 50/30/20",
                description="Простой метод распределения бюджета",
                content="50% на необходимое, 30% на желания, 20% на накопления...",
                questions=[
                    {
                        "question": "Сколько процентов выделять на накопления?",
                        "options": ["10%", "20%", "30%", "50%"],
                        "correct": 1
                    }
                ],
                xp_reward=100,
                order=1,
                required_level=3
            ),
            Lesson(
                module_id=module2.id,
                title="Отслеживание расходов",
                description="Как контролировать свои траты",
                content="Регулярное отслеживание расходов помогает понять, куда уходят деньги...",
                questions=[
                    {
                        "question": "Как часто нужно проверять расходы?",
                        "options": [
                            "Раз в год",
                            "Никогда",
                            "Регулярно (каждый день или неделю)",
                            "Только когда кончились деньги"
                        ],
                        "correct": 2
                    }
                ],
                xp_reward=100,
                order=2,
                required_level=3
            )
        ]

        for lesson in lessons_module2:
            session.add(lesson)

        # Создаем уроки для модуля 3
        lessons_module3 = [
            Lesson(
                module_id=module3.id,
                title="Что такое инвестиции?",
                description="Введение в мир инвестиций",
                content="Инвестиции - это вложение денег с целью получения дохода в будущем...",
                questions=[
                    {
                        "question": "Что такое инвестиции?",
                        "options": [
                            "Хранение денег под подушкой",
                            "Вложение денег для получения дохода",
                            "Трата всех денег",
                            "Взятие кредита"
                        ],
                        "correct": 1
                    }
                ],
                xp_reward=150,
                order=1,
                required_level=5
            )
        ]

        for lesson in lessons_module3:
            session.add(lesson)

        await session.commit()

        print("✅ Тестовые данные успешно созданы!")
        print(f"   - Создано {len(achievements)} достижений")
        print(f"   - Создано 3 модуля")
        print(f"   - Создано {len(lessons_module1) + len(lessons_module2) + len(lessons_module3)} уроков")

if __name__ == "__main__":
    asyncio.run(init_test_data())
