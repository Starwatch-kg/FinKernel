# 🏦 FinKernel - Финансовый AI-ассистент

> Полноценное веб-приложение для управления личными финансами с AI-движком, образовательной платформой и системой геймификации.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://reactjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791.svg)](https://www.postgresql.org/)

---

## 📖 Описание проекта

**FinKernel** — это современное приложение для финансовой грамотности, которое помогает пользователям:
- 💰 Отслеживать доходы и расходы в реальном времени
- 📊 Анализировать траты с помощью AI-советов
- 📚 Изучать финансовую грамотность через интерактивные уроки
- 🏆 Получать достижения и повышать уровень
- 🎯 Оценивать импульсивные покупки перед их совершением

### Ключевые особенности

✅ **Умный дашборд** - Баланс, прогноз, AI-советы на основе ваших трат  
✅ **Образовательная платформа** - 3 модуля, 6+ уроков по финансовой грамотности  
✅ **Геймификация** - Уровни, XP, streak, достижения  
✅ **AI-оценка покупок** - Проверьте, стоит ли тратить деньги  
✅ **Адаптивный интерфейс** - Красивые анимации (Framer Motion)  
✅ **Онбординг** - Персонализированный опыт для новых пользователей  

---

## 🛠 Технологический стек

### Backend
- **FastAPI** - Современный async веб-фреймворк
- **PostgreSQL** - Надежная реляционная БД
- **SQLAlchemy** - Async ORM для работы с БД
- **Pydantic** - Валидация данных
- **Docker** - Контейнеризация

### Frontend
- **React 18** - UI библиотека
- **Vite** - Быстрый сборщик
- **Framer Motion** - Плавные анимации
- **Fetch API** - HTTP клиент

### DevOps
- **Docker Compose** - Оркестрация контейнеров
- **Nginx** - Веб-сервер для фронтенда
- **Git** - Контроль версий

---

## 📁 Структура проекта

```
FinKernel/
├── backend/              # FastAPI сервер
│   ├── main.py           # Главный файл приложения
│   ├── models.py         # SQLAlchemy модели
│   ├── llm_agent.py      # LLM агент (с fallback)
│   ├── security.py       # Утилиты безопасности
│   ├── init_data.py      # Инициализация тестовых данных
│   └── requirements.txt  # Python зависимости
│
├── frontend/             # React приложение
│   ├── src/
│   │   ├── api.js        # API клиент
│   │   ├── App.jsx       # Главный компонент
│   │   ├── components/   # Переиспользуемые компоненты
│   │   └── screens/      # Экраны приложения
│   ├── package.json      # NPM зависимости
│   └── vite.config.js    # Vite конфигурация
│
├── docker-compose.yml    # Оркестрация сервисов
├── README.md             # Эта документация
└── .env.example          # Пример переменных окружения
```

---

## 🚀 Быстрый старт

### Предварительные требования

- Docker & Docker Compose
- Git
- (Опционально) Node.js 18+ для локальной разработки фронтенда

### 1. Клонирование репозитория

```bash
git clone https://github.com/Starwatch-kg/FinKernel.git
cd FinKernel
```

### 2. Настройка переменных окружения

```bash
# Создайте .env файл в корне проекта
cp .env.example .env

# Отредактируйте .env (опционально)
nano .env
```

**Минимальная конфигурация (.env):**
```env
# Database
POSTGRES_USER=finuser
POSTGRES_PASSWORD=finpass123
POSTGRES_DB=financedb

# Backend
DATABASE_URL=postgresql+asyncpg://finuser:finpass123@db:5432/financedb
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# LLM (опционально)
OPENROUTER_API_KEY=your_key_here

# Frontend
VITE_API_URL=http://localhost:8000/api
```

### 3. Запуск через Docker Compose

```bash
# Запустите все сервисы (БД + Backend + Frontend)
docker-compose up --build -d

# Проверьте статус
docker-compose ps
```

### 4. Инициализация тестовых данных

```bash
# Создайте достижения, модули и уроки
docker exec -it finkernel-api python init_data.py
```

### 5. Откройте приложение

- **Фронтенд:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **Swagger UI:** http://localhost:8000/docs

---

## 🎮 Использование

### Первый запуск

1. Откройте http://localhost:5173
2. Нажмите "Регистрация"
3. Введите email, имя и пароль
4. Пройдите онбординг (3 вопроса)
5. Начните отслеживать финансы!

### Основные функции

#### 💰 Добавление транзакции
1. Перейдите на вкладку "Транзакции"
2. Нажмите "Добавить"
3. Укажите сумму, категорию и описание
4. Ваш баланс обновится автоматически

#### 📚 Прохождение уроков
1. Откройте "Обучение"
2. Выберите модуль
3. Пройдите урок и ответьте на вопросы
4. Получите XP и повысьте уровень!

#### 🏆 Достижения
1. Откройте "Достижения"
2. Просмотрите доступные награды
3. Выполняйте условия для разблокировки

---

## 📡 API Спецификация

### Аутентификация

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| POST | `/api/register` | Регистрация нового пользователя |
| POST | `/api/login` | Вход в систему |

### Пользователь

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/api/dashboard?userId={id}` | Дашборд с балансом и статистикой |
| GET | `/api/progress?userId={id}` | Прогресс пользователя (уровень, XP) |

### Транзакции

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/api/transactions?userId={id}` | Список транзакций |
| POST | `/api/transactions` | Добавить транзакцию |
| DELETE | `/api/transactions/{id}` | Удалить транзакцию |

### Обучение

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/api/v2/modules?userId={id}` | Список модулей |
| GET | `/api/v2/lessons?userId={id}&moduleId={id}` | Уроки модуля |
| GET | `/api/v2/lesson/{id}?userId={id}` | Детали урока |
| POST | `/api/v2/complete-lesson` | Завершить урок |

### Достижения

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/api/achievements?userId={id}` | Список достижений |

### Онбординг

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/api/onboarding/status?userId={id}` | Статус онбординга |
| GET | `/api/onboarding/questions` | Вопросы теста |
| POST | `/api/onboarding/submit` | Отправить ответы |

**Полная документация:** http://localhost:8000/docs (Swagger UI)

---

## 🗄️ База данных

### Схема

```
users
├── id (PK)
├── username
├── email
├── name
├── current_balance
├── financial_score
├── level
├── xp
├── streak
└── onboarding_completed

transactions
├── id (PK)
├── user_id (FK)
├── amount
├── category
├── description
└── timestamp

achievements
├── id (PK)
├── title
├── description
├── icon
├── xp_reward
└── condition_type

modules
├── id (PK)
├── title
├── description
└── required_level

lessons
├── id (PK)
├── module_id (FK)
├── title
├── content
├── questions (JSON)
└── xp_reward
```

---

## 🧪 Тестовые данные

После запуска `init_data.py` создаются:

### Достижения (5 шт.)
- 🎯 **Первые шаги** - Совершите первую транзакцию (50 XP)
- 💰 **Экономный** - Накопите 5000 рублей (100 XP)
- 🏆 **Финансовый гуру** - Достигните 10 уровня (500 XP)
- 🔥 **Постоянство** - Поддерживайте серию 7 дней (200 XP)
- 📚 **Ученик** - Завершите 5 уроков (150 XP)

### Модули (3 шт.)
1. **Основы финансовой грамотности** (3 урока)
2. **Бюджетирование** (2 урока)
3. **Инвестиции для начинающих** (1 урок)

---

## 🔧 Разработка

### Локальный запуск Backend

```bash
cd backend

# Создайте виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установите зависимости
pip install -r requirements.txt

# Запустите сервер
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Локальный запуск Frontend

```bash
cd frontend

# Установите зависимости
npm install

# Создайте .env.local
echo 'VITE_API_URL=http://localhost:8000/api' > .env.local

# Запустите dev сервер
npm run dev
```

### Полезные команды

```bash
# Просмотр логов
docker-compose logs -f backend
docker-compose logs -f frontend

# Перезапуск сервиса
docker-compose restart backend

# Остановка всех сервисов
docker-compose down

# Полная очистка (включая volumes)
docker-compose down -v
```

---

## 🐛 Отладка

### Backend не запускается

```bash
# Проверьте логи
docker logs finkernel-api

# Проверьте подключение к БД
docker exec -it finkernel-db psql -U finuser -d financedb
```

### Frontend показывает ошибки API

```bash
# Проверьте CORS настройки в backend/.env
ALLOWED_ORIGINS=http://localhost:5173

# Проверьте API URL в frontend/.env.local
VITE_API_URL=http://localhost:8000/api
```

### База данных не инициализируется

```bash
# Пересоздайте volume
docker-compose down -v
docker-compose up -d
docker exec -it finkernel-api python init_data.py
```

---

## 📝 Примечания

- **Пароли:** В текущей версии пароли не хешируются (TODO для продакшена)
- **JWT:** Токены не валидируются (используется простая схема)
- **LLM:** Работает с fallback (простой парсинг без AI)
- **Админ:** Пользователь `admin@admin.com` имеет админ-права

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

Этот проект распространяется под лицензией MIT. См. файл `LICENSE` для деталей.

---

## 👥 Команда

Разработано командой **Starwatch-kg**

- GitHub: [@Starwatch-kg](https://github.com/Starwatch-kg)
- Репозиторий: [FinKernel](https://github.com/Starwatch-kg/FinKernel)

---

## 🙏 Благодарности

- [FastAPI](https://fastapi.tiangolo.com/) - за отличный фреймворк
- [React](https://reactjs.org/) - за мощную UI библиотеку
- [Framer Motion](https://www.framer.com/motion/) - за красивые анимации
- [PostgreSQL](https://www.postgresql.org/) - за надежную БД

---

**Сделано с ❤️ для финансовой грамотности**
