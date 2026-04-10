import os
import json
import re
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

async def parse_transaction_with_llm(user_input: str) -> dict:
    """
    Парсит распознанный текст чека и извлекает сумму, категорию и название магазина
    """
    # Простой парсинг без LLM
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
    """
    # Простая логика без LLM
    wish_lower = user_wish.lower()

    # Пытаемся найти цену в желании
    numbers = re.findall(r'\d+(?:\.\d+)?', user_wish)
    estimated_price = float(numbers[0]) if numbers else current_balance * 0.1

    # Оценка необходимости
    if any(word in wish_lower for word in ['нужно', 'необходимо', 'срочно', 'важно']):
        necessity_score = 8
    elif any(word in wish_lower for word in ['хочу', 'купить', 'взять']):
        necessity_score = 5
    else:
        necessity_score = 3

    # Вердикт на основе баланса
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


async def generate_lesson_with_llm(weak_topic: str = None, strong_topic: str = None) -> dict:
    """
    Генерирует урок с помощью LLM на основе слабых и сильных тем пользователя
    """
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key or api_key == "":
        # Fallback: генерируем простой урок без LLM
        topic = weak_topic or "Основы финансов"
        return {
            "title": f"Урок: {topic}",
            "content": f"Это автоматически сгенерированный урок по теме '{topic}'. Изучите основные концепции и примените их на практике.",
            "questions": [
                {
                    "question": f"Что такое {topic}?",
                    "options": ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
                    "correct": 0
                }
            ],
            "xp_reward": 100
        }

    try:
        # Формируем промпт для LLM
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
            model="openai/gpt-4o",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )

        content = response.choices[0].message.content

        # Пытаемся извлечь JSON из ответа
        import json
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            lesson_data = json.loads(json_match.group())
            return lesson_data
        else:
            raise ValueError("LLM не вернул валидный JSON")

    except Exception as e:
        # Fallback при ошибке LLM
        topic = weak_topic or "Финансовая грамотность"
        return {
            "title": f"Урок: {topic}",
            "content": f"Это автоматически сгенерированный урок по теме '{topic}'. Изучите основные концепции и примените их на практике.",
            "questions": [
                {
                    "question": f"Основной принцип темы '{topic}'?",
                    "options": ["Планирование", "Импульсивность", "Игнорирование", "Случайность"],
                    "correct": 0
                }
            ],
            "xp_reward": 100
        }


async def generate_adaptive_question_with_llm(topic: str, difficulty: float = 0.5) -> dict:
    """
    Генерирует адаптивный вопрос с помощью LLM
    """
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key or api_key == "":
        # Fallback без LLM
        return {
            "question": f"Вопрос по теме '{topic}'",
            "options": ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
            "correct": 0,
            "difficulty": difficulty
        }

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
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        content = response.choices[0].message.content

        import json
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            question_data = json.loads(json_match.group())
            question_data["difficulty"] = difficulty
            return question_data
        else:
            raise ValueError("LLM не вернул валидный JSON")

    except Exception as e:
        return {
            "question": f"Вопрос по теме '{topic}'",
            "options": ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
            "correct": 0,
            "difficulty": difficulty
        }
