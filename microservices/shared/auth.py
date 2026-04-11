"""Enhanced JWT authentication with refresh tokens"""
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict
import os
from redis.asyncio import Redis
from logger import setup_logger

logger = setup_logger("auth")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


def hash_password(password: str) -> str:
    """Hash password with bcrypt"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    try:
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def create_access_token(user_id: int, email: str, is_admin: bool = False) -> str:
    """Create short-lived access token (15 min)"""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "user_id": user_id,
        "email": email,
        "is_admin": is_admin,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: int, email: str) -> str:
    """Create long-lived refresh token (7 days)"""
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[Dict]:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None


async def store_refresh_token(redis: Redis, user_id: int, token: str):
    """Store refresh token in Redis with TTL"""
    key = f"refresh_token:{user_id}:{token[-12:]}"
    ttl = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    await redis.setex(key, ttl, token)
    logger.debug(f"Stored refresh token for user {user_id}")


async def validate_refresh_token(redis: Redis, user_id: int, token: str) -> bool:
    """Validate refresh token exists in Redis"""
    key = f"refresh_token:{user_id}:{token[-12:]}"
    exists = await redis.exists(key)
    return bool(exists)


async def revoke_refresh_token(redis: Redis, user_id: int, token: str):
    """Revoke refresh token"""
    key = f"refresh_token:{user_id}:{token[-12:]}"
    await redis.delete(key)
    logger.info(f"Revoked refresh token for user {user_id}")


async def revoke_all_user_tokens(redis: Redis, user_id: int):
    """Revoke all refresh tokens for a user"""
    pattern = f"refresh_token:{user_id}:*"
    cursor = 0
    count = 0
    async for key in redis.scan_iter(match=pattern):
        await redis.delete(key)
        count += 1
    logger.info(f"Revoked {count} refresh tokens for user {user_id}")


async def blacklist_token(redis: Redis, token: str, ttl: int):
    """Add token to blacklist"""
    key = f"blacklist:{token[-12:]}"
    await redis.setex(key, ttl, "1")
    logger.debug(f"Blacklisted token")


async def is_token_blacklisted(redis: Redis, token: str) -> bool:
    """Check if token is blacklisted"""
    key = f"blacklist:{token[-12:]}"
    return bool(await redis.exists(key))


def is_admin_email(email: str) -> bool:
    """Check if email is in admin list"""
    admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")
    return email.strip().lower() in [e.strip().lower() for e in admin_emails if e.strip()]
