"""
Fixtures for integration tests
"""

import asyncio
import os

import pytest
from redis.asyncio import Redis


@pytest.fixture(autouse=True)
async def clear_rate_limits():
    """Clear rate limits before each test to prevent interference"""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis = Redis.from_url(redis_url, decode_responses=True)

    try:
        # Clear all rate limit keys
        keys = await redis.keys("ratelimit:*")
        if keys:
            await redis.delete(*keys)
    finally:
        await redis.close()

    yield
