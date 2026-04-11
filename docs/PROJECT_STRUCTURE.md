# Структура проекта FinKernel

## 📁 Обзор

Проект реорганизован для улучшения читаемости и поддерживаемости.

## Корневая структура

```
FinKernel/
├── alembic/              # Миграции базы данных
├── archive/              # Устаревшие файлы (не используются)
├── docs/                 # Вся документация проекта
├── frontend/             # React приложение
├── microservices/        # Бэкенд микросервисы
├── scripts/              # Утилиты и скрипты
├── tests/                # Тесты (unit, integration, e2e)
├── .github/workflows/    # CI/CD конфигурация
├── docker-compose.yml    # Docker конфигурация
├── .gitignore           # Git ignore правила
└── README.md            # Главный README
```

## Микросервисы

### API Gateway (`microservices/api-gateway/`)
**Активные файлы:**
- `main_secure.py` - основной файл сервиса

**Функции:**
- Точка входа для всех API запросов
- JWT аутентификация
- Rate limiting
- Маршрутизация к другим сервисам
- Маппинг категорий транзакций (EN → RU)

### Transaction Service (`microservices/transaction-service/`)
**Активные файлы:**
- `main_secure.py` - основной файл
- `portfolio_routes_secure.py` - маршруты портфолио
- `learning_routes.py` - обучающие модули
- `adaptive_routes.py` - адаптивное обучение
- `market_routes.py` - рыночные данные
- `onboarding_routes.py` - онбординг

**Функции:**
- Управление транзакциями (CRUD)
- Расчет баланса с database-level locking
- Idempotency для предотвращения дубликатов
- Портфолио и инвестиции

### AI Service (`microservices/ai-service/`)
**Активные файлы:**
- `main_secure.py` - основной файл
- `engine_secure.py` - движок предсказаний
- `openrouter_client_secure.py` - клиент OpenRouter API

**Функции:**
- Предсказание расходов
- AI-советы на основе транзакций
- Анализ финансового поведения

### Shared (`microservices/shared/`)
**Активные файлы:**
- `auth_secure.py` - JWT аутентификация
- `db.py` - подключение к БД
- `models.py` - SQLAlchemy модели
- `schemas.py` - Pydantic схемы
- `redis.py` - Redis клиент
- `security_hardening.py` - защита от атак
- `rate_limit_global.py` - глобальный rate limiting
- `audit_logger.py` - логирование действий
- `http_client.py` - HTTP клиент с retry
- `circuit_breaker_v2.py` - circuit breaker
- `retry_v2.py` - retry логика
- `startup.py` - валидация конфигурации
- `logger.py` - настройка логирования

## Frontend (`frontend/`)

```
frontend/
├── src/
│   ├── screens/          # Экраны приложения
│   │   ├── HomeScreen.jsx
│   │   ├── PortfolioScreen.jsx
│   │   ├── AuthScreen.jsx
│   │   └── ...
│   ├── components/       # Переиспользуемые компоненты
│   │   ├── Sidebar.jsx
│   │   ├── Tutorial.jsx
│   │   └── ...
│   ├── api.js           # API клиент
│   ├── App.jsx          # Главный компонент
│   ├── settings.js      # Настройки приложения
│   └── DevContext.js    # Контекст разработчика
├── public/
└── Dockerfile
```

## Документация (`docs/`)

- `README.md` - Индекс документации
- `DEPLOYMENT_GUIDE.md` - Руководство по развертыванию
- `SECURITY_FIXES_REPORT.md` - Отчет по безопасности
- `TESTING_DOCUMENTATION.md` - Документация тестов
- `PROJECT_STRUCTURE.md` - Этот файл

## Архив (`archive/`)

Содержит устаревшие версии файлов:
- Старые версии main.py (main_enhanced.py, main_hardened.py)
- Устаревшие модули shared/
- Старые API файлы

**Важно:** Файлы в archive/ не используются в production!

## Тесты (`tests/`)

```
tests/
├── unit/                # Юнит-тесты
│   ├── test_transaction_service.py
│   └── test_portfolio_service.py
├── integration/         # Интеграционные тесты
│   ├── test_rate_limiting.py
│   └── test_audit_logging.py
└── e2e/                # End-to-end тесты
    ├── test_auth_flow.py
    └── test_transaction_flow.py
```

## Соглашения об именовании

### Файлы
- `*_secure.py` - production-ready версии с усиленной безопасностью
- `*_routes.py` - FastAPI маршруты
- `test_*.py` - тестовые файлы

### Компоненты
- `*Screen.jsx` - экраны приложения
- `*.jsx` - React компоненты

## Миграции

Все миграции БД в `alembic/versions/`:
- `000_initial_schema.py` - начальная схема
- `001_security_hardening.py` - улучшения безопасности
- `002_add_idempotency.py` - idempotency keys

## CI/CD

GitHub Actions workflows в `.github/workflows/`:
- `ci.yml` - Continuous Integration (тесты, линтинг)
- `cd.yml` - Continuous Deployment

## Порты сервисов

- Frontend: 80, 443
- API Gateway: 8000
- Transaction Service: 8001
- AI Service: 8002
- PostgreSQL: 5432
- Redis: 6379
- Prometheus: 9090
- Grafana: 3000
- Jaeger: 16686

## Переменные окружения

Основные переменные в `docker-compose.yml`:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `JWT_SECRET` - секрет для JWT токенов
- `OPENROUTER_API_KEY` - API ключ OpenRouter (опционально)

## Следующие шаги

1. Удалить файлы из `archive/` после подтверждения работоспособности
2. Добавить больше тестов
3. Улучшить документацию API
4. Настроить автоматическое развертывание
