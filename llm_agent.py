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
