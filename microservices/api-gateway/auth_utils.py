"""JWT Authentication utilities"""
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
import sys
sys.path.append('/app')

from shared.config import get_config

config = get_config()


def hash_password(password: str) -> str:
    """Hash password with bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def create_access_token(user_id: int, email: str, is_admin: bool = False) -> str:
    """Create JWT access token"""
    expire = datetime.utcnow() + timedelta(minutes=config.jwt_expiry_minutes)

    payload = {
        "sub": str(user_id),
        "email": email,
        "is_admin": is_admin,
        "exp": expire,
        "iat": datetime.utcnow()
    }

    token = jwt.encode(payload, config.jwt_secret_key, algorithm=config.jwt_algorithm)
    return token


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(token, config.jwt_secret_key, algorithms=[config.jwt_algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_user_id_from_token(token: str) -> Optional[int]:
    """Extract user ID from token"""
    payload = decode_token(token)
    if payload:
        return int(payload.get("sub"))
    return None


def is_admin_email(email: str) -> bool:
    """Check if email is in admin list"""
    admin_emails = config.admin_emails
    if not admin_emails:
        # No admins configured - fail closed
        return False
    return email.lower() in [e.lower() for e in admin_emails]
