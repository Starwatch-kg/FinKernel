#!/bin/bash

echo "🚀 Запуск Financial AI Assistant"
echo ""

# Проверка наличия Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python 3.11+"
    exit 1
fi

# Создание виртуального окружения если его нет
if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активация виртуального окружения
echo "🔧 Активация виртуального окружения..."
source venv/bin/activate

# Установка зависимостей
echo "📥 Установка зависимостей..."
pip install -r requirements.txt

# Проверка .env файла
if [ ! -f ".env" ]; then
    echo "⚠️  Файл .env не найден. Создайте его из .env.example"
    echo "   cp .env.example .env"
    echo "   Затем добавьте ваш ANTHROPIC_API_KEY"
    exit 1
fi

# Запуск API сервера
echo ""
echo "✅ Запуск API сервера на http://localhost:8000"
echo "📚 Документация API: http://localhost:8000/docs"
echo ""
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
