"""
OAuth related utility functions
"""
import secrets
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from src.config import settings


class TokenEncryption:
    """Token encryption/decryption tool"""
    
    def __init__(self):
        # Generate encryption key from config
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=settings.SECRET_KEY.encode()[:16].ljust(16, b'0'),
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))
        self.cipher = Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """Encrypt string"""
        if not data:
            return ""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string"""
        if not encrypted_data:
            return ""
        try:
            return self.cipher.decrypt(encrypted_data.encode()).decode()
        except Exception:
            return ""


# Global encryption instance
token_encryption = TokenEncryption()


def generate_state() -> str:
    """Generate OAuth state parameter"""
    return secrets.token_urlsafe(32)


def generate_nonce() -> str:
    """Generate OAuth nonce parameter"""
    return secrets.token_urlsafe(16)


def is_token_expired(expires_at: Optional[datetime]) -> bool:
    """Check if token is expired"""
    if not expires_at:
        return True
    return datetime.now(timezone.utc) >= expires_at


def calculate_token_expiry(expires_in: int) -> datetime:
    """Calculate token expiration time"""
    return datetime.now(timezone.utc) + timedelta(seconds=expires_in)


def safe_get_nested_value(data: dict, keys: str, default=None):
    """Safely get nested dictionary value
    
    Args:
        data: Source dictionary
        keys: Key path, e.g. "user.profile.name" or "name"
        default: Default value
    
    Returns:
        Value found or default value
    """
    if not keys or not isinstance(data, dict):
        return default
        
    key_list = keys.split('.')
    current = data
    
    for key in key_list:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    
    return current