"""Production-grade authentication and authorization system"""

import os
import sys
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Optional

import bcrypt
import jwt
from fastapi import Header, HTTPException, Request

sys.path.append("/app")

from shared.config import get_config
from shared.logger import setup_logger

config = get_config()
logger = setup_logger("auth_secure")

# Token configuration
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # SHORT-LIVED
REFRESH_TOKEN_EXPIRE_DAYS = 7


class UserContext:
    """Authenticated user context"""

    def __init__(self, user_id: int, email: str, is_admin: bool = False):
        self.user_id = user_id
        self.email = email
        self.is_admin = is_admin

    def __repr__(self):
        return f"UserContext(user_id={self.user_id}, email={self.email}, is_admin={self.is_admin})"


def hash_password(password: str) -> str:
    """Hash password with bcrypt (cost factor 12)"""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash - constant time comparison"""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def create_access_token(user_id: int, email: str, is_admin: bool = False) -> str:
    """Create short-lived access token (15 minutes)"""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),
        "email": email,
        "is_admin": is_admin,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
    }

    token = jwt.encode(payload, config.jwt_secret_key, algorithm=config.jwt_algorithm)
    return token


def create_refresh_token(user_id: int, email: str) -> str:
    """Create long-lived refresh token (7 days)"""
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
    }

    token = jwt.encode(payload, config.jwt_secret_key, algorithm=config.jwt_algorithm)
    return token


def decode_token(token: str) -> Optional[Dict]:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(
            token,
            config.jwt_secret_key,
            algorithms=[config.jwt_algorithm],
            options={"verify_exp": True},
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"Token decode error: {e}")
        return None


async def get_current_user(
    request: Request, authorization: str = Header(None, alias="Authorization")
) -> UserContext:
    """
    CRITICAL: Extract authenticated user from JWT token.
    This is the ONLY way to get user identity.
    NEVER trust user_id from query params or path params.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    if not authorization:
        logger.warning(f"[{request_id}] Missing Authorization header")
        raise HTTPException(
            status_code=401,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not authorization.startswith("Bearer "):
        logger.warning(f"[{request_id}] Invalid Authorization header format")
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:]  # Remove "Bearer " prefix

    payload = decode_token(token)
    if not payload:
        logger.warning(f"[{request_id}] Invalid or expired token")
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify token type
    if payload.get("type") != "access":
        logger.warning(f"[{request_id}] Wrong token type: {payload.get('type')}")
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = int(payload.get("sub"))
    email = payload.get("email")
    is_admin = payload.get("is_admin", False)

    logger.info(
        f"[{request_id}] Authenticated user_id={user_id}, email={email}, admin={is_admin}"
    )

    return UserContext(user_id=user_id, email=email, is_admin=is_admin)


async def get_current_admin(
    request: Request, authorization: str = Header(None, alias="Authorization")
) -> UserContext:
    """
    Require admin privileges.
    Use this for admin-only endpoints.
    """
    user = await get_current_user(request, authorization)

    if not user.is_admin:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.warning(
            f"[{request_id}] Non-admin user {user.user_id} attempted admin action"
        )
        raise HTTPException(status_code=403, detail="Admin privileges required")

    return user


def verify_resource_ownership(user: UserContext, resource_user_id: int):
    """
    CRITICAL: Verify user owns the resource.
    Prevents horizontal privilege escalation (IDOR).
    """
    if user.user_id != resource_user_id and not user.is_admin:
        logger.warning(
            f"Authorization violation: user {user.user_id} attempted to access "
            f"resource owned by user {resource_user_id}"
        )
        raise HTTPException(
            status_code=403, detail="You do not have permission to access this resource"
        )


def is_admin_email(email: str) -> bool:
    """Check if email is in admin whitelist"""
    admin_emails = config.admin_emails
    if not admin_emails:
        return False
    return email.lower().strip() in [e.lower().strip() for e in admin_emails]
