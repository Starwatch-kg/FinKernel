# 🏦 FinFuture - Умный финансовый ассистент

> Полнофункциональное приложение для управления личными финансами с AI-советником, геймификацией, портфелем акций и адаптивным обучением.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19+-61DAFB.svg)](https://reactjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791.svg)](https://www.postgresql.org/)

---

## 📖 Описание проекта

**FinFuture** — это современное приложение для финансовой грамотности, которое помогает пользователям:
- 💰 Отслеживать доходы и расходы в реальном времени
- 📊 Анализировать траты с помощью AI-советов
- 📈 Управлять портфелем акций (симуляция)
- 🎯 Реагировать на рыночные события
- 📚 Изучать финансовую грамотность через адаптивные уроки
- 🏆 Получать достижения и выполнять ежедневные миссии
- 🎮 Повышать уровень и зарабатывать XP

### Ключевые особенности

✅ **Умный дашборд** - Баланс, прогноз, AI-советы на основе ваших трат  
✅ **Портфель акций** - Покупка/продажа 6 акций (AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA)  
✅ **Рыночные события** - Динамические события с выбором действий  
✅ **Адаптивное обучение** - 15 модулей с персонализированными вопросами  
✅ **Ежедневные миссии** - Новые задания каждый день  
✅ **Геймификация** - 12 достижений, уровни, XP, streak система  
✅ **LLM интеграция** - Генерация уроков и вопросов через OpenRouter (опционально)  
✅ **Красивый UI** - Плавные анимации (Framer Motion), адаптивный дизайн  

---

## 🛠 Технологический стек

### Backend
- **FastAPI** - Async веб-фреймворк с автоматической документацией
- **PostgreSQL 15** - Реляционная база данных
- **SQLAlchemy 2.0** - Async ORM
- **Pydantic** - Валидация данных и схемы
- **OpenRouter API** - LLM интеграция (Claude 3.5 Sonnet)
- **asyncpg** - Async PostgreSQL драйвер

### Frontend
- **React 19** - UI библиотека
- **Vite** - Быстрый build tool
- **Framer Motion** - Анимации и transitions
- **Recharts** - Графики и визуализация данных
- **Fetch API** - HTTP клиент

### Infrastructure
- **Docker Compose** - Оркестрация контейнеров
- **PostgreSQL** - Persistent storage
- **Nginx** - Production web server (опционально)

---

## 📁 Структура проекта

```
FIN/
├── backend/
│   ├── main.py              # FastAPI приложение, все эндпоинты (18 endpoints)
│   ├── models.py            # SQLAlchemy модели (15 таблиц)
│   ├── llm_agent.py         # OpenRouter интеграция для LLM
│   ├── init_data.py         # Инициализация достижений, модулей, уроков
│   ├── init_stocks.py       # Инициализация акций, событий, вопросов
│   ├── requirements.txt     # Python зависимости
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── screens/         # React компоненты страниц
│   │   │   ├── HomeScreen.jsx
│   │   │   ├── AuthScreen.jsx
│   │   │   ├── TransactionsScreen.jsx
│   │   │   ├── StocksScreen.jsx
│   │   │   ├── LearningScreen.jsx
│   │   │   ├── AchievementsScreen.jsx
│   │   │   └── ProfileScreen.jsx
│   │   ├── api.js           # API клиент
│   │   └── App.jsx          # Главный компонент с роутингом
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
│
├── docker-compose.yml       # Оркестрация (db, backend, frontend)
├── .env                     # Переменные окружения
└── README.md                # Документация
```

---

## 🚀 Быстрый старт

### Требования

- **Docker 20.10+** и **Docker Compose 2.0+**
- **2GB свободной RAM**
- **Свободные порты:** 5174 (frontend), 8001 (backend), 5432 (postgres)

---

### macOS

```bash
# 1. Установите Docker Desktop
# Скачайте с https://www.docker.com/products/docker-desktop

# 2. Клонируйте репозиторий
git clone <repository-url>
cd FIN

# 3. Создайте .env файл (опционально)
cp .env.example .env
# Отредактируйте .env если нужно изменить пароли или добавить OPENROUTER_API_KEY

# 4. Запустите проект
docker compose up -d

# 5. Дождитесь запуска (10-15 секунд)
docker compose ps

# 6. Инициализируйте данные
docker exec -it finkernel-api python init_data.py
docker exec -it finkernel-api python init_stocks.py

# 7. Откройте приложение
open http://localhost:5174
```

---

### Windows

```powershell
# 1. Установите Docker Desktop
# Скачайте с https://www.docker.com/products/docker-desktop
# Включите WSL 2 backend в настройках Docker Desktop

# 2. Клонируйте репозиторий
git clone <repository-url>
cd FIN

# 3. Создайте .env файл (опционально)
copy .env.example .env
# Отредактируйте .env в блокноте если нужно

# 4. Запустите проект
docker compose up -d

# 5. Дождитесь запуска (10-15 секунд)
docker compose ps

# 6. Инициализируйте данные
docker exec -it finkernel-api python init_data.py
docker exec -it finkernel-api python init_stocks.py

# 7. Откройте приложение
start http://localhost:5174
```

---

### Linux

```bash
# 1. Установите Docker и Docker Compose
sudo apt-get update
sudo apt-get install docker.io docker-compose-plugin

# 2. Добавьте пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker

# 3. Клонируйте репозиторий
git clone <repository-url>
cd FIN

# 4. Создайте .env файл (опционально)
cp .env.example .env
nano .env  # Отредактируйте если нужно

# 5. Запустите проект
docker compose up -d

# 6. Дождитесь запуска (10-15 секунд)
docker compose ps

# 7. Инициализируйте данные
docker exec -it finkernel-api python init_data.py
docker exec -it finkernel-api python init_stocks.py

# 8. Откройте приложение
xdg-open http://localhost:5174
```

---

### Доступ к приложению

- **Frontend:** http://localhost:5174
- **Backend API:** http://localhost:8001
- **API Docs (Swagger):** http://localhost:8001/docs
- **PostgreSQL:** localhost:5432

### Тестовые аккаунты

**Гость:**
- Email: `guest@finfuture.app`
- Пароль: `guest12345`

**Админ:**
- Email: `admin@finfuture.app`
- Пароль: `admin12345`

---

## 🎮 Основные функции

### 1. Управление финансами
- ✅ Учёт доходов и расходов
- ✅ Категоризация транзакций (еда, транспорт, развлечения и т.д.)
- ✅ Прогноз баланса (сколько дней хватит денег)
- ✅ Статистика по категориям с графиками
- ✅ AI-советы на основе паттернов трат

### 2. Портфель акций (симуляция)
- ✅ Покупка/продажа 6 акций: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA
- ✅ Отслеживание портфеля в реальном времени
- ✅ Расчёт прибыли/убытка
- ✅ Рыночные события с выбором действий
- ✅ Динамические изменения цен

### 3. Обучение
- ✅ 15 модулей по финансовой грамотности
- ✅ Интерактивные уроки с вопросами
- ✅ Адаптивная система (mastery level 0-100%)
- ✅ Персонализированные вопросы на основе слабых тем
- ✅ LLM-генерация уроков (опционально)

### 4. Геймификация
- ✅ 12 достижений в 4 категориях (экономия, бюджет, дисциплина, серия)
- ✅ Система уровней (1-50) и XP
- ✅ Ежедневные миссии (3 типа)
- ✅ Streak система (поддержание активности)
- ✅ Финансовый скоринг (0-1000)

### 5. AI-советник
- ✅ Персональные рекомендации на основе трат
- ✅ Анализ категорий расходов
- ✅ Предупреждения о критическом балансе
- ✅ Генерация адаптивных вопросов через LLM (опционально)

---

## 🗄️ База данных (15 таблиц)

### Основные таблицы

**users** - Пользователи
- id, username, email, name, password_hash
- current_balance, financial_score, level, xp, streak
- last_activity, onboarding_completed, created_at

**transactions** - Транзакции
- id, user_id, amount, category, description, timestamp

**achievements** - Достижения
- id, name, description, icon, category, xp_reward, condition_type, condition_value

**user_achievements** - Связь пользователей и достижений
- id, user_id, achievement_id, unlocked_at

**modules** - Обучающие модули
- id, title, description, icon, order_index

**lessons** - Уроки
- id, module_id, title, content, questions (JSON), xp_reward, order_index

**user_lessons** - Прогресс по урокам
- id, user_id, lesson_id, completed, score, completed_at

### Акции и портфель

**stocks** - Акции
- id, ticker, name, current_price, change_percent, sector

**user_stocks** - Портфель пользователя
- id, user_id, stock_id, shares, avg_buy_price

**market_events** - Рыночные события
- id, title, description, event_type, impact, options (JSON), expires_at

**user_market_event_actions** - Действия пользователей на события
- id, user_id, event_id, action_taken, result, created_at

### Миссии и адаптивное обучение

**daily_missions** - Ежедневные миссии
- id, title, description, mission_type, target_value, xp_reward, active_date

**user_daily_missions** - Прогресс по миссиям
- id, user_id, mission_id, progress, completed, claimed, completed_at

**adaptive_mastery** - Уровень владения темами
- id, user_id, topic, mastery_level, correct_answers, total_answers, last_question_at

**adaptive_questions** - Банк вопросов
- id, topic, difficulty, question_text, options (JSON), correct_answer, explanation

---

## 📡 API Endpoints (18 эндпоинтов)

### Authentication
- `POST /api/register` - Регистрация нового пользователя
- `POST /api/login` - Вход в систему

### User & Dashboard
- `GET /api/user` - Профиль пользователя (баланс, уровень, XP, streak)
- `GET /api/dashboard` - Дашборд (транзакции, прогноз, AI-советы, статистика)

### Transactions
- `POST /api/transactions` - Создать транзакцию (доход/расход)
- `GET /api/transactions` - Список транзакций пользователя

### Stocks & Portfolio
- `GET /api/stocks` - Список всех акций с текущими ценами
- `GET /api/portfolio` - Портфель пользователя (акции, прибыль/убыток)
- `POST /api/trade` - Купить/продать акцию

### Learning
- `GET /api/modules` - Список обучающих модулей
- `GET /api/modules/{id}/lessons` - Уроки конкретного модуля
- `POST /api/lessons/{id}/complete` - Завершить урок (получить XP)
- `GET /api/adaptive/question` - Получить адаптивный вопрос
- `POST /api/adaptive/answer` - Ответить на вопрос (обновить mastery)

### Gamification
- `GET /api/achievements` - Список достижений (открытые/закрытые)
- `GET /api/missions` - Ежедневные миссии
- `POST /api/missions/{id}/claim` - Забрать награду за миссию

### Market Events
- `GET /api/market-events` - Активные рыночные события
- `POST /api/market-events/{id}/action` - Выбрать действие на событие

**Полная документация:** http://localhost:8001/docs (Swagger UI)

---

## ⚙️ Конфигурация

### Переменные окружения (.env)

```env
# Database
POSTGRES_USER=finuser
POSTGRES_PASSWORD=finpass123
POSTGRES_DB=financedb

# Backend
DATABASE_URL=postgresql+asyncpg://finuser:finpass123@db:5432/financedb
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:3000,http://localhost:8001
OPENROUTER_API_KEY=  # Опционально, для LLM функций

# Frontend
VITE_API_URL=http://localhost:8001/api
```

### Настройка LLM (опционально)

Для использования AI-генерации уроков и адаптивных вопросов:

1. Получите API ключ на https://openrouter.ai
2. Добавьте в `.env`:
   ```env
   OPENROUTER_API_KEY=sk-or-v1-...
   ```
3. Перезапустите backend:
   ```bash
   docker compose restart backend
   ```

**Без API ключа** приложение работает с заранее созданными уроками и вопросами из `init_data.py` и `init_stocks.py`.

---

## 🔧 Управление проектом

### Просмотр логов

```bash
# Все сервисы
docker compose logs -f

# Только backend
docker compose logs -f backend

# Только frontend
docker compose logs -f frontend

# Только база данных
docker compose logs -f db
```

### Перезапуск сервисов

```bash
# Все сервисы
docker compose restart

# Только backend (после изменений в коде)
docker compose restart backend

# Только frontend
docker compose restart frontend
```

### Остановка проекта

```bash
# Остановить контейнеры (данные сохраняются)
docker compose stop

# Остановить и удалить контейнеры (данные сохраняются)
docker compose down

# Удалить всё включая данные БД (полная очистка)
docker compose down -v
```

### Пересборка после изменений

```bash
# Пересобрать все образы
docker compose build

# Пересобрать и запустить
docker compose up -d --build

# Пересобрать только backend
docker compose build backend
docker compose up -d backend
```

### Подключение к базе данных

```bash
# Через psql
docker exec -it finkernel-db psql -U finuser -d financedb

# Список таблиц
\dt

# Описание таблицы users
\d users

# Выход
\q
```

### Сброс базы данных

```bash
# Удалить volume с данными
docker compose down -v

# Запустить заново
docker compose up -d

# Дождаться запуска БД (10-15 секунд)
docker compose ps

# Переинициализировать данные
docker exec -it finkernel-api python init_data.py
docker exec -it finkernel-api python init_stocks.py
```

---

## 🐛 Troubleshooting

### Порт уже занят

```bash
# Найти процесс на порту 5174 (frontend)
lsof -i :5174  # macOS/Linux
netstat -ano | findstr :5174  # Windows

# Убить процесс или изменить порт в docker-compose.yml
```

### Контейнер не запускается

```bash
# Проверить логи
docker compose logs backend

# Проверить статус всех контейнеров
docker compose ps

# Пересобрать образ без кэша
docker compose build backend --no-cache
docker compose up -d backend
```

### База данных не инициализируется

```bash
# Проверить что БД здорова
docker compose ps db
# Должно быть: STATUS = Up (healthy)

# Подождать 10-15 секунд после первого запуска
# Затем запустить init скрипты
docker exec -it finkernel-api python init_data.py
docker exec -it finkernel-api python init_stocks.py
```

### Frontend показывает NetworkError

1. Проверьте что backend запущен: http://localhost:8001/docs
2. Проверьте CORS настройки в `backend/main.py` (должно быть `allow_origins=["*"]`)
3. Проверьте `VITE_API_URL` в `.env` и `frontend/.env.local`
4. Перезапустите frontend: `docker compose restart frontend`
5. Очистите кэш браузера (Ctrl+Shift+R)

### Permission denied для Docker (Linux)

```bash
# Добавить пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker

# Перезапустить Docker daemon
sudo systemctl restart docker
```

### Ошибка "column users.email does not exist"

Это означает что БД создана со старой схемой. Решение:

```bash
# Удалить volume и пересоздать БД
docker compose down -v
docker compose up -d
docker exec -it finkernel-api python init_data.py
docker exec -it finkernel-api python init_stocks.py
```

---

## 💻 Локальная разработка (без Docker)

### Backend

```bash
cd backend

# Создайте виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установите зависимости
pip install -r requirements.txt

# Запустите PostgreSQL отдельно или измените DATABASE_URL
export DATABASE_URL=postgresql+asyncpg://finuser:finpass123@localhost:5432/financedb

# Запустите сервер
uvicorn main:app --reload --port 8001
```

### Frontend

```bash
cd frontend

# Установите зависимости
npm install

# Создайте .env.local
echo 'VITE_API_URL=http://localhost:8001/api' > .env.local

# Запустите dev сервер
npm run dev
```

---

## 📝 Тестовые данные

После запуска `init_data.py` создаются:

### Достижения (12 шт.)
- 🎯 **Первые шаги** - Совершите первую транзакцию (50 XP)
- 💰 **Экономный** - Накопите 10000 рублей (100 XP)
- 🏆 **Финансовый гуру** - Достигните 10 уровня (500 XP)
- 🔥 **Постоянство** - Поддерживайте серию 7 дней (200 XP)
- 📚 **Ученик** - Завершите 5 уроков (150 XP)
- 💎 **Миллионер** - Накопите 1000000 рублей (1000 XP)
- 📊 **Бюджетный мастер** - Создайте бюджет на месяц (300 XP)
- 🎓 **Профессор** - Завершите все модули (800 XP)
- ⚡ **Молния** - Серия 30 дней (500 XP)
- 🌟 **Легенда** - Достигните 50 уровня (2000 XP)
- 📈 **Инвестор** - Купите первую акцию (100 XP)
- 💼 **Трейдер** - Совершите 10 сделок (300 XP)

### Модули (15 шт.)
1. **Основы финансовой грамотности** - Базовые концепции
2. **Бюджетирование** - Планирование расходов
3. **Инвестиции для начинающих** - Введение в инвестиции
4. **Управление долгами** - Как избавиться от долгов
5. **Пенсионное планирование** - Подготовка к пенсии
6. **Налоги** - Основы налогообложения
7. **Страхование** - Виды страхования
8. **Недвижимость** - Покупка и аренда
9. **Кредиты** - Как правильно брать кредиты
10. **Фондовый рынок** - Акции и облигации
11. **Криптовалюты** - Введение в крипто
12. **Финансовая безопасность** - Защита от мошенников
13. **Предпринимательство** - Основы бизнеса
14. **Психология денег** - Финансовое мышление
15. **Финансовая независимость** - Путь к FIRE

После запуска `init_stocks.py` создаются:

### Акции (6 шт.)
- **AAPL** - Apple Inc. ($150.00)
- **GOOGL** - Alphabet Inc. ($120.00)
- **MSFT** - Microsoft Corp. ($280.00)
- **AMZN** - Amazon.com Inc. ($140.00)
- **TSLA** - Tesla Inc. ($200.00)
- **NVDA** - NVIDIA Corp. ($450.00)

### Рыночное событие
- 📈 **Рост технологического сектора** - Акции tech-компаний растут на 5-10%

### Адаптивные вопросы (5 шт.)
- Бюджетирование, Инвестиции, Долги, Накопления, Налоги

---

## 🚀 Производственный деплой

### Рекомендации для продакшена

1. **Измените пароли** в `.env` на сильные
2. **Настройте CORS** - укажите конкретные домены в `ALLOWED_ORIGINS`
3. **Добавьте HTTPS** - используйте Nginx + Let's Encrypt
4. **Настройте бэкапы БД** - регулярные pg_dump
5. **Мониторинг** - добавьте логирование и алерты (Sentry, Prometheus)
6. **Масштабирование** - используйте несколько инстансов backend за load balancer
7. **Безопасность** - включите rate limiting, добавьте JWT валидацию

### Пример Nginx конфигурации

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:5174;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /api {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 🤝 Вклад в проект

Мы приветствуем вклад в развитие проекта!

1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

---

## 📄 Лицензия

Этот проект распространяется под лицензией MIT.

---

**Сделано с ❤️ для финансовой грамотности**
