# FinKernel - Financial Management Platform

Современная платформа для управления личными финансами с AI-советами и аналитикой.

## 📁 Структура проекта

```
FinKernel/
├── frontend/                 # React фронтенд
│   ├── src/
│   │   ├── screens/         # Экраны приложения
│   │   ├── components/      # Переиспользуемые компоненты
│   │   └── api.js          # API клиент
│   └── Dockerfile
│
├── microservices/           # Микросервисы
│   ├── api-gateway/        # API Gateway (порт 8000)
│   │   └── main_secure.py  # Основной файл
│   ├── transaction-service/ # Сервис транзакций (порт 8001)
│   │   ├── main_secure.py
│   │   ├── portfolio_routes_secure.py
│   │   ├── learning_routes.py
│   │   ├── adaptive_routes.py
│   │   ├── market_routes.py
│   │   └── onboarding_routes.py
│   ├── ai-service/         # AI сервис (порт 8002)
│   │   ├── main_secure.py
│   │   ├── engine_secure.py
│   │   └── openrouter_client_secure.py
│   ├── celery-worker/      # Celery worker
│   │   └── worker.py
│   └── shared/             # Общие модули
│       ├── auth_secure.py  # Аутентификация JWT
│       ├── db.py           # База данных
│       ├── models.py       # SQLAlchemy модели
│       ├── schemas.py      # Pydantic схемы
│       ├── redis.py        # Redis клиент
│       ├── security_hardening.py
│       ├── rate_limit_global.py
│       ├── audit_logger.py
│       └── http_client.py
│
├── tests/                   # Тесты
│   ├── unit/               # Юнит-тесты
│   ├── integration/        # Интеграционные тесты
│   └── e2e/                # E2E тесты
│
├── alembic/                # Миграции БД
│   └── versions/
│
├── docs/                   # Документация
│   ├── DEPLOYMENT_GUIDE.md
│   ├── SECURITY_FIXES_REPORT.md
│   ├── TESTING_DOCUMENTATION.md
│   └── ...
│
├── scripts/                # Утилиты и скрипты
├── .github/workflows/      # CI/CD
├── docker-compose.yml      # Docker конфигурация
├── CHANGELOG.md           # История изменений
└── README.md              # Этот файл
```

## 🚀 Быстрый старт

### Требования
- Docker & Docker Compose
- Node.js 18+ (для локальной разработки фронтенда)
- Python 3.11+ (для локальной разработки бэкенда)

### Запуск

```bash
# Клонировать репозиторий
git clone <repo-url>
cd FinKernel

# Запустить все сервисы
docker-compose up -d

# Проверить статус
docker-compose ps
```

Приложение будет доступно:
- Frontend: http://localhost (порт 80/443)
- API Gateway: http://localhost:8000
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- Jaeger: http://localhost:16686

### Первый вход
- Email: `admin@admin.com`
- Password: `admin123`

## 🏗️ Архитектура

### Микросервисы
1. **API Gateway** - точка входа, аутентификация, маршрутизация
2. **Transaction Service** - управление транзакциями и балансом
3. **AI Service** - предсказания и AI-советы
4. **Celery Worker** - фоновые задачи

### Технологии
- **Backend**: FastAPI, SQLAlchemy, PostgreSQL, Redis
- **Frontend**: React, Framer Motion
- **Infrastructure**: Docker, Nginx, Prometheus, Grafana, Jaeger
- **Security**: JWT, Rate Limiting, Audit Logging

## 📊 Мониторинг

- **Prometheus**: метрики производительности
- **Grafana**: дашборды и визуализация
- **Jaeger**: distributed tracing
- **Audit Logs**: логирование всех действий

## 🔒 Безопасность

- JWT аутентификация с refresh tokens
- Rate limiting (глобальный и per-user)
- SQL injection защита
- XSS защита
- CSRF защита
- Audit logging всех операций
- Database-level locking для транзакций

## 🧪 Тестирование

```bash
# Запустить все тесты
pytest

# Юнит-тесты
pytest tests/unit/

# Интеграционные тесты
pytest tests/integration/

# E2E тесты
pytest tests/e2e/
```

## 📝 Документация

Подробная документация находится в папке `docs/`:
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)
- [Security Fixes Report](docs/SECURITY_FIXES_REPORT.md)
- [Testing Documentation](docs/TESTING_DOCUMENTATION.md)

## 🤝 Разработка

### Добавление новой функции
1. Создать ветку: `git checkout -b feature/название`
2. Внести изменения
3. Написать тесты
4. Создать PR

### Миграции БД
```bash
# Создать миграцию
alembic revision -m "описание"

# Применить миграции
alembic upgrade head
```

## 📄 Лицензия

MIT License
