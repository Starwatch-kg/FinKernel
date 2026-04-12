"""Centralized Secrets Management with Vault/AWS Secrets Manager abstraction"""

import json
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from shared.logger import setup_logger

logger = setup_logger("secrets_manager")


class SecretsBackend(ABC):
    """Abstract secrets backend"""

    @abstractmethod
    async def get_secret(self, key: str) -> Optional[str]:
        pass

    @abstractmethod
    async def get_secrets(self, keys: list[str]) -> Dict[str, str]:
        pass


class VaultBackend(SecretsBackend):
    """HashiCorp Vault backend (mock implementation)"""

    def __init__(self, vault_addr: str, vault_token: str):
        self.vault_addr = vault_addr
        self.vault_token = vault_token
        logger.info(f"Initialized Vault backend: {vault_addr}")

    async def get_secret(self, key: str) -> Optional[str]:
        # Mock implementation - in production, use hvac library
        logger.debug(f"Fetching secret from Vault: {key}")
        # Simulate Vault API call
        return os.getenv(key)

    async def get_secrets(self, keys: list[str]) -> Dict[str, str]:
        return {key: await self.get_secret(key) for key in keys}


class AWSSecretsBackend(SecretsBackend):
    """AWS Secrets Manager backend (mock implementation)"""

    def __init__(self, region: str):
        self.region = region
        logger.info(f"Initialized AWS Secrets Manager: {region}")

    async def get_secret(self, key: str) -> Optional[str]:
        # Mock implementation - in production, use boto3
        logger.debug(f"Fetching secret from AWS: {key}")
        return os.getenv(key)

    async def get_secrets(self, keys: list[str]) -> Dict[str, str]:
        return {key: await self.get_secret(key) for key in keys}


class EnvBackend(SecretsBackend):
    """Fallback environment variable backend"""

    async def get_secret(self, key: str) -> Optional[str]:
        return os.getenv(key)

    async def get_secrets(self, keys: list[str]) -> Dict[str, str]:
        return {key: os.getenv(key) for key in keys}


class SecretsCache:
    """TTL-based secrets cache"""

    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self.cache: Dict[str, tuple[str, datetime]] = {}

    def get(self, key: str) -> Optional[str]:
        if key in self.cache:
            value, expires_at = self.cache[key]
            if datetime.utcnow() < expires_at:
                return value
            else:
                del self.cache[key]
        return None

    def set(self, key: str, value: str):
        expires_at = datetime.utcnow() + timedelta(seconds=self.ttl)
        self.cache[key] = (value, expires_at)

    def invalidate(self, key: str):
        if key in self.cache:
            del self.cache[key]

    def clear(self):
        self.cache.clear()


class SecretsManager:
    """Centralized secrets manager with caching and auto-refresh"""

    def __init__(self, backend: SecretsBackend, cache_ttl: int = 300):
        self.backend = backend
        self.cache = SecretsCache(ttl=cache_ttl)
        self.refresh_interval = cache_ttl
        logger.info("Secrets manager initialized")

    async def get_secret(self, key: str, use_cache: bool = True) -> Optional[str]:
        """Get secret with caching"""
        if use_cache:
            cached = self.cache.get(key)
            if cached:
                logger.debug(f"Secret cache hit: {key}")
                return cached

        value = await self.backend.get_secret(key)
        if value:
            self.cache.set(key, value)
            logger.debug(f"Secret fetched and cached: {key}")
        else:
            logger.warning(f"Secret not found: {key}")

        return value

    async def get_secrets(self, keys: list[str]) -> Dict[str, str]:
        """Get multiple secrets"""
        result = {}
        missing_keys = []

        for key in keys:
            cached = self.cache.get(key)
            if cached:
                result[key] = cached
            else:
                missing_keys.append(key)

        if missing_keys:
            fetched = await self.backend.get_secrets(missing_keys)
            for key, value in fetched.items():
                if value:
                    self.cache.set(key, value)
                    result[key] = value

        return result

    async def refresh_secret(self, key: str):
        """Force refresh a secret"""
        self.cache.invalidate(key)
        return await self.get_secret(key, use_cache=False)

    async def refresh_all(self):
        """Refresh all cached secrets"""
        self.cache.clear()
        logger.info("All secrets cache cleared")


def create_secrets_manager() -> SecretsManager:
    """Factory to create secrets manager based on configuration"""
    backend_type = os.getenv("SECRETS_BACKEND", "env")

    if backend_type == "vault":
        vault_addr = os.getenv("VAULT_ADDR", "http://vault:8200")
        vault_token = os.getenv("VAULT_TOKEN", "")
        backend = VaultBackend(vault_addr, vault_token)
    elif backend_type == "aws":
        region = os.getenv("AWS_REGION", "us-east-1")
        backend = AWSSecretsBackend(region)
    else:
        logger.warning(
            "Using environment variable backend (not recommended for production)"
        )
        backend = EnvBackend()

    cache_ttl = int(os.getenv("SECRETS_CACHE_TTL", "300"))
    return SecretsManager(backend, cache_ttl=cache_ttl)


# Global secrets manager instance
secrets_manager = create_secrets_manager()
