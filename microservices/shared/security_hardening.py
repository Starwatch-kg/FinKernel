"""Security hardening utilities"""

import html
import re
import secrets
import uuid
from typing import Any, Dict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # HSTS - Force HTTPS
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # XSS Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to all requests for tracing"""

    async def dispatch(self, request: Request, call_next):
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """
    Sanitize string input to prevent XSS and injection attacks.
    Used for user-generated content that will be displayed or stored.
    """
    if not isinstance(value, str):
        return ""

    # Truncate to max length
    value = value[:max_length]

    # HTML escape to prevent XSS
    value = html.escape(value)

    # Remove null bytes
    value = value.replace("\x00", "")

    # Remove control characters except newline and tab
    value = "".join(char for char in value if ord(char) >= 32 or char in "\n\t")

    return value.strip()


def sanitize_for_llm(value: str, max_length: int = 500) -> str:
    """
    CRITICAL: Sanitize input before sending to LLM to prevent prompt injection.

    Removes patterns that could manipulate LLM behavior:
    - Instruction keywords
    - JSON injection attempts
    - System prompt manipulation
    """
    if not isinstance(value, str):
        return ""

    # Truncate
    value = value[:max_length]

    # Remove null bytes and control characters
    value = value.replace("\x00", "")
    value = "".join(char for char in value if ord(char) >= 32 or char in "\n\t")

    # Remove dangerous patterns that could inject instructions
    dangerous_patterns = [
        r"ignore\s+previous\s+instructions",
        r"ignore\s+all\s+previous",
        r"disregard\s+previous",
        r"forget\s+previous",
        r"new\s+instructions",
        r"system\s*:",
        r"assistant\s*:",
        r"user\s*:",
        r"<\|.*?\|>",  # Special tokens
        r"\[INST\]",
        r"\[/INST\]",
    ]

    for pattern in dangerous_patterns:
        value = re.sub(pattern, "", value, flags=re.IGNORECASE)

    # Escape JSON special characters to prevent JSON injection
    value = value.replace('"', '\\"').replace("\n", " ").replace("\r", "")

    return value.strip()


def validate_amount(
    amount: float, min_val: float = 0.01, max_val: float = 1_000_000_000
) -> float:
    """
    Validate financial amounts to prevent:
    - Negative amounts
    - Zero amounts
    - Unreasonably large amounts
    - NaN/Infinity
    """
    if not isinstance(amount, (int, float)):
        raise ValueError("Amount must be a number")

    if amount != amount:  # NaN check
        raise ValueError("Amount cannot be NaN")

    if amount == float("inf") or amount == float("-inf"):
        raise ValueError("Amount cannot be infinite")

    if amount < min_val:
        raise ValueError(f"Amount must be at least {min_val}")

    if amount > max_val:
        raise ValueError(f"Amount cannot exceed {max_val}")

    # Round to 2 decimal places for currency
    return round(amount, 2)


def validate_shares(shares: int, min_val: int = 1, max_val: int = 1_000_000) -> int:
    """Validate share counts for trading"""
    if not isinstance(shares, int):
        raise ValueError("Shares must be an integer")

    if shares < min_val:
        raise ValueError(f"Shares must be at least {min_val}")

    if shares > max_val:
        raise ValueError(f"Shares cannot exceed {max_val}")

    return shares


def generate_csrf_token() -> str:
    """Generate CSRF token"""
    return secrets.token_urlsafe(32)


def validate_csrf_token(token: str, expected: str) -> bool:
    """Validate CSRF token with constant-time comparison"""
    if not token or not expected:
        return False
    return secrets.compare_digest(token, expected)


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded"""

    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds")
