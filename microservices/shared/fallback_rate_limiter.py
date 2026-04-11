"""In-memory fallback rate limiter when Redis is unavailable"""
import time
from collections import defaultdict
from typing import Dict, Tuple
from logger import setup_logger

logger = setup_logger("fallback_rate_limiter")


class InMemoryRateLimiter:
    """In-memory rate limiter as Redis fallback"""

    def __init__(self):
        self.requests: Dict[str, list[float]] = defaultdict(list)
        self.last_cleanup = time.time()
        self.cleanup_interval = 60

    def check_rate_limit(self, key: str, max_requests: int = 100, window: int = 60) -> bool:
        """Check if request is within rate limit"""
        now = time.time()

        # Periodic cleanup
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup()

        # Get request timestamps for this key
        timestamps = self.requests[key]

        # Remove old timestamps
        cutoff = now - window
        timestamps[:] = [ts for ts in timestamps if ts > cutoff]

        # Check limit
        if len(timestamps) >= max_requests:
            logger.warning(f"Rate limit exceeded for {key}: {len(timestamps)}/{max_requests}")
            return False

        # Add current request
        timestamps.append(now)
        return True

    def _cleanup(self):
        """Remove old entries"""
        now = time.time()
        cutoff = now - 300  # 5 minutes

        keys_to_delete = []
        for key, timestamps in self.requests.items():
            timestamps[:] = [ts for ts in timestamps if ts > cutoff]
            if not timestamps:
                keys_to_delete.append(key)

        for key in keys_to_delete:
            del self.requests[key]

        self.last_cleanup = now
        logger.debug(f"Cleaned up {len(keys_to_delete)} expired rate limit entries")

    def reset(self, key: str):
        """Reset rate limit for key"""
        if key in self.requests:
            del self.requests[key]

    def get_stats(self) -> dict:
        """Get rate limiter statistics"""
        return {
            "total_keys": len(self.requests),
            "total_requests": sum(len(ts) for ts in self.requests.values())
        }


# Global fallback rate limiter
fallback_rate_limiter = InMemoryRateLimiter()
