"""Advanced rate limiting with sliding window"""
import time
from typing import Optional
from redis.asyncio import Redis
from shared.logger import setup_logger

logger = setup_logger("rate_limiter")


class SlidingWindowRateLimiter:
    """Sliding window rate limiter using Redis sorted sets"""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        identifier: Optional[str] = None
    ) -> tuple[bool, dict]:
        """
        Check if request is within rate limit

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

                # Record metric
                try:
                    from metrics import rate_limit_exceeded_total
                    rate_limit_exceeded_total.labels(
                        endpoint=key,
                        user_type="authenticated" if identifier else "anonymous"
                    ).inc()
                except ImportError:
                    pass

                return False, {
                    "remaining": 0,
                    "reset_at": int(now + retry_after),
                    "retry_after": retry_after
                }

            # Add current request
            await self.redis.zadd(full_key, {str(now): now})

            # Set expiry on key
            await self.redis.expire(full_key, window_seconds + 10)

            remaining = max_requests - current_count - 1

            return True, {
                "remaining": remaining,
                "reset_at": int(now + window_seconds),
                "retry_after": 0
            }

        except Exception as e:
            logger.error(f"Rate limiter error for {full_key}: {e} - failing open")
            # Fail open on Redis errors
            return True, {
                "remaining": max_requests,
                "reset_at": int(now + window_seconds),
                "retry_after": 0
            }


# Rate limit configurations
RATE_LIMITS = {
    "auth:login": {"max_requests": 5, "window": 300},  # 5 per 5 min
    "auth:register": {"max_requests": 3, "window": 300},  # 3 per 5 min
    "auth:refresh": {"max_requests": 10, "window": 60},  # 10 per min
    "api:default": {"max_requests": 100, "window": 60},  # 100 per min
    "api:ai": {"max_requests": 10, "window": 60},  # 10 per min
    "api:transaction": {"max_requests": 50, "window": 60},  # 50 per min
}


def get_rate_limit_config(endpoint: str) -> dict:
    """Get rate limit configuration for endpoint"""
    return RATE_LIMITS.get(endpoint, RATE_LIMITS["api:default"])
