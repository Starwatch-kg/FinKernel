# ШАГ 5: ПЛАН СЛИЯНИЯ В MAIN

## 🎯 ЦЕЛЬ
Безопасно перенести backend и frontend в ветку main с правильной monorepo структурой.

## ⚠️ ВАЖНО ПЕРЕД НАЧАЛОМ
1. Убедитесь, что все изменения закоммичены
2. Сделайте backup (опционально): `git clone . ../FinKernel-backup`
3. Убедитесь, что Docker контейнеры остановлены: `docker-compose down`

---

## 📋 ПОШАГОВЫЕ КОМАНДЫ

### Этап 1: Подготовка (на ветке backend)

```bash
# Убедитесь, что вы на ветке backend
git checkout backend

# Закоммитьте все изменения
git add main.py models.py llm_agent.py security.py
git commit -m "fix: исправлены форматы API, добавлены заглушки, улучшена безопасность"

# Запушьте изменения
git push origin backend

# Проверьте статус
git status
```

### Этап 2: Создание новой структуры в main

```bash
# Переключитесь на main (или создайте, если нет)
git checkout main || git checkout -b main

# Создайте структуру папок
mkdir -p backend frontend docs

# Скопируйте файлы backend из ветки backend
git checkout backend -- main.py models.py llm_agent.py security.py init_data.py requirements.txt Dockerfile docker-compose.yml .env.example .gitignore

# Переместите backend файлы в папку backend/
mv main.py models.py llm_agent.py security.py init_data.py requirements.txt Dockerfile backend/
mv .env.example backend/.env.example

# Создайте backend/.gitignore
cat > backend/.gitignore << 'EOF'
__pycache__/
*.py[cod]
.env
*.db
.pytest_cache/
EOF
```

### Этап 3: Добавление frontend

```bash
# Скопируйте файлы frontend из ветки frontend
git checkout frontend -- src/ public/ index.html package.json package-lock.json vite.config.js eslint.config.js nginx.conf Dockerfile .dockerignore

# Переместите frontend файлы в папку frontend/
mv src/ public/ index.html package.json package-lock.json vite.config.js eslint.config.js nginx.conf Dockerfile .dockerignore frontend/

# Создайте frontend/.env.local.example
cat > frontend/.env.local.example << 'EOF'
VITE_API_URL=http://localhost:8000/api
EOF

# Создайте frontend/.gitignore
cat > frontend/.gitignore << 'EOF'
node_modules/
dist/
.vite/
.env.local
*.log
EOF
```

### Этап 4: Создание корневых файлов

```bash
# Скопируйте Ultimate README
cp ULTIMATE_README.md README.md

# Создайте корневой .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*.so
.Python
venv/
ENV/
*.egg-info/

# Node
node_modules/
npm-debug.log*
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
.DS_Store

# Claude
.claude/

# Database
*.db
*.sqlite
postgres_data/

# Logs
*.log

# Docker
.dockerignore
EOF

# Создайте корневой docker-compose.yml
cat > docker-compose.yml << 'EOF'
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
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U finuser"]
      interval: 10s
      timeout: 5s
      retries: 5

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
      db:
        condition: service_healthy
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
EOF

# Создайте корневой .env.example
cat > .env.example << 'EOF'
# Database
POSTGRES_USER=finuser
POSTGRES_PASSWORD=finpass123
POSTGRES_DB=financedb

# Backend
DATABASE_URL=postgresql+asyncpg://finuser:finpass123@db:5432/financedb
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
OPENROUTER_API_KEY=

# Frontend
VITE_API_URL=http://localhost:8000/api
EOF
```

### Этап 5: Создание документации

```bash
# Создайте папку docs
mkdir -p docs

# Переместите документы
mv API_AUDIT.md CODE_REVIEW.md PROJECT_STRUCTURE.md docs/

# Создайте docs/API.md (краткая спецификация)
cat > docs/API.md << 'EOF'
# API Спецификация

## Base URL
`http://localhost:8000/api`

## Аутентификация
- POST `/register` - Регистрация
- POST `/login` - Вход

## Пользователь
- GET `/dashboard?userId={id}` - Дашборд
- GET `/progress?userId={id}` - Прогресс

## Транзакции
- GET `/transactions?userId={id}` - Список
- POST `/transactions` - Создать
- DELETE `/transactions/{id}` - Удалить

## Обучение
- GET `/v2/modules?userId={id}` - Модули
- GET `/v2/lessons?userId={id}&moduleId={id}` - Уроки
- GET `/v2/lesson/{id}?userId={id}` - Детали
- POST `/v2/complete-lesson` - Завершить

## Достижения
- GET `/achievements?userId={id}` - Список

Полная документация: http://localhost:8000/docs
EOF
```

### Этап 6: Коммит и push

```bash
# Добавьте все файлы
git add .

# Проверьте, что добавилось
git status

# Создайте коммит
git commit -m "feat: monorepo структура с backend и frontend

- Разделены backend и frontend в отдельные папки
- Обновлен docker-compose.yml для monorepo
- Добавлена полная документация (README.md)
- Исправлены форматы API (body вместо query params)
- Добавлены заглушки для неиспользуемых эндпоинтов
- Улучшена безопасность (CORS из .env, валидация email)
- Добавлено логирование
- Создана документация в docs/

BREAKING CHANGES:
- Изменена структура проекта (monorepo)
- API эндпоинты теперь принимают данные из body"

# Запушьте в main
git push origin main

# Если main не существует на remote, создайте:
git push -u origin main
```

### Этап 7: Проверка

```bash
# Клонируйте репозиторий в новую папку для проверки
cd ..
git clone https://github.com/Starwatch-kg/FinKernel.git FinKernel-test
cd FinKernel-test

# Проверьте структуру
ls -la
tree -L 2  # если установлен tree

# Запустите проект
cp .env.example .env
docker-compose up --build -d

# Инициализируйте данные
docker exec -it finkernel-api python init_data.py

# Откройте http://localhost:5173
```

---

## 🔄 АЛЬТЕРНАТИВНЫЙ СПОСОБ (Если возникли проблемы)

### Вариант 2: Создание main с нуля

```bash
# Создайте новую ветку main от пустого коммита
git checkout --orphan main-new
git rm -rf .

# Создайте структуру вручную
mkdir -p backend frontend docs

# Скопируйте файлы из веток
# ... (повторите шаги 2-5 выше)

# Переименуйте ветку
git branch -m main-new main
git push -f origin main
```

---

## ✅ ЧЕКЛИСТ ПОСЛЕ СЛИЯНИЯ

- [ ] Структура папок соответствует monorepo
- [ ] README.md в корне проекта
- [ ] docker-compose.yml запускает все сервисы
- [ ] Backend доступен на :8000
- [ ] Frontend доступен на :5173
- [ ] Swagger UI работает на :8000/docs
- [ ] Тестовые данные создаются через init_data.py
- [ ] .gitignore корректно игнорирует файлы
- [ ] Ветки backend и frontend сохранены (не удалены)

---

## 🚨 ОТКАТ (Если что-то пошло не так)

```bash
# Вернитесь к предыдущему состоянию
git checkout backend  # или frontend

# Или восстановите из backup
cd ..
rm -rf FinKernel
mv FinKernel-backup FinKernel
cd FinKernel
```

---

## 📝 ПОСЛЕ УСПЕШНОГО СЛИЯНИЯ

1. Обновите README на GitHub (добавьте badges, скриншоты)
2. Создайте Release v1.0.0
3. Добавьте CONTRIBUTING.md для контрибьюторов
4. Настройте GitHub Actions для CI/CD (опционально)
5. Удалите временные файлы (API_AUDIT.md, CODE_REVIEW.md из корня)

---

## 🎉 ГОТОВО!

Теперь у вас есть чистая monorepo структура в ветке main, готовая к релизу и защите проекта!
