"""
Fallback in-memory rate limiter for when Redis is unavailable.
Prevents complete bypass of rate limiting on Redis failure.
"""

import time
from collections import defaultdict
from typing import Dict, Optional, Tuple

from shared.logger import setup_logger

logger = setup_logger("fallback_rate_limiter")


class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter using sliding window.
    Used as fallback when Redis is unavailable.
    NOT distributed - only protects single instance.
    """

    def __init__(self):
        # key -> list of (timestamp, request_count)
        self._windows: Dict[str, list] = defaultdict(list)
        self._last_cleanup = time.time()

    def check_rate_limit(
        self, key: str, max_requests: int, window_seconds: int
    ) -> Tuple[bool, dict]:
        """
        Check if request is within rate limit.
        Returns (allowed, info_dict)
        """
        now = time.time()
        window_start = now - window_seconds

        # Cleanup old entries periodically
        if now - self._last_cleanup > 60:
            self._cleanup_old_entries(now)
            self._last_cleanup = now

        # Get or create window for this key
        requests = self._windows[key]

        # Remove requests outside current window
        requests[:] = [ts for ts in requests if ts > window_start]

        # Check if limit exceeded
        current_count = len(requests)

        if current_count >= max_requests:
            # Calculate retry_after based on oldest request
            if requests:
                oldest = min(requests)
                retry_after = int(oldest + window_seconds - now)
            else:
                retry_after = window_seconds

            return False, {
                "remaining": 0,
                "reset_at": int(now + retry_after),
                "retry_after": max(1, retry_after),
            }

        # Add current request
        requests.append(now)

        remaining = max_requests - current_count - 1

        return True, {
            "remaining": remaining,
            "reset_at": int(now + window_seconds),
            "retry_after": 0,
        }

    def _cleanup_old_entries(self, now: float):
        """Remove entries older than 1 hour to prevent memory leak"""
        cutoff = now - 3600
        for key in list(self._windows.keys()):
            self._windows[key][:] = [ts for ts in self._windows[key] if ts > cutoff]
            if not self._windows[key]:
                del self._windows[key]


# Singleton instance
fallback_limiter = InMemoryRateLimiter()
