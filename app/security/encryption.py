"""
Security and Token Encryption at Rest.

Encrypts OAuth tokens, session cookies, and API secrets using AES-128-CBC / HMAC (Fernet).
Guarantees credentials are never stored in plaintext within database tables.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from typing import Optional
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


def get_encryption_key() -> bytes:
    """
    Retrieve or derive the encryption key for token encryption at rest.
    """
    raw_key = os.getenv("TOKEN_ENCRYPTION_KEY", "").strip()
    if raw_key:
        try:
            # Validate Fernet key format (32 url-safe base64-encoded bytes)
            Fernet(raw_key.encode("utf-8"))
            return raw_key.encode("utf-8")
        except Exception:
            # Hash into valid 32-byte Fernet key
            digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
            return base64.urlsafe_b64encode(digest)

    # Derive deterministic key from project secret or fallback
    secret_seed = os.getenv("SECRET_KEY", "insta-agent-production-secret-seed-key-32b")
    digest = hashlib.sha256(secret_seed.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


class TokenEncryptor:
    """
    Handles encryption and decryption of sensitive tokens.
    """

    def __init__(self, key: Optional[bytes] = None):
        self._key = key or get_encryption_key()
        self._cipher = Fernet(self._key)

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        encrypted_bytes = self._cipher.encrypt(plaintext.encode("utf-8"))
        return encrypted_bytes.decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        decrypted_bytes = self._cipher.decrypt(ciphertext.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")


_default_encryptor: Optional[TokenEncryptor] = None


def encrypt_token(token: str) -> str:
    global _default_encryptor
    if _default_encryptor is None:
        _default_encryptor = TokenEncryptor()
    return _default_encryptor.encrypt(token)


def decrypt_token(cipher_token: str) -> str:
    global _default_encryptor
    if _default_encryptor is None:
        _default_encryptor = TokenEncryptor()
    return _default_encryptor.decrypt(cipher_token)
