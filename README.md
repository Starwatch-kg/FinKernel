# 🏦 FinKernel - Финансовый AI-ассистент

> Образовательная платформа для финансовой грамотности с AI-движком и модульной архитектурой.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791.svg)](https://www.postgresql.org/)

---

## 🚀 Быстрый старт

### Запуск одной командой:

```bash
./start.sh
```

Скрипт автоматически:
- ✅ Запустит PostgreSQL в Docker
- ✅ Запустит FastAPI backend
- ✅ Инициализирует базу данных
- ✅ Создаст тестовые данные

### Остановка:

```bash
./stop.sh
```

### Доступ к сервисам:

- **Backend API:** http://localhost:8000
- **Swagger UI:** http://localhost:8000/docs
- **Database:** localhost:5432

---

## 📖 Описание

**FinKernel** помогает пользователям:
- 💰 Отслеживать доходы и расходы
- 📊 Анализировать траты с AI-советами
- 📚 Изучать финансовую грамотность
- 🏆 Получать достижения и повышать уровень
- 🎯 Оценивать импульсивные покупки

---

## 🏗️ Архитектура (Модульный монолит)

```
backend/
├── main.py              # Точка входа (65 строк)
├── models.py            # ORM модели
├── core/                # Конфигурация
│   ├── config.py        # Pydantic Settings
│   ├── database.py      # SQLAlchemy setup
│   └── security.py      # Хеширование паролей (bcrypt)
├── api/routes/          # API эндпоинты
│   ├── auth.py          # Регистрация/логин
│   ├── transactions.py  # Транзакции/дашборд
│   ├── learning.py      # Модули/уроки
│   ├── stocks.py        # Акции/портфолио
│   └── gamification.py  # Достижения/миссии
├── schemas/             # Pydantic модели
│   ├── auth.py
│   ├── transactions.py
│   ├── learning.py
│   ├── stocks.py
│   └── gamification.py
└── services/            # Бизнес-логика
    └── llm_service.py   # LLM с fallback
```

### Ключевые особенности:

- ✅ **Модульная архитектура** - 19 модулей вместо 1 файла
- ✅ **Безопасность** - bcrypt для паролей
- ✅ **LLM Fallback** - работает даже без API ключа
- ✅ **Чистый код** - разделение по доменам
- ✅ **Production Ready** - готово к деплою

---

## 🛠 Технологический стек

### Backend
- **FastAPI** - Async веб-фреймворк
- **PostgreSQL** - Реляционная БД
- **SQLAlchemy** - Async ORM
- **Pydantic** - Валидация данных
- **passlib** - Хеширование паролей (bcrypt)
- **Docker** - Контейнеризация

### DevOps
- **Docker Compose** - Оркестрация
- **Git** - Контроль версий

---

## 📡 API Endpoints

### Аутентификация
- `POST /api/register` - Регистрация (с bcrypt)
- `POST /api/login` - Вход (проверка пароля)

### Транзакции
- `GET /api/dashboard?userId=...` - Дашборд с AI-советами
- `GET /api/transactions?userId=...` - Список транзакций
- `POST /api/transactions` - Добавить транзакцию
- `DELETE /api/transactions/{id}` - Удалить транзакцию
- `POST /api/evaluate-purchase` - AI оценка покупки

### Обучение
- `GET /api/v2/modules?userId=...` - Модули
- `GET /api/v2/lessons?userId=...&moduleId=...` - Уроки
- `GET /api/v2/lesson/{id}?userId=...` - Детали урока
- `POST /api/v2/complete-lesson` - Завершить урок
- `POST /api/v2/generate-lesson` - Генерация урока (LLM + fallback)

### Акции
- `GET /api/portfolio?userId=...` - Портфолио
- `GET /api/stocks?userId=...` - Список акций
- `POST /api/trade` - Купить/продать акции
- `GET /api/market-event?userId=...` - Рыночные события

### Геймификация
- `GET /api/achievements?userId=...` - Достижения
- `GET /api/daily-missions?userId=...` - Ежедневные миссии
- `GET /api/progress?userId=...` - Прогресс пользователя
- `POST /api/buy-freeze` - Купить заморозку streak

### Онбординг
- `GET /api/onboarding/status?userId=...` - Статус
- `GET /api/onboarding/questions` - Вопросы
- `POST /api/onboarding/submit` - Отправить ответы

**Полная документация:** http://localhost:8000/docs

---

## 🔐 Безопасность

- **Пароли**: bcrypt хеширование (passlib)
- **Валидация**: Pydantic schemas
- **SQL Injection**: SQLAlchemy ORM
- **CORS**: Настраиваемые origins
- **Timeout**: 10 секунд на LLM запросы

---

## 🔧 Разработка

### Локальный запуск без Docker:

```bash
# Создать venv
python3 -m venv venv
source venv/bin/activate

# Установить зависимости
cd backend
pip install -r requirements.txt

# Запустить PostgreSQL
docker run -d -p 5432:5432 \
  -e POSTGRES_USER=finuser \
  -e POSTGRES_PASSWORD=finpass123 \
  -e POSTGRES_DB=financedb \
  postgres:15-alpine

# Создать .env
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://finuser:finpass123@localhost:5432/financedb
OPENROUTER_API_KEY=
ALLOWED_ORIGINS=http://localhost:8080,http://localhost:5173,http://localhost:3000
EOF

# Запустить backend
uvicorn main:app --reload
```

### Инициализация тестовых данных:

```bash
python backend/init_data.py
```

### Полезные команды:

```bash
# Логи
docker-compose logs -f backend

# Рестарт
docker-compose restart backend

# Остановка
docker-compose down

# Полная очистка
docker-compose down -v
```

---

## 📊 База данных

### Основные таблицы:

- **users** - Пользователи (с password_hash)
- **transactions** - Транзакции
- **achievements** - Достижения
- **modules** - Модули обучения
- **lessons** - Уроки
- **stocks** - Акции
- **daily_missions** - Ежедневные миссии
- **adaptive_mastery** - Адаптивное обучение

---

## 📝 Переменные окружения

Создайте `.env` файл:

```env
DATABASE_URL=postgresql+asyncpg://finuser:finpass123@localhost:5432/financedb
OPENROUTER_API_KEY=your_key_here  # Опционально
ALLOWED_ORIGINS=http://localhost:8080,http://localhost:5173,http://localhost:3000
```

---

## 🎯 Roadmap

- [x] Модульная архитектура
- [x] bcrypt хеширование паролей
- [x] LLM fallback механизм
- [x] Docker setup
- [ ] JWT аутентификация
- [ ] Alembic миграции
- [ ] Pytest тесты
- [ ] CI/CD (GitHub Actions)
- [ ] Sentry мониторинг
- [ ] Rate limiting

---

## 🐛 Отладка

### Backend не запускается:

```bash
docker logs fin_backend
docker exec -it fin_db psql -U finuser -d financedb
```

### База данных не инициализируется:

```bash
docker-compose down -v
docker-compose up -d
docker exec -it fin_backend python init_data.py
```

---

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/amazing`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing`)
5. Откройте Pull Request

---

## 📄 Лицензия

MIT License

---

## 👥 Команда

Разработано командой **Starwatch-kg**
- GitHub: [@H1ytoozxc](https://github.com/H1ytoozxc)
- GitHub: [@Starwatch-kg](https://github.com/Starwatch-kg)

---

**Версия**: 2.0.0-modular  
**Архитектура**: Модульный монолит  
**Статус**: Production Ready ✅

Сделано с ❤️ для финансовой грамотности
