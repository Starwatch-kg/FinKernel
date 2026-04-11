#!/bin/bash
# Скрипт для применения исправлений финансовой корректности

set -e

echo "🔧 Применение исправлений финансовой корректности..."
echo ""

# Проверка, что мы в правильной директории
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Ошибка: docker-compose.yml не найден"
    echo "Запустите скрипт из корневой директории проекта"
    exit 1
fi

echo "1️⃣ Остановка сервисов..."
docker-compose down

echo ""
echo "2️⃣ Применение миграций БД..."
# Запускаем временный контейнер для миграций
docker-compose run --rm transactions alembic upgrade head

echo ""
echo "3️⃣ Пересборка и запуск сервисов..."
docker-compose up -d --build

echo ""
echo "4️⃣ Ожидание запуска сервисов..."
sleep 10

echo ""
echo "5️⃣ Проверка статуса сервисов..."
docker-compose ps

echo ""
echo "6️⃣ Проверка health endpoints..."
echo "API Gateway:"
curl -s http://localhost:8000/health | jq '.' || echo "❌ API Gateway не отвечает"

echo ""
echo "Transaction Service:"
curl -s http://localhost:8001/health | jq '.' || echo "❌ Transaction Service не отвечает"

echo ""
echo "AI Service:"
curl -s http://localhost:8002/health | jq '.' || echo "❌ AI Service не отвечает"

echo ""
echo "✅ Применение завершено!"
echo ""
echo "📋 Что было исправлено:"
echo "  ✅ Race conditions в транзакциях"
echo "  ✅ Race conditions в торговле"
echo "  ✅ Race conditions в удалении транзакций"
echo "  ✅ Добавлена идемпотентность"
echo "  ✅ Атомарные транзакции БД"
echo ""
echo "📖 Подробности в файле: FINANCIAL_CORRECTNESS_FIXES.md"
echo ""
echo "🧪 Рекомендуется провести тестирование:"
echo "  - Конкурентные транзакции"
echo "  - Повторы запросов (idempotency)"
echo "  - Нагрузочное тестирование"
