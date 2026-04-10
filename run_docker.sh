#!/bin/bash

echo "🐳 Запуск через Docker"
echo ""

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не найден. Установите Docker Desktop"
    exit 1
fi

# Проверка .env файла
if [ ! -f ".env" ]; then
    echo "⚠️  Файл .env не найден. Создайте его из .env.example"
    echo "   cp .env.example .env"
    echo "   Затем добавьте ваш ANTHROPIC_API_KEY"
    exit 1
fi

# Запуск через docker-compose
echo "🚀 Запуск контейнеров..."
docker-compose up --build

echo ""
echo "✅ API доступен на http://localhost:8000"
echo "📚 Документация: http://localhost:8000/docs"
