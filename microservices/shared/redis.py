"""Shared Redis client with proper error handling"""

import json
import os
import time

import redis.asyncio as redis
from shared.logger import setup_logger

logger = setup_logger("redis")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
pool = redis.ConnectionPool.from_url(
    REDIS_URL, max_connections=50, decode_responses=True
)
client = redis.Redis(connection_pool=pool)

# Import metrics if available
try:
    from metrics import redis_operation_duration_seconds, redis_operations_total

    _metrics_available = True
except ImportError:
    _metrics_available = False


async def get_cache(key: str):
    """Get value from cache with error logging"""
    start_time = time.time()
    try:
        value = await client.get(key)
        if _metrics_available:
            redis_operations_total.labels(operation="get", status="success").inc()
            redis_operation_duration_seconds.labels(operation="get").observe(
                time.time() - start_time
            )

        if value:
            logger.debug(f"Cache HIT: {key}")
            return json.loads(value)
        logger.debug(f"Cache MISS: {key}")
        return None
    except redis.RedisError as e:
        if _metrics_available:
            redis_operations_total.labels(operation="get", status="error").inc()
        logger.error(f"Redis GET error for key '{key}': {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error for key '{key}': {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in get_cache for key '{key}': {e}")
        return None


async def set_cache(key: str, value: dict, ttl: int = 60):
    """Set cache value with error logging"""
    start_time = time.time()
    try:
        await client.set(key, json.dumps(value), ex=ttl)
        if _metrics_available:
            redis_operations_total.labels(operation="set", status="success").inc()
            redis_operation_duration_seconds.labels(operation="set").observe(
                time.time() - start_time
            )
        logger.debug(f"Cache SET: {key} (ttl={ttl}s)")
    except redis.RedisError as e:
        if _metrics_available:
            redis_operations_total.labels(operation="set", status="error").inc()
        logger.error(f"Redis SET error for key '{key}': {e}")
    except TypeError as e:
        logger.error(f"JSON serialization error for key '{key}': {e}")
    except Exception as e:
        logger.error(f"Unexpected error in set_cache for key '{key}': {e}")


async def delete_cache(key: str):
    """Delete cache key with error logging"""
    try:
        result = await client.delete(key)
        logger.debug(f"Cache DELETE: {key} (existed={result > 0})")
    except redis.RedisError as e:
        logger.error(f"Redis DELETE error for key '{key}': {e}")
    except Exception as e:
        logger.error(f"Unexpected error in delete_cache for key '{key}': {e}")


async def publish_event(channel: str, data: dict):
    """Publish event to Redis channel with error logging"""
    try:
        subscribers = await client.publish(channel, json.dumps(data))
        logger.info(f"Event published to '{channel}': {subscribers} subscribers")
    except redis.RedisError as e:
        logger.error(f"Redis PUBLISH error for channel '{channel}': {e}")
    except TypeError as e:
        logger.error(f"JSON serialization error for channel '{channel}': {e}")
    except Exception as e:
        logger.error(f"Unexpected error in publish_event for channel '{channel}': {e}")


async def rate_limit(user_id: int, max_req: int = 100, window: int = 60) -> bool:
    """Rate limit check with error logging - fails open on error"""
    key = f"rate:{user_id}"
    try:
        count = await client.incr(key)
        if count == 1:
            await client.expire(key, window)

        if count > max_req:
            logger.warning(
                f"Rate limit exceeded for user {user_id}: {count}/{max_req} in {window}s"
            )
            return False

        return True
    except redis.RedisError as e:
        logger.error(f"Redis rate limit error for user {user_id}: {e} - failing open")
        return True  # Fail open - allow request if Redis is down
    except Exception as e:
        logger.error(
            f"Unexpected error in rate_limit for user {user_id}: {e} - failing open"
        )
        return True
