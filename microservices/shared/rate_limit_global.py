"""Global rate limiting with Redis backend"""

import os
import time
from typing import Optional, Tuple

from fastapi import HTTPException, Request
from redis.asyncio import Redis
from shared.fallback_limiter import fallback_limiter
from shared.logger import setup_logger

logger = setup_logger("rate_limiter")


class GlobalRateLimiter:
    """
    Production-grade rate limiter with sliding window algorithm.
    Fails open if Redis is unavailable (but logs the failure).
    """

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        identifier: Optional[str] = None,
    ) -> Tuple[bool, dict]:
        """
        Check if request is within rate limit.

        Returns:
            (allowed, info) where info contains:
                - remaining: requests remaining
                - reset_at: timestamp when limit resets
                - retry_after: seconds to wait if blocked
        """
        now = time.time()
        window_start = now - window_seconds

        # Build key with identifier
        full_key = f"ratelimit:{key}"
        if identifier:
            full_key = f"{full_key}:{identifier}"

        try:
            # Remove old entries outside window
            await self.redis.zremrangebyscore(full_key, 0, window_start)

            # Count requests in current window
            current_count = await self.redis.zcard(full_key)

            if current_count >= max_requests:
                # Get oldest request in window
                oldest = await self.redis.zrange(full_key, 0, 0, withscores=True)
                if oldest:
                    oldest_timestamp = oldest[0][1]
                    retry_after = int(oldest_timestamp + window_seconds - now)
                else:
                    retry_after = window_seconds

                logger.warning(
                    f"Rate limit exceeded for {full_key}: "
                    f"{current_count}/{max_requests} in {window_seconds}s"
                )

                return False, {
                    "remaining": 0,
                    "reset_at": int(now + retry_after),
                    "retry_after": retry_after,
                }

            # Add current request
            await self.redis.zadd(full_key, {str(now): now})

            # Set expiry on key
            await self.redis.expire(full_key, window_seconds + 10)

            remaining = max_requests - current_count - 1

            return True, {
                "remaining": remaining,
                "reset_at": int(now + window_seconds),
                "retry_after": 0,
            }

        except Exception as e:
            logger.error(f"Rate limiter error for {full_key}: {e} - USING FALLBACK")

            # FAIL CLOSED: Use in-memory fallback rate limiter
            # This prevents complete bypass but only protects single instance
            try:
                allowed, info = fallback_limiter.check_rate_limit(
                    key=full_key,
                    max_requests=max_requests,
                    window_seconds=window_seconds,
                )

                if not allowed:
                    logger.warning(
                        f"Fallback rate limiter blocked {full_key}: "
                        f"Redis unavailable, using in-memory limits"
                    )

                return allowed, info

            except Exception as fallback_error:
                logger.critical(
                    f"Both Redis and fallback rate limiter failed for {full_key}: {fallback_error} "
                    f"- FAILING OPEN as last resort"
                )
                # Only fail open if both Redis AND fallback fail
                return True, {
                    "remaining": max_requests,
                    "reset_at": int(now + window_seconds),
                    "retry_after": 0,
                }


# Rate limit configurations by endpoint type
RATE_LIMITS = {
    # Authentication endpoints - very strict
    "auth:login": {"max_requests": 20, "window": 300},  # 20 per 5 min
    "auth:register": {"max_requests": 20, "window": 300},  # 20 per 5 min
    "auth:refresh": {"max_requests": 10, "window": 60},  # 10 per min
    # AI endpoints - strict (expensive operations)
    "ai:predict": {"max_requests": 10, "window": 60},  # 10 per min
    "ai:generate": {"max_requests": 5, "window": 60},  # 5 per min
    # Financial operations - moderate
    "finance:trade": {"max_requests": 20, "window": 60},  # 20 per min
    "finance:transaction": {"max_requests": 50, "window": 60},  # 50 per min
    # Read operations - lenient
    "read:dashboard": {"max_requests": 100, "window": 60},  # 100 per min
    "read:list": {"max_requests": 200, "window": 60},  # 200 per min
    # Default fallback
    "default": {"max_requests": 100, "window": 60},
}


def get_rate_limit_config(endpoint_type: str) -> dict:
    """Get rate limit configuration for endpoint type"""
    return RATE_LIMITS.get(endpoint_type, RATE_LIMITS["default"])


async def apply_rate_limit(
    request: Request,
    rate_limiter: GlobalRateLimiter,
    endpoint_type: str,
    user_identifier: Optional[str] = None,
):
    """
    Apply rate limit to request.
    Raises HTTPException if limit exceeded.
    Skips rate limiting in test environment unless explicitly testing rate limits.
    """
    # Skip rate limiting in test environment, unless the test explicitly wants to test it
    # Tests can set X-Test-Rate-Limit header to enable rate limiting
    if os.getenv("ENVIRONMENT") == "test":
        test_rate_limit = request.headers.get("X-Test-Rate-Limit")
        if not test_rate_limit:
            return

    config = get_rate_limit_config(endpoint_type)
    request_id = getattr(request.state, "request_id", "unknown")

    allowed, info = await rate_limiter.check_rate_limit(
        key=endpoint_type,
        max_requests=config["max_requests"],
        window_seconds=config["window"],
        identifier=user_identifier,
    )

    # Add rate limit headers to response (will be added by middleware)
    request.state.rate_limit_info = info

    if not allowed:
        logger.warning(
            f"[{request_id}] Rate limit exceeded for {endpoint_type} "
            f"(user: {user_identifier}). Retry after {info['retry_after']}s"
        )
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Retry after {info['retry_after']} seconds",
            headers={
                "Retry-After": str(info["retry_after"]),
                "X-RateLimit-Limit": str(config["max_requests"]),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(info["reset_at"]),
            },
        )
