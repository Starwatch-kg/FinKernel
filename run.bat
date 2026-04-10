@echo off
echo 🚀 Запуск Financial AI Assistant
echo.

REM Проверка наличия Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден. Установите Python 3.11+
    exit /b 1
)

REM Создание виртуального окружения если его нет
if not exist "venv" (
    echo 📦 Создание виртуального окружения...
    python -m venv venv
)

REM Активация виртуального окружения
echo 🔧 Активация виртуального окружения...
call venv\Scripts\activate.bat

REM Установка зависимостей
echo 📥 Установка зависимостей...
pip install -r requirements.txt

REM Проверка .env файла
if not exist ".env" (
    echo ⚠️  Файл .env не найден. Создайте его из .env.example
    echo    copy .env.example .env
    echo    Затем добавьте ваш ANTHROPIC_API_KEY
    exit /b 1
)

REM Запуск API сервера
echo.
echo ✅ Запуск API сервера на http://localhost:8000
echo 📚 Документация API: http://localhost:8000/docs
echo.
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
