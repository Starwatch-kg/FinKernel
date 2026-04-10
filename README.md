# FinKernel - Финансовый AI-ассистент

Полноценное приложение для управления личными финансами с AI-движком и образовательной платформой.

## 🚀 Быстрый старт

### 1. Запуск бэкенда (Docker)

```bash
# Перейдите в ветку backend
git checkout backend

# Запустите Docker контейнеры
docker-compose up --build -d

# Инициализируйте тестовые данные (достижения, уроки)
docker exec -it fin-api-1 python init_data.py
```

Бэкенд будет доступен на http://localhost:8000
Swagger UI: http://localhost:8000/docs

### 2. Запуск фронтенда

```bash
# Перейдите в ветку frontend
git checkout frontend

# Установите зависимости
npm install

# Создайте .env.local
echo 'VITE_API_URL=http://localhost:8000/api' > .env.local

# Запустите dev сервер
npm run dev
```

Фронтенд будет доступен на http://localhost:5173

## 📋 Основные функции

### Бэкенд API

- ✅ **Аутентификация**: Регистрация и вход пользователей
- ✅ **Дашборд**: Баланс, расходы, прогноз, AI-советы
- ✅ **Транзакции**: Добавление, просмотр, удаление транзакций
- ✅ **Достижения**: Система достижений с прогрессом
- ✅ **Обучение**: Модули и уроки по финансовой грамотности
- ✅ **Прогресс**: Уровни, XP, streak
- ✅ **Онбординг**: Тест для новых пользователей
- ✅ **AI-оценка покупок**: Оценка импульсивных покупок (с fallback)

### Фронтенд

- 🏠 **Главная**: Дашборд с балансом и статистикой
- 💰 **Транзакции**: История операций
- 📚 **Обучение**: Интерактивные уроки
- 🏆 **Достижения**: Прогресс и награды
- ⚙️ **Настройки**: Персонализация

## 🗄️ Структура базы данных

### Таблицы

- `users` - Пользователи (баланс, уровень, XP, streak)
- `transactions` - Транзакции (сумма, категория, описание)
- `achievements` - Достижения
- `user_achievements` - Прогресс по достижениям
- `modules` - Модули обучения
- `lessons` - Уроки
- `lesson_progress` - Прогресс по урокам

## 🔧 Технологии

### Backend
- Python 3.11+
- FastAPI (REST API)
- PostgreSQL + asyncpg
- SQLAlchemy (async ORM)
- Docker + Docker Compose

### Frontend
- React 18
- Vite
- Framer Motion (анимации)
- Fetch API

## 📡 API Эндпоинты

### Аутентификация
- `POST /api/register` - Регистрация
- `POST /api/login` - Вход

### Пользователь
- `GET /api/dashboard?userId={userId}` - Дашборд
- `GET /api/progress?userId={userId}` - Прогресс

### Транзакции
- `GET /api/transactions?userId={userId}` - Список транзакций
- `POST /api/transactions` - Добавить транзакцию
- `DELETE /api/transactions/{id}` - Удалить транзакцию

### Обучение
- `GET /api/v2/modules?userId={userId}` - Модули
- `GET /api/v2/lessons?userId={userId}&moduleId={id}` - Уроки модуля
- `GET /api/v2/lesson/{id}?userId={userId}` - Детали урока
- `POST /api/v2/complete-lesson` - Завершить урок

### Достижения
- `GET /api/achievements?userId={userId}` - Достижения

### Онбординг
- `GET /api/onboarding/status?userId={userId}` - Статус
- `GET /api/onboarding/questions` - Вопросы
- `POST /api/onboarding/submit` - Отправить ответы

## 🎮 Тестовые данные

После запуска `init_data.py` создаются:

- **5 достижений**: Первые шаги, Экономный, Финансовый гуру, Постоянство, Ученик
- **3 модуля**: Основы финансовой грамотности, Бюджетирование, Инвестиции
- **6 уроков**: С вопросами и наградами XP

## 🔐 Переменные окружения

### Backend (.env)
```env
DATABASE_URL=postgresql+asyncpg://finuser:finpass123@db:5432/financedb
OPENROUTER_API_KEY=your_key_here  # Опционально для LLM
```

### Frontend (.env.local)
```env
VITE_API_URL=http://localhost:8000/api
```

## 🐛 Отладка

### Проверка бэкенда
```bash
curl http://localhost:8000/
curl http://localhost:8000/api/dashboard?userId=test@test.com
```

### Логи Docker
```bash
docker logs fin-api-1 --tail 50
docker logs fin-db-1 --tail 50
```

### Перезапуск с пересборкой
```bash
docker-compose down
docker-compose up --build -d
```

## 📝 Примечания

- LLM функции работают с fallback (простой парсинг без AI)
- Для полноценной работы AI нужен OPENROUTER_API_KEY
- Первый пользователь: admin@admin.com (админ права)
- Начальный баланс: 10,000 руб.
- Начальный уровень: 1, XP: 0

## 🤝 Разработка

Проект разделен на две ветки:
- `backend` - FastAPI сервер
- `frontend` - React приложение

Для разработки запускайте оба одновременно.

