"""Security utilities - input sanitization, CSRF, etc."""

import html
import re
import secrets
from typing import Any, Dict


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Sanitize string input to prevent XSS"""
    if not isinstance(value, str):
        return ""

    # Truncate
    value = value[:max_length]

    # HTML escape
    value = html.escape(value)

    # Remove null bytes
    value = value.replace("\x00", "")

    return value.strip()


def sanitize_dict(data: Dict[str, Any], string_fields: list[str]) -> Dict[str, Any]:
    """Sanitize dictionary fields"""
    sanitized = data.copy()
    for field in string_fields:
        if field in sanitized and isinstance(sanitized[field], str):
            sanitized[field] = sanitize_string(sanitized[field])
    return sanitized


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def generate_csrf_token() -> str:
    """Generate CSRF token"""
    return secrets.token_urlsafe(32)


def validate_csrf_token(token: str, expected: str) -> bool:
    """Validate CSRF token with constant-time comparison"""
    return secrets.compare_digest(token, expected)


def is_safe_redirect_url(url: str, allowed_hosts: list[str]) -> bool:
    """Check if redirect URL is safe"""
    if not url:
        return False

    # Prevent open redirects
    if url.startswith("http://") or url.startswith("https://"):
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return parsed.netloc in allowed_hosts

    # Relative URLs are safe
    return url.startswith("/")


def strip_dangerous_chars(value: str) -> str:
    """Remove potentially dangerous characters"""
    # Remove control characters except newline and tab
    return "".join(char for char in value if ord(char) >= 32 or char in "\n\t")
