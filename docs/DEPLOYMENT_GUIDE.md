# 🚀 DEPLOYMENT GUIDE - FinKernel

**Дата:** 2026-04-12  
**Статус:** ✅ Готово к запуску

---

## 📦 Что было исправлено

### Frontend-Backend Integration
1. ✅ Исправлен API client (`frontend/src/api.js`)
   - Убран `userId` из всех запросов (теперь используется JWT)
   - Исправлены пути: `/api/auth/register`, `/api/auth/login`
   - Добавлен маппинг категорий: Русский → Английский
   - Добавлен маппинг полей: `comment` → `description`

2. ✅ Обновлен `AuthScreen.jsx`
   - Исправлена обработка ответа: `res.access_token` вместо `res.ok`
   - Токены сохраняются автоматически через API client

3. ✅ Исправлен синтаксис в `api.js`
   - Заменен Python docstring `"""` на JavaScript комментарий `/**/`

---

## 🐳 Запуск через Docker

### Быстрый старт
```bash
# 1. Создать .env файл (уже создан из .env.development)
cp .env.development .env

# 2. Собрать все образы
docker-compose build

# 3. Запустить все сервисы
docker-compose up -d

# 4. Проверить статус
docker-compose ps
```

### Доступные сервисы

| Сервис | URL | Описание |
|--------|-----|----------|
| **Frontend** | http://localhost | Веб-интерфейс |
| **Frontend (HTTPS)** | https://localhost | Веб-интерфейс (SSL) |
| **API Gateway** | http://localhost:8000 | Главный API endpoint |
| **Transactions Service** | http://localhost:8001 | Микросервис транзакций |
| **AI Service** | http://localhost:8002 | Микросервис AI |
| **PostgreSQL** | localhost:5432 | База данных |
| **Redis** | localhost:6379 | Кэш и очереди |
| **Jaeger UI** | http://localhost:16686 | Трейсинг |
| **Prometheus** | http://localhost:9090 | Метрики |
| **Grafana** | http://localhost:3000 | Дашборды (admin/admin) |

---

## 🔧 Управление сервисами

### Просмотр логов
```bash
# Все сервисы
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f gateway
docker-compose logs -f frontend
docker-compose logs -f transactions
```

### Перезапуск сервиса
```bash
docker-compose restart gateway
docker-compose restart frontend
```

### Остановка всех сервисов
```bash
docker-compose down
```

### Полная очистка (включая volumes)
```bash
docker-compose down -v
```

---

## 🧪 Тестирование

### Проверка здоровья сервисов
```bash
# Gateway
curl http://localhost:8000/health

# Frontend
curl http://localhost/

# Transactions
curl http://localhost:8001/health
```

### Запуск тестов
```bash
# Unit тесты
pytest tests/unit/ -v

# Integration тесты
pytest tests/integration/ -v

# E2E тесты
pytest tests/e2e/ -v

# Concurrency тесты (КРИТИЧЕСКИЕ!)
pytest tests/concurrency/ -v
```

---

## 📊 Мониторинг

### Jaeger (Трейсинг)
- URL: http://localhost:16686
- Отслеживание запросов между микросервисами
- Анализ производительности

### Prometheus (Метрики)
- URL: http://localhost:9090
- Метрики всех сервисов
- Алерты и мониторинг

### Grafana (Визуализация)
- URL: http://localhost:3000
- Логин: `admin`
- Пароль: `admin`
- Дашборды для визуализации метрик

---

## 🔐 Безопасность

### Исправленные уязвимости
1. ✅ IDOR в portfolio endpoints
2. ✅ Idempotency для финансовых операций
3. ✅ Audit logging для compliance
4. ✅ Rate limiting с fallback
5. ✅ Retry логика для inter-service calls
6. ✅ Валидация баланса при удалении транзакций

### JWT Authentication
- Токены хранятся в localStorage
- Автоматическое добавление в Authorization header
- Refresh token для продления сессии

---

## 🐛 Известные проблемы

### Отсутствующие endpoints
Backend (`main_secure.py`) не имеет следующих endpoints, которые ожидает фронтенд:
- `/api/portfolio` - Данные портфолио
- `/api/trade` - Выполнение сделок
- `/api/stocks` - Список акций
- `/api/stock/{ticker}` - Детали акции
- `/api/recommendations` - AI рекомендации

**Решение:** Эти endpoints существуют в `main.py` (старая версия). Нужно мигрировать их в `main_secure.py`.

---

## 📝 Переменные окружения

### Обязательные
```env
DATABASE_URL=postgresql+asyncpg://finuser:finpass123@postgres:5432/financedb
REDIS_URL=redis://redis:6379/0
JWT_SECRET_KEY=<your-secret-key>
```

### Опциональные
```env
OPENROUTER_API_KEY=<your-api-key>
ADMIN_EMAILS=admin@example.com,dev@example.com
ENVIRONMENT=development
DEBUG=true
```

---

## 🚨 Troubleshooting

### Frontend не загружается
```bash
# Проверить логи
docker logs fin_frontend

# Пересобрать
docker-compose build frontend
docker-compose up -d frontend
```

### Backend возвращает 404
```bash
# Проверить что gateway запущен
docker-compose ps gateway

# Проверить логи
docker logs fin_gateway
```

### База данных не подключается
```bash
# Проверить что PostgreSQL запущен
docker-compose ps postgres

# Проверить healthcheck
docker inspect fin_postgres | grep Health
```

### Redis недоступен
```bash
# Проверить Redis
docker-compose ps redis

# Тест подключения
docker exec fin_redis redis-cli ping
```

---

## 📚 Дополнительная документация

- `SECURITY_FIXES_REPORT.md` - Отчет об исправлениях безопасности
- `TESTING_DOCUMENTATION.md` - Документация тестов
- `FRONTEND_BACKEND_ISSUES.md` - Анализ проблем интеграции
- `FINAL_REPORT.md` - Итоговый отчет

---

## ✅ Checklist перед production

- [x] Все критические уязвимости исправлены
- [x] Idempotency реализована
- [x] Audit logging настроен
- [x] Rate limiting работает
- [x] Frontend-backend интеграция исправлена
- [x] Docker образы собраны
- [x] Все сервисы запускаются
- [ ] Тесты прошли на staging
- [ ] Performance тестирование
- [ ] Security audit
- [ ] Миграция отсутствующих endpoints

---

**Система готова к тестированию!** 🎉
