# Документация FinKernel

## 📚 Содержание

### Руководства по развертыванию
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Полное руководство по развертыванию
- [DOCKER_DEPLOYMENT_SUCCESS.md](DOCKER_DEPLOYMENT_SUCCESS.md) - Успешное развертывание Docker

### Отчеты и документация
- [FINAL_REPORT.md](FINAL_REPORT.md) - Финальный отчет проекта
- [SECURITY_FIXES_REPORT.md](SECURITY_FIXES_REPORT.md) - Отчет по исправлениям безопасности
- [TESTING_DOCUMENTATION.md](TESTING_DOCUMENTATION.md) - Документация по тестированию
- [FRONTEND_BACKEND_ISSUES.md](FRONTEND_BACKEND_ISSUES.md) - Известные проблемы фронтенд-бэкенд интеграции

## 🏗️ Архитектура

### Микросервисы
1. **API Gateway** (порт 8000) - точка входа, аутентификация, маршрутизация
2. **Transaction Service** (порт 8001) - управление транзакциями и балансом
3. **AI Service** (порт 8002) - предсказания и AI-советы
4. **Celery Worker** - фоновые задачи

## 🔒 Безопасность

- JWT токены с refresh механизмом
- Rate limiting (глобальный и per-user)
- Audit logging всех операций
- Database-level locking для финансовых операций

## 🧪 Тестирование

```bash
pytest                    # Все тесты
pytest tests/unit/        # Юнит-тесты
pytest tests/integration/ # Интеграционные
pytest tests/e2e/         # E2E
```

## 📊 API Endpoints

### Аутентификация
- POST /api/auth/register
- POST /api/auth/login
- POST /api/auth/refresh

### Транзакции
- GET /api/transactions
- POST /api/transactions
- DELETE /api/transactions/{id}

### Дашборд
- GET /api/dashboard

Подробнее см. документы в этой папке.
