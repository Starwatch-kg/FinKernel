"""Application-level encryption for sensitive data"""

import base64
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from shared.logger import setup_logger

logger = setup_logger("encryption")


class DataEncryption:
    """Encrypt sensitive financial data at application level"""

    def __init__(self):
        encryption_key = os.getenv("ENCRYPTION_KEY", "")

        if not encryption_key:
            logger.warning(
                "ENCRYPTION_KEY not set - generating temporary key (NOT FOR PRODUCTION)"
            )
            encryption_key = Fernet.generate_key().decode()

        # Derive key from password
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"fintech_salt_v1",  # In production, use unique salt per deployment
            iterations=100000,
            backend=default_backend(),
        )

        key = base64.urlsafe_b64encode(kdf.derive(encryption_key.encode()))
        self.cipher = Fernet(key)

    def encrypt_balance(self, balance: float) -> str:
        """Encrypt balance value"""
        try:
            plaintext = str(balance).encode()
            encrypted = self.cipher.encrypt(plaintext)
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise

    def decrypt_balance(self, encrypted_balance: str) -> float:
        """Decrypt balance value"""
        try:
            encrypted = encrypted_balance.encode()
            decrypted = self.cipher.decrypt(encrypted)
            return float(decrypted.decode())
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise

    def encrypt_field(self, value: str) -> str:
        """Encrypt generic string field"""
        try:
            encrypted = self.cipher.encrypt(value.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise

    def decrypt_field(self, encrypted_value: str) -> str:
        """Decrypt generic string field"""
        try:
            decrypted = self.cipher.decrypt(encrypted_value.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise


# Global encryption instance
data_encryption = DataEncryption()
