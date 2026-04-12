"""Role-Based Access Control (RBAC) System"""

from functools import wraps
from typing import List, Optional

from auth_v2 import decode_token, is_token_blacklisted
from fastapi import Header, HTTPException, Request
from redis.asyncio import Redis
from shared.logger import setup_logger

logger = setup_logger("rbac")


class Role:
    """Role definitions"""

    USER = "user"
    ADMIN = "admin"
    SYSTEM = "system"


class Permission:
    """Permission definitions"""

    READ_OWN_DATA = "read:own"
    WRITE_OWN_DATA = "write:own"
    READ_ALL_DATA = "read:all"
    WRITE_ALL_DATA = "write:all"
    MANAGE_USERS = "manage:users"
    SYSTEM_ADMIN = "system:admin"


ROLE_PERMISSIONS = {
    Role.USER: [Permission.READ_OWN_DATA, Permission.WRITE_OWN_DATA],
    Role.ADMIN: [
        Permission.READ_OWN_DATA,
        Permission.WRITE_OWN_DATA,
        Permission.READ_ALL_DATA,
        Permission.WRITE_ALL_DATA,
        Permission.MANAGE_USERS,
    ],
    Role.SYSTEM: [
        Permission.SYSTEM_ADMIN,
        Permission.READ_ALL_DATA,
        Permission.WRITE_ALL_DATA,
    ],
}


def has_permission(role: str, permission: str) -> bool:
    """Check if role has permission"""
    permissions = ROLE_PERMISSIONS.get(role, [])
    return permission in permissions


async def extract_and_validate_token(
    authorization: Optional[str], redis: Redis
) -> dict:
    """Extract and validate JWT token from Authorization header"""
    if not authorization:
        raise HTTPException(401, "Missing authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid authorization header format")

    token = authorization.replace("Bearer ", "")
    payload = decode_token(token)

    if not payload:
        raise HTTPException(401, "Invalid or expired token")

    if payload.get("type") != "access":
        raise HTTPException(401, "Invalid token type")

    # Check blacklist
    jti = payload.get("jti")
    if jti and await is_token_blacklisted(redis, jti):
        raise HTTPException(401, "Token has been revoked")

    return payload


def require_role(required_role: str):
    """Decorator to require specific role"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request and authorization from kwargs
            request: Optional[Request] = kwargs.get("request")
            authorization: Optional[str] = kwargs.get("authorization")

            if not request and not authorization:
                raise HTTPException(
                    500, "RBAC misconfiguration: missing request or authorization"
                )

            # Get Redis from request state if available
            redis = getattr(request.state, "redis", None) if request else None
            if not redis:
                raise HTTPException(500, "Redis not available")

            payload = await extract_and_validate_token(authorization, redis)

            user_role = payload.get("role", Role.USER)

            # Check role hierarchy
            if required_role == Role.ADMIN and user_role not in [
                Role.ADMIN,
                Role.SYSTEM,
            ]:
                logger.warning(
                    f"Access denied: user {payload.get('user_id')} with role {user_role} attempted admin action"
                )
                raise HTTPException(403, "Insufficient permissions")

            if required_role == Role.SYSTEM and user_role != Role.SYSTEM:
                logger.warning(
                    f"Access denied: user {payload.get('user_id')} with role {user_role} attempted system action"
                )
                raise HTTPException(403, "Insufficient permissions")

            # Add user info to kwargs
            kwargs["current_user"] = payload

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_permission(required_permission: str):
    """Decorator to require specific permission"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request: Optional[Request] = kwargs.get("request")
            authorization: Optional[str] = kwargs.get("authorization")

            if not request and not authorization:
                raise HTTPException(500, "RBAC misconfiguration")

            redis = getattr(request.state, "redis", None) if request else None
            if not redis:
                raise HTTPException(500, "Redis not available")

            payload = await extract_and_validate_token(authorization, redis)

            user_role = payload.get("role", Role.USER)

            if not has_permission(user_role, required_permission):
                logger.warning(
                    f"Permission denied: user {payload.get('user_id')} lacks {required_permission}"
                )
                raise HTTPException(
                    403, f"Missing required permission: {required_permission}"
                )

            kwargs["current_user"] = payload

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def verify_resource_ownership(user_id: int, resource_user_id: int, role: str) -> bool:
    """Verify user owns resource or has admin privileges"""
    if role in [Role.ADMIN, Role.SYSTEM]:
        return True
    return user_id == resource_user_id
