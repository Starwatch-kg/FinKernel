"""Enterprise-grade JWT V2 Authentication System with Refresh Tokens"""
import jwt
import bcrypt
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
import os
from redis.asyncio import Redis
from shared.logger import setup_logger

logger = setup_logger("auth_v2")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


class TokenVersion:
    """Token versioning for revocation"""
    CURRENT_VERSION = "v2"


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


def create_access_token(user_id: int, email: str, role: str = "user") -> str:
    """Create short-lived access token (15 min) with jti for replay protection"""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    jti = str(uuid.uuid4())

    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
        "jti": jti,
        "version": TokenVersion.CURRENT_VERSION
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: int, email: str) -> str:
    """Create long-lived refresh token (7 days)"""
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())

    payload = {
        "user_id": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
        "jti": jti,
        "version": TokenVersion.CURRENT_VERSION
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


async def store_refresh_token(redis: Redis, user_id: int, token: str, jti: str):
    """Store refresh token in Redis with TTL"""
    key = f"refresh_token:{user_id}:{jti}"
    ttl = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    await redis.setex(key, ttl, token)
    logger.debug(f"Stored refresh token for user {user_id}")


async def validate_refresh_token(redis: Redis, user_id: int, jti: str) -> bool:
    """Validate refresh token exists in Redis"""
    key = f"refresh_token:{user_id}:{jti}"
    exists = await redis.exists(key)
    return bool(exists)


async def revoke_refresh_token(redis: Redis, user_id: int, jti: str):
    """Revoke specific refresh token"""
    key = f"refresh_token:{user_id}:{jti}"
    await redis.delete(key)
    logger.info(f"Revoked refresh token {jti} for user {user_id}")


async def revoke_all_user_tokens(redis: Redis, user_id: int):
    """Revoke all refresh tokens for a user"""
    pattern = f"refresh_token:{user_id}:*"
    count = 0
    async for key in redis.scan_iter(match=pattern):
        await redis.delete(key)
        count += 1
    logger.info(f"Revoked {count} refresh tokens for user {user_id}")


async def blacklist_token(redis: Redis, jti: str, ttl: int):
    """Add token JTI to blacklist"""
    key = f"blacklist:{jti}"
    await redis.setex(key, ttl, "1")
    logger.debug(f"Blacklisted token {jti}")


async def is_token_blacklisted(redis: Redis, jti: str) -> bool:
    """Check if token JTI is blacklisted"""
    key = f"blacklist:{jti}"
    return bool(await redis.exists(key))


def determine_role(email: str) -> str:
    """Determine user role from email"""
    admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")
    if email.strip().lower() in [e.strip().lower() for e in admin_emails if e.strip()]:
        return "admin"
    return "user"


async def rotate_refresh_token(redis: Redis, old_token: str) -> Tuple[Optional[str], Optional[str]]:
    """Rotate refresh token - return new access and refresh tokens"""
    payload = decode_token(old_token)
    if not payload or payload.get("type") != "refresh":
        return None, None

    user_id = payload.get("user_id")
    email = payload.get("email")
    jti = payload.get("jti")

    if not user_id or not email or not jti:
        return None, None

    # Validate token exists in Redis
    if not await validate_refresh_token(redis, user_id, jti):
        logger.warning(f"Refresh token not found in Redis for user {user_id}")
        return None, None

    # Revoke old refresh token
    await revoke_refresh_token(redis, user_id, jti)

    # Create new tokens
    role = determine_role(email)
    new_access_token = create_access_token(user_id, email, role)
    new_refresh_token = create_refresh_token(user_id, email)

    # Store new refresh token
    new_payload = decode_token(new_refresh_token)
    new_jti = new_payload.get("jti")
    await store_refresh_token(redis, user_id, new_refresh_token, new_jti)

    logger.info(f"Rotated refresh token for user {user_id}")
    return new_access_token, new_refresh_token


def generate_internal_service_token() -> str:
    """Generate secure internal service token"""
    return secrets.token_urlsafe(32)


async def validate_internal_service_token(redis: Redis, token: str, service_name: str) -> bool:
    """Validate internal service-to-service token"""
    key = f"service_token:{service_name}"
    stored_token = await redis.get(key)
    return stored_token == token


async def store_internal_service_token(redis: Redis, service_name: str, token: str):
    """Store internal service token (no expiry)"""
    key = f"service_token:{service_name}"
    await redis.set(key, token)
    logger.info(f"Stored internal service token for {service_name}")
