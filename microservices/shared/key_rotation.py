"""Key Rotation System with versioned keys"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import jwt
from redis.asyncio import Redis
from secrets_manager import secrets_manager
from shared.logger import setup_logger

logger = setup_logger("key_rotation")


class KeyVersion:
    """Versioned key with metadata"""

    def __init__(
        self,
        key_id: str,
        key_value: str,
        created_at: datetime,
        expires_at: Optional[datetime] = None,
    ):
        self.key_id = key_id
        self.key_value = key_value
        self.created_at = created_at
        self.expires_at = expires_at
        self.is_active = expires_at is None or datetime.utcnow() < expires_at

    def to_dict(self) -> dict:
        return {
            "key_id": self.key_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
        }


class KeyRotationManager:
    """Manage versioned keys with rotation"""

    def __init__(self, redis: Redis):
        self.redis = redis
        self.jwt_keys: Dict[str, KeyVersion] = {}
        self.encryption_keys: Dict[str, KeyVersion] = {}
        self.active_jwt_key_id: Optional[str] = None
        self.active_encryption_key_id: Optional[str] = None

    async def initialize(self):
        """Load keys from secrets manager"""
        # Load JWT key
        jwt_secret = await secrets_manager.get_secret("JWT_SECRET_KEY")
        if jwt_secret:
            key_id = "jwt_v1"
            self.jwt_keys[key_id] = KeyVersion(
                key_id=key_id, key_value=jwt_secret, created_at=datetime.utcnow()
            )
            self.active_jwt_key_id = key_id
            logger.info(f"Loaded JWT key: {key_id}")

        # Load encryption key
        encryption_key = await secrets_manager.get_secret("ENCRYPTION_KEY")
        if encryption_key:
            key_id = "enc_v1"
            self.encryption_keys[key_id] = KeyVersion(
                key_id=key_id, key_value=encryption_key, created_at=datetime.utcnow()
            )
            self.active_encryption_key_id = key_id
            logger.info(f"Loaded encryption key: {key_id}")

        # Load previous keys from Redis
        await self._load_previous_keys()

    async def _load_previous_keys(self):
        """Load previous key versions from Redis"""
        jwt_keys_data = await self.redis.get("key_rotation:jwt_keys")
        if jwt_keys_data:
            keys_dict = json.loads(jwt_keys_data)
            for key_id, key_data in keys_dict.items():
                if key_id not in self.jwt_keys:
                    self.jwt_keys[key_id] = KeyVersion(
                        key_id=key_id,
                        key_value=key_data["key_value"],
                        created_at=datetime.fromisoformat(key_data["created_at"]),
                        expires_at=(
                            datetime.fromisoformat(key_data["expires_at"])
                            if key_data.get("expires_at")
                            else None
                        ),
                    )

        enc_keys_data = await self.redis.get("key_rotation:encryption_keys")
        if enc_keys_data:
            keys_dict = json.loads(enc_keys_data)
            for key_id, key_data in keys_dict.items():
                if key_id not in self.encryption_keys:
                    self.encryption_keys[key_id] = KeyVersion(
                        key_id=key_id,
                        key_value=key_data["key_value"],
                        created_at=datetime.fromisoformat(key_data["created_at"]),
                        expires_at=(
                            datetime.fromisoformat(key_data["expires_at"])
                            if key_data.get("expires_at")
                            else None
                        ),
                    )

    async def _save_keys(self):
        """Persist keys to Redis"""
        jwt_keys_dict = {
            key_id: {
                "key_value": key.key_value,
                "created_at": key.created_at.isoformat(),
                "expires_at": key.expires_at.isoformat() if key.expires_at else None,
            }
            for key_id, key in self.jwt_keys.items()
        }
        await self.redis.set("key_rotation:jwt_keys", json.dumps(jwt_keys_dict))

        enc_keys_dict = {
            key_id: {
                "key_value": key.key_value,
                "created_at": key.created_at.isoformat(),
                "expires_at": key.expires_at.isoformat() if key.expires_at else None,
            }
            for key_id, key in self.encryption_keys.items()
        }
        await self.redis.set("key_rotation:encryption_keys", json.dumps(enc_keys_dict))

    async def rotate_jwt_key(self, new_key: str, grace_period_days: int = 7) -> str:
        """Rotate JWT signing key"""
        # Mark current key as expiring
        if self.active_jwt_key_id:
            current_key = self.jwt_keys[self.active_jwt_key_id]
            current_key.expires_at = datetime.utcnow() + timedelta(
                days=grace_period_days
            )
            logger.info(
                f"Marked JWT key {self.active_jwt_key_id} for expiration in {grace_period_days} days"
            )

        # Create new key version
        version_num = len(self.jwt_keys) + 1
        new_key_id = f"jwt_v{version_num}"
        self.jwt_keys[new_key_id] = KeyVersion(
            key_id=new_key_id, key_value=new_key, created_at=datetime.utcnow()
        )
        self.active_jwt_key_id = new_key_id

        await self._save_keys()
        logger.info(f"Rotated to new JWT key: {new_key_id}")

        return new_key_id

    async def rotate_encryption_key(
        self, new_key: str, grace_period_days: int = 30
    ) -> str:
        """Rotate encryption key"""
        if self.active_encryption_key_id:
            current_key = self.encryption_keys[self.active_encryption_key_id]
            current_key.expires_at = datetime.utcnow() + timedelta(
                days=grace_period_days
            )
            logger.info(
                f"Marked encryption key {self.active_encryption_key_id} for expiration in {grace_period_days} days"
            )

        version_num = len(self.encryption_keys) + 1
        new_key_id = f"enc_v{version_num}"
        self.encryption_keys[new_key_id] = KeyVersion(
            key_id=new_key_id, key_value=new_key, created_at=datetime.utcnow()
        )
        self.active_encryption_key_id = new_key_id

        await self._save_keys()
        logger.info(f"Rotated to new encryption key: {new_key_id}")

        return new_key_id

    def get_active_jwt_key(self) -> Optional[str]:
        """Get current active JWT key"""
        if self.active_jwt_key_id:
            return self.jwt_keys[self.active_jwt_key_id].key_value
        return None

    def get_jwt_key_by_id(self, key_id: str) -> Optional[str]:
        """Get JWT key by version ID"""
        if key_id in self.jwt_keys:
            return self.jwt_keys[key_id].key_value
        return None

    def get_all_valid_jwt_keys(self) -> List[str]:
        """Get all non-expired JWT keys for validation"""
        return [
            key.key_value
            for key in self.jwt_keys.values()
            if key.is_active or (key.expires_at and datetime.utcnow() < key.expires_at)
        ]

    def get_active_encryption_key(self) -> Optional[str]:
        """Get current active encryption key"""
        if self.active_encryption_key_id:
            return self.encryption_keys[self.active_encryption_key_id].key_value
        return None

    def get_encryption_key_by_id(self, key_id: str) -> Optional[str]:
        """Get encryption key by version ID"""
        if key_id in self.encryption_keys:
            return self.encryption_keys[key_id].key_value
        return None

    def decode_jwt_with_rotation(
        self, token: str, algorithms: List[str] = ["HS256"]
    ) -> Optional[dict]:
        """Decode JWT trying all valid keys"""
        valid_keys = self.get_all_valid_jwt_keys()

        for key in valid_keys:
            try:
                payload = jwt.decode(token, key, algorithms=algorithms)
                return payload
            except jwt.InvalidTokenError:
                continue

        logger.warning("JWT validation failed with all available keys")
        return None

    async def cleanup_expired_keys(self):
        """Remove expired keys"""
        now = datetime.utcnow()

        # Cleanup JWT keys
        expired_jwt = [
            key_id
            for key_id, key in self.jwt_keys.items()
            if key.expires_at and now > key.expires_at
        ]
        for key_id in expired_jwt:
            del self.jwt_keys[key_id]
            logger.info(f"Removed expired JWT key: {key_id}")

        # Cleanup encryption keys
        expired_enc = [
            key_id
            for key_id, key in self.encryption_keys.items()
            if key.expires_at and now > key.expires_at
        ]
        for key_id in expired_enc:
            del self.encryption_keys[key_id]
            logger.info(f"Removed expired encryption key: {key_id}")

        if expired_jwt or expired_enc:
            await self._save_keys()

    def get_key_status(self) -> dict:
        """Get status of all keys"""
        return {
            "jwt_keys": {
                "active": self.active_jwt_key_id,
                "total": len(self.jwt_keys),
                "versions": [key.to_dict() for key in self.jwt_keys.values()],
            },
            "encryption_keys": {
                "active": self.active_encryption_key_id,
                "total": len(self.encryption_keys),
                "versions": [key.to_dict() for key in self.encryption_keys.values()],
            },
        }
