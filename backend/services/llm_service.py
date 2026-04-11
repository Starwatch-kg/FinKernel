"""
Сервис для работы с LLM (OpenRouter)
Включает жесткие fallback-механизмы при ошибках API
"""
import os
import re
import json
import logging
from openai import AsyncOpenAI
from typing import Optional

logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY", "")
)


async def parse_transaction_with_llm(user_input: str) -> dict:
    """
    Парсит распознанный текст чека и извлекает сумму, категорию и название магазина
    FALLBACK: Простой regex-парсинг без LLM
    """
    numbers = re.findall(r'\d+(?:\.\d+)?', user_input)
    amount = float(numbers[0]) if numbers else 0.0

    text_lower = user_input.lower()
    if any(word in text_lower for word in ['кофе', 'еда', 'продукты', 'магазин', 'супермаркет', 'ресторан']):
        category = 'food'
    elif any(word in text_lower for word in ['такси', 'проезд', 'транспорт', 'метро', 'автобус']):
        category = 'transport'
    elif any(word in text_lower for word in ['кино', 'игры', 'развлечения', 'концерт']):
        category = 'entertainment'
    else:
        category = 'other'

    return {
        "status": "success",
        "amount": amount,
        "category": category,
        "merchant_name": None
    }


async def evaluate_purchase_with_llm(user_wish: str, current_balance: float) -> dict:
    """
    Оценивает импульсивную покупку подростка и дает совет
    FALLBACK: Простая логика без LLM
    """
    wish_lower = user_wish.lower()

    numbers = re.findall(r'\d+(?:\.\d+)?', user_wish)
    estimated_price = float(numbers[0]) if numbers else current_balance * 0.1

    if any(word in wish_lower for word in ['нужно', 'необходимо', 'срочно', 'важно']):
        necessity_score = 8
    elif any(word in wish_lower for word in ['хочу', 'купить', 'взять']):
        necessity_score = 5
    else:
        necessity_score = 3

    if estimated_price > current_balance * 0.5:
        verdict = "Бро, это слишком дорого для твоего баланса"
        reasoning = f"Это {estimated_price:.0f} руб., а у тебя всего {current_balance:.0f}. Подумай дважды."
    elif estimated_price > current_balance:
        verdict = "Нет денег — нет проблем (и покупки)"
        reasoning = "У тебя не хватает средств на это."
    else:
        verdict = "Можно взять, но с умом"
        reasoning = f"У тебя {current_balance:.0f} руб., это потянешь."

    return {
        "necessity_score": necessity_score,
        "verdict": verdict,
        "reasoning": reasoning
    }


async def generate_lesson_with_llm(weak_topic: Optional[str] = None, strong_topic: Optional[str] = None) -> dict:
    """
    Генерирует урок с помощью LLM на основе слабых и сильных тем пользователя
    FALLBACK: Захардкоженный урок при ошибке API
    """
    api_key = os.getenv("OPENROUTER_API_KEY", "")

    if not api_key or api_key == "":
        logger.warning("OPENROUTER_API_KEY not set, using fallback lesson")
        return _get_fallback_lesson(weak_topic)

    try:
        prompt = f"""Создай образовательный урок по финансовой грамотности для подростков.

Слабая тема пользователя: {weak_topic or 'не указана'}
Сильная тема пользователя: {strong_topic or 'не указана'}

Сгенерируй урок в формате JSON:
{{
    "title": "Название урока",
    "content": "Подробное содержание урока (3-5 абзацев)",
    "questions": [
        {{
            "question": "Текст вопроса",
            "options": ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
            "correct": 0
        }}
    ],
    "xp_reward": 100
}}

Урок должен быть понятным, интересным и практичным. Включи 3-4 вопроса."""

        response = await client.chat.completions.create(
            model="anthropic/claude-3.5-sonnet",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000,
            timeout=10.0  # 10 секунд таймаут
        )

        content = response.choices[0].message.content
        json_match = re.search(r'\{.*\}', content, re.DOTALL)

        if json_match:
            lesson_data = json.loads(json_match.group())
            logger.info(f"Successfully generated lesson via LLM: {lesson_data.get('title')}")
            return lesson_data
        else:
            raise ValueError("LLM не вернул валидный JSON")

    except Exception as e:
        logger.error(f"LLM lesson generation failed: {str(e)}, using fallback")
        return _get_fallback_lesson(weak_topic)


async def generate_adaptive_question_with_llm(topic: str, difficulty: float = 0.5) -> dict:
    """
    Генерирует адаптивный вопрос с помощью LLM
    FALLBACK: Захардкоженный вопрос при ошибке API
    """
    api_key = os.getenv("OPENROUTER_API_KEY", "")

    if not api_key or api_key == "":
        logger.warning("OPENROUTER_API_KEY not set, using fallback question")
        return _get_fallback_question(topic, difficulty)

    try:
        difficulty_text = "легкий" if difficulty < 0.4 else "средний" if difficulty < 0.7 else "сложный"

        prompt = f"""Создай {difficulty_text} вопрос по финансовой грамотности на тему: {topic}

Формат JSON:
{{
    "question": "Текст вопроса",
    "options": ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
    "correct": 0
}}

Вопрос должен быть понятным для подростков и проверять реальное понимание темы."""

        response = await client.chat.completions.create(
            model="anthropic/claude-3.5-sonnet",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500,
            timeout=10.0
        )

        content = response.choices[0].message.content
        json_match = re.search(r'\{.*\}', content, re.DOTALL)

        if json_match:
            question_data = json.loads(json_match.group())
            question_data["difficulty"] = difficulty
            logger.info(f"Successfully generated question via LLM for topic: {topic}")
            return question_data
        else:
            raise ValueError("LLM не вернул валидный JSON")

    except Exception as e:
        logger.error(f"LLM question generation failed: {str(e)}, using fallback")
        return _get_fallback_question(topic, difficulty)


def _get_fallback_lesson(topic: Optional[str] = None) -> dict:
    """Захардкоженный урок для fallback"""
    topic = topic or "Основы финансов"

    lessons_bank = {
        "Основы финансов": {
            "title": "Урок: Основы финансовой грамотности",
            "content": """Финансовая грамотность — это умение управлять своими деньгами.

Основные принципы:
1. Планирование бюджета — знай, сколько у тебя денег и на что ты их тратишь
2. Контроль расходов — отслеживай каждую покупку
3. Накопления — откладывай хотя бы 10% от дохода
4. Разумные траты — думай перед покупкой, действительно ли тебе это нужно

Эти простые правила помогут тебе всегда иметь деньги на важные вещи.""",
            "questions": [
                {
                    "question": "Сколько процентов от дохода рекомендуется откладывать?",
                    "options": ["5%", "10%", "50%", "100%"],
                    "correct": 1
                },
                {
                    "question": "Что такое бюджет?",
                    "options": ["План доходов и расходов", "Кредитная карта", "Банковский счет", "Налог"],
                    "correct": 0
                },
                {
                    "question": "Что нужно делать перед крупной покупкой?",
                    "options": ["Подумать, нужна ли она", "Сразу купить", "Взять кредит", "Спросить друзей"],
                    "correct": 0
                }
            ],
            "xp_reward": 100
        },
        "Бюджетирование": {
            "title": "Урок: Как составить личный бюджет",
            "content": """Бюджет — это план твоих денег. Он помогает понять, куда уходят деньги и как их сохранить.

Как составить бюджет:
1. Запиши все доходы (карманные деньги, подработка)
2. Запиши все расходы (еда, транспорт, развлечения)
3. Вычти расходы из доходов
4. Если остается — отлично! Если нет — нужно сокращать траты

Правило 50/30/20: 50% на необходимое, 30% на желания, 20% на накопления.""",
            "questions": [
                {
                    "question": "Что такое правило 50/30/20?",
                    "options": ["Распределение бюджета", "Скидка в магазине", "Налоговая ставка", "Процент по вкладу"],
                    "correct": 0
                },
                {
                    "question": "Первый шаг в составлении бюджета?",
                    "options": ["Купить что-то", "Записать доходы", "Взять кредит", "Удалить приложение"],
                    "correct": 1
                }
            ],
            "xp_reward": 100
        }
    }

    return lessons_bank.get(topic, lessons_bank["Основы финансов"])


def _get_fallback_question(topic: str, difficulty: float) -> dict:
    """Захардкоженный вопрос для fallback"""
    questions_bank = [
        {
            "question": f"Какой основной принцип темы '{topic}'?",
            "options": ["Планирование и контроль", "Импульсивные траты", "Игнорирование финансов", "Случайные решения"],
            "correct": 0,
            "difficulty": difficulty
        },
        {
            "question": "Что важнее всего в управлении финансами?",
            "options": ["Отслеживание расходов", "Тратить все сразу", "Не думать о деньгах", "Брать кредиты"],
            "correct": 0,
            "difficulty": difficulty
        }
    ]

    return questions_bank[0]
