# ШАГ 3: СТРУКТУРА ПРОЕКТА (Monorepo)

## 📁 РЕКОМЕНДУЕМАЯ СТРУКТУРА

```
FinKernel/
├── README.md                    # Главная документация
├── .gitignore                   # Игнорируемые файлы
├── docker-compose.yml           # Общий Docker Compose
├── .env.example                 # Пример переменных окружения
│
├── backend/                     # FastAPI сервер
│   ├── main.py                  # Главный файл приложения
│   ├── models.py                # SQLAlchemy модели
│   ├── llm_agent.py             # LLM агент (с fallback)
│   ├── security.py              # Утилиты безопасности
│   ├── init_data.py             # Скрипт инициализации данных
│   ├── requirements.txt         # Python зависимости
│   ├── Dockerfile               # Docker образ для бэкенда
│   ├── .env                     # Переменные окружения (не в git)
│   └── tests/                   # Тесты (будущее)
│       └── test_api.py
│
├── frontend/                    # React приложение
│   ├── src/
│   │   ├── api.js               # API клиент
│   │   ├── App.jsx              # Главный компонент
│   │   ├── main.jsx             # Entry point
│   │   ├── settings.js          # Настройки
│   │   ├── DevContext.js        # Dev контекст
│   │   ├── components/          # Компоненты
│   │   │   ├── Sidebar.jsx
│   │   │   ├── Tutorial.jsx
│   │   │   └── motion/          # Анимации
│   │   ├── screens/             # Экраны
│   │   │   ├── HomeScreen.jsx
│   │   │   ├── AuthScreen.jsx
│   │   │   ├── PortfolioScreen.jsx
│   │   │   ├── LearnScreen.jsx
│   │   │   ├── LessonScreen.jsx
│   │   │   ├── AchievementsScreen.jsx
│   │   │   ├── SettingsScreen.jsx
│   │   │   ├── AboutScreen.jsx
│   │   │   └── OnboardingScreen.jsx
│   │   └── hooks/               # Custom hooks
│   │       └── useIsMobile.js
│   ├── public/                  # Статические файлы
│   ├── index.html               # HTML шаблон
│   ├── package.json             # NPM зависимости
│   ├── vite.config.js           # Vite конфигурация
│   ├── eslint.config.js         # ESLint правила
│   ├── Dockerfile               # Docker образ для фронтенда
│   ├── nginx.conf               # Nginx конфигурация
│   └── .env.local               # Переменные окружения (не в git)
│
└── docs/                        # Дополнительная документация
    ├── API.md                   # API спецификация
    ├── DEPLOYMENT.md            # Инструкции по деплою
    └── CONTRIBUTING.md          # Гайд для контрибьюторов
```

## 🔧 ОБНОВЛЕННЫЙ docker-compose.yml

```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: finkernel-db
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-finuser}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-finpass123}
      POSTGRES_DB: ${POSTGRES_DB:-financedb}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - finkernel-network

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: finkernel-api
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-finuser}:${POSTGRES_PASSWORD:-finpass123}@db:5432/${POSTGRES_DB:-financedb}
      OPENROUTER_API_KEY: ${OPENROUTER_API_KEY:-}
      ALLOWED_ORIGINS: ${ALLOWED_ORIGINS:-http://localhost:5173,http://localhost:3000}
    ports:
      - "8000:8000"
    depends_on:
      - db
    networks:
      - finkernel-network
    volumes:
      - ./backend:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: finkernel-web
    ports:
      - "5173:80"
    depends_on:
      - backend
    networks:
      - finkernel-network
    environment:
      VITE_API_URL: http://localhost:8000/api

volumes:
  postgres_data:

networks:
  finkernel-network:
    driver: bridge
```

## 📝 .gitignore (корневой)

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
*.egg-info/
dist/
build/

# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.pnpm-debug.log*
dist/
.vite/

# Environment
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Claude
.claude/

# Database
*.db
*.sqlite
postgres_data/

# Logs
*.log
logs/

# Docker
.dockerignore

# Testing
.coverage
htmlcov/
.pytest_cache/
```

## 🚀 ПРЕИМУЩЕСТВА ЭТОЙ СТРУКТУРЫ

1. **Четкое разделение** - фронт и бэк в отдельных папках
2. **Единый Docker Compose** - запуск всего проекта одной командой
3. **Общая документация** - README в корне
4. **Масштабируемость** - легко добавить mobile, admin и т.д.
5. **CI/CD friendly** - каждая часть может деплоиться отдельно
