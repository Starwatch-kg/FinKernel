"""Network Security Middleware"""

import os

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from shared.logger import setup_logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

logger = setup_logger("network_security")


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect HTTP to HTTPS in production"""

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next):
        if self.enabled and request.url.scheme == "http":
            # Allow health checks on HTTP
            if request.url.path in ["/health", "/metrics"]:
                return await call_next(request)

            # Redirect to HTTPS
            url = request.url.replace(scheme="https")
            logger.info(f"Redirecting HTTP to HTTPS: {request.url} -> {url}")
            return RedirectResponse(url=str(url), status_code=301)

        return await call_next(request)


def get_trusted_hosts():
    """Get list of trusted hosts from environment"""
    hosts_str = os.getenv("TRUSTED_HOSTS", "localhost,127.0.0.1,*.localhost")
    return [host.strip() for host in hosts_str.split(",") if host.strip()]


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """Whitelist specific IPs for admin endpoints"""

    def __init__(self, app, admin_ips: list = None):
        super().__init__(app)
        self.admin_ips = admin_ips or []

    async def dispatch(self, request: Request, call_next):
        # Check if accessing admin endpoint
        if request.url.path.startswith("/admin/"):
            client_ip = self.get_client_ip(request)

            if self.admin_ips and client_ip not in self.admin_ips:
                logger.warning(f"Unauthorized admin access attempt from {client_ip}")
                raise HTTPException(403, "Access denied")

        return await call_next(request)

    @staticmethod
    def get_client_ip(request: Request) -> str:
        """Extract real client IP"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


class RateLimitByIPMiddleware(BaseHTTPMiddleware):
    """Global rate limiting by IP"""

    def __init__(self, app, redis_client, max_requests: int = 1000, window: int = 60):
        super().__init__(app)
        self.redis = redis_client
        self.max_requests = max_requests
        self.window = window

    async def dispatch(self, request: Request, call_next):
        client_ip = self.get_client_ip(request)
        key = f"ip_rate_limit:{client_ip}"

        try:
            count = await self.redis.incr(key)
            if count == 1:
                await self.redis.expire(key, self.window)

            if count > self.max_requests:
                logger.warning(
                    f"IP rate limit exceeded: {client_ip} ({count}/{self.max_requests})"
                )
                raise HTTPException(429, "Too many requests from your IP")

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open - allow request if Redis is down

        return await call_next(request)

    @staticmethod
    def get_client_ip(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
