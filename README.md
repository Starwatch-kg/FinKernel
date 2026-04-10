# Финансовый AI-ассистент

REST API с AI-движком для управления личными финансами.

## Быстрый старт

1. Создайте `.env` файл:
```bash
cp .env.example .env
```

2. Заполните обязательные переменные:
```env
ANTHROPIC_API_KEY=your_api_key_here
DATABASE_URL=postgresql://user:password@localhost:5432/finance_db
```

3. Запустите:
```bash
# Через Docker (рекомендуется)
docker-compose up --build

# Или локально
pip install -r requirements.txt
python api.py
```

## Порты

- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432

## Основные фичи

- REST API для управления финансами
- AI-предсказания (когда закончатся деньги)
- Финансовый скоринг (0-1000 баллов)
- Система достижений и геймификация
- Инвестиционные рекомендации
- LLM агент с обработкой естественного языка

## Безопасность

Для продакшена установите в `.env`:
```env
API_KEY=your_secure_api_key
ALLOWED_ORIGINS=https://yourdomain.com
```

API защищен:
- Rate limiting (10-100 запросов/минуту)
- Валидация всех входных данных
- Опциональная аутентификация через Bearer токен
- CORS настраивается через переменные окружения

## API примеры

### Создать пользователя
```bash
curl -X POST "http://localhost:8000/users" \
  -H "Content-Type: application/json" \
  -d '{"name": "Иван", "age": 25, "balance": 10000}'
```

### Добавить транзакцию
```bash
curl -X POST "http://localhost:8000/users/{user_id}/transactions" \
  -H "Content-Type: application/json" \
  -d '{"amount": 500, "category": "food", "transaction_type": "expense"}'
```

### Получить предсказание
```bash
curl "http://localhost:8000/users/{user_id}/analytics/prediction"
```

## Структура

```
├── api.py              # FastAPI REST API (порт 8000)
├── llm_agent.py        # LLM агент с Claude API
├── database.py         # PostgreSQL + SQLAlchemy
├── models.py           # Модели данных
├── scoring.py          # Финансовый скоринг
├── ai_predictor.py     # AI-предсказания
├── gamification.py     # Достижения
├── investment.py       # Инвестиции
└── requirements.txt    # Зависимости
```

## Технологии

- Python 3.11+
- FastAPI (REST API)
- PostgreSQL (база данных)
- Claude 3.5 Sonnet (AI)
- Docker + Docker Compose
- slowapi (rate limiting)
