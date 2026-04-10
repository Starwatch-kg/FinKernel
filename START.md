# Запуск

```bash
docker-compose up --build
```

API доступен на http://localhost:8000

## Создать тестового пользователя:
```bash
curl -X POST "http://localhost:8000/api/user/create?username=test_user&initial_balance=10000"
```

## Отправить транзакцию:
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "message": "Потратил 500 рублей на еду"}'
```

## Получить дашборд:
```bash
curl "http://localhost:8000/api/user/1/dashboard"
```
