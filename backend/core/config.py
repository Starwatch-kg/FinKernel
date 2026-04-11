"""
Конфигурация приложения через Pydantic Settings
"""
import os
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://finuser:finpass123@localhost:5432/financedb"

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:8080,http://localhost:5173,http://localhost:3000"

    # OpenRouter API
    OPENROUTER_API_KEY: str = ""

    # App
    APP_TITLE: str = "Financial AI Assistant"
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]


settings = Settings()
