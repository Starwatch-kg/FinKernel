#!/bin/bash
# Простой запуск всего проекта

set -e

echo "🚀 Запуск Financial AI Assistant..."
echo ""

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Проверка .env
if [ ! -f .env ]; then
    echo "📝 Создание .env файла..."
    cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://finuser:finpass123@localhost:5432/financedb
OPENROUTER_API_KEY=
ALLOWED_ORIGINS=http://localhost:8080,http://localhost:5173,http://localhost:3000
EOF
    echo "✅ .env создан. Добавьте OPENROUTER_API_KEY если нужно."
fi

# Остановка старых контейнеров
echo "🧹 Очистка старых контейнеров..."
docker-compose down 2>/dev/null || true

# Запуск
echo "🐳 Запуск Docker контейнеров..."
docker-compose up -d --build

# Ожидание БД
echo "⏳ Ожидание PostgreSQL..."
sleep 5

# Инициализация БД
echo "📊 Инициализация базы данных..."
docker-compose exec -T backend python -c "
import asyncio
from backend.core import init_db

async def main():
    await init_db()
    print('✅ База данных инициализирована')

asyncio.run(main())
" 2>/dev/null || echo "⚠️  БД уже инициализирована"

echo ""
echo "✅ Запуск завершен!"
echo ""
echo "📍 Сервисы:"
echo "   Backend:  http://localhost:8000"
echo "   Database: localhost:5432"
echo ""
echo "📝 Команды:"
echo "   Логи:     docker-compose logs -f"
echo "   Остановка: docker-compose down"
echo "   Рестарт:  docker-compose restart"
echo ""
