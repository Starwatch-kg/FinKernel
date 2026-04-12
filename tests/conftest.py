import asyncio
import os
import sys
from pathlib import Path

import httpx
import pytest
import pytest_asyncio

# Add microservices to Python path
microservices_path = Path(__file__).parent.parent / "microservices"
sys.path.insert(0, str(microservices_path))

# Set environment variables for tests
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://finuser:finpass123@localhost:5432/financedb"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault(
    "JWT_SECRET_KEY", "test-secret-key-for-ci-pipeline-must-be-at-least-64-chars-long"
)
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("BASE_URL", "http://localhost:8000")


# Base URL for API tests
@pytest.fixture
def base_url():
    return os.getenv("BASE_URL", "http://localhost:8000")


# HTTP client fixture
@pytest_asyncio.fixture
async def client(base_url):
    """Async HTTP client for API tests"""
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        yield client


# Authenticated client fixture
@pytest_asyncio.fixture
async def auth_client(client):
    """Async HTTP client with authentication"""
    from tests.helpers import register_and_get_token

    auth_data = await register_and_get_token(client)
    client.headers.update({"Authorization": f"Bearer {auth_data['token']}"})

    # Store auth data for tests that need it
    client.auth_data = auth_data

    yield client
