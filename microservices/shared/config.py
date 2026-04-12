"""Production-safe configuration management"""

import os
import sys
from typing import Optional


class ConfigurationError(Exception):
    """Raised when required configuration is missing"""

    pass


class Config:
    """Centralized configuration with validation"""

    def __init__(self):
        self._validate_required_vars()

    # Database
    @property
    def database_url(self) -> str:
        return self._get_required("DATABASE_URL")

    # Redis
    @property
    def redis_url(self) -> str:
        return self._get_required("REDIS_URL")

    # JWT Authentication
    @property
    def jwt_secret_key(self) -> str:
        """JWT secret key - MUST be set in production"""
        secret = self._get_required("JWT_SECRET_KEY")
        if len(secret) < 32:
            raise ConfigurationError("JWT_SECRET_KEY must be at least 32 characters")
        return secret

    @property
    def jwt_algorithm(self) -> str:
        return os.getenv("JWT_ALGORITHM", "HS256")

    @property
    def jwt_expiry_minutes(self) -> int:
        return int(os.getenv("JWT_EXPIRY_MINUTES", "10080"))  # 7 days default

    # Groq API (Primary LLM)
    @property
    def groq_api_key(self) -> Optional[str]:
        """Groq API key - primary LLM provider"""
        return os.getenv("GROQ_API_KEY")

    @property
    def groq_base_url(self) -> str:
        return os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

    @property
    def groq_model(self) -> str:
        return os.getenv("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")

    # OpenRouter API (Fallback LLM)
    @property
    def openrouter_api_key(self) -> Optional[str]:
        """OpenRouter API key - fallback LLM provider"""
        return os.getenv("OPENROUTER_API_KEY")

    @property
    def openrouter_base_url(self) -> str:
        return os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    @property
    def openrouter_model(self) -> str:
        return os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")

    # Service URLs
    @property
    def transactions_url(self) -> str:
        return os.getenv("TRANSACTIONS_URL", "http://transactions:8001")

    @property
    def ai_url(self) -> str:
        return os.getenv("AI_URL", "http://ai:8002")

    # Admin Configuration
    @property
    def admin_emails(self) -> list[str]:
        """List of admin emails - comma separated"""
        emails = os.getenv("ADMIN_EMAILS", "")
        return [e.strip() for e in emails.split(",") if e.strip()]

    # Environment
    @property
    def environment(self) -> str:
        return os.getenv("ENVIRONMENT", "production")

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def debug(self) -> bool:
        return os.getenv("DEBUG", "false").lower() == "true"

    def _get_required(self, key: str) -> str:
        """Get required environment variable or fail fast"""
        value = os.getenv(key)
        if not value:
            raise ConfigurationError(
                f"Required environment variable '{key}' is not set. "
                f"Please set it in your environment or .env file."
            )
        return value

    def _validate_required_vars(self):
        """Validate all required configuration on startup"""
        required = []

        # Check database
        if not os.getenv("DATABASE_URL"):
            required.append("DATABASE_URL")

        # Check Redis
        if not os.getenv("REDIS_URL"):
            required.append("REDIS_URL")

        # Check JWT secret
        jwt_secret = os.getenv("JWT_SECRET_KEY")
        if not jwt_secret:
            required.append("JWT_SECRET_KEY")
        elif len(jwt_secret) < 32:
            raise ConfigurationError(
                "JWT_SECRET_KEY must be at least 32 characters for security. "
                "Generate one with: openssl rand -hex 32"
            )

        if required:
            raise ConfigurationError(
                f"Missing required environment variables: {', '.join(required)}\n"
                f"Please set them in your environment or create a .env file.\n"
                f"See .env.example for reference."
            )

    def log_config(self):
        """Log non-sensitive configuration for debugging"""
        print("=" * 60)
        print("Configuration loaded:")
        print(f"  Environment: {self.environment}")
        print(f"  Debug: {self.debug}")
        print(
            f"  Database: {self.database_url.split('@')[1] if '@' in self.database_url else 'configured'}"
        )
        print(
            f"  Redis: {self.redis_url.split('@')[1] if '@' in self.redis_url else 'configured'}"
        )
        print(f"  JWT Algorithm: {self.jwt_algorithm}")
        print(f"  JWT Expiry: {self.jwt_expiry_minutes} minutes")
        print(
            f"  Groq: {'configured' if self.groq_api_key else 'not configured'}"
        )
        print(
            f"  OpenRouter: {'configured' if self.openrouter_api_key else 'not configured'}"
        )
        print(f"  Admin emails: {len(self.admin_emails)} configured")
        print("=" * 60)


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create global config instance"""
    global _config
    if _config is None:
        try:
            _config = Config()
        except ConfigurationError as e:
            print(f"FATAL: Configuration error: {e}", file=sys.stderr)
            sys.exit(1)
    return _config


def init_config():
    """Initialize and validate configuration on startup"""
    config = get_config()
    if config.debug:
        config.log_config()
    return config
