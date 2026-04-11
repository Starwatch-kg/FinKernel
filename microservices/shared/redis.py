"""Shared Redis client"""
import redis.asyncio as redis
import json
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
pool = redis.ConnectionPool.from_url(REDIS_URL, max_connections=50, decode_responses=True)
client = redis.Redis(connection_pool=pool)


async def get_cache(key: str):
    try:
        value = await client.get(key)
        return json.loads(value) if value else None
    except:
        return None


async def set_cache(key: str, value: dict, ttl: int = 60):
    try:
        await client.set(key, json.dumps(value), ex=ttl)
    except:
        pass


async def delete_cache(key: str):
    try:
        await client.delete(key)
    except:
        pass


async def publish_event(channel: str, data: dict):
    try:
        await client.publish(channel, json.dumps(data))
    except:
        pass


async def rate_limit(user_id: int, max_req: int = 100, window: int = 60) -> bool:
    key = f"rate:{user_id}"
    try:
        count = await client.incr(key)
        if count == 1:
            await client.expire(key, window)
        return count <= max_req
    except:
        return True
