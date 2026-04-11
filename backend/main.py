"""
Главный файл приложения FastAPI
Модульный монолит с чистой архитектурой
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from backend.core import settings, init_db
from backend.api import (
    auth_router,
    transactions_router,
    learning_router,
    stocks_router,
    gamification_router,
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация приложения
app = FastAPI(title=settings.APP_TITLE)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(auth_router)
app.include_router(transactions_router)
app.include_router(learning_router)
app.include_router(stocks_router)
app.include_router(gamification_router)


@app.on_event("startup")
async def startup():
    """Инициализация при запуске"""
    logger.info("Starting Financial AI Assistant API...")
    await init_db()
    logger.info("Database initialized successfully")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Financial AI Assistant API",
        "status": "running",
        "version": "2.0.0-modular"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
