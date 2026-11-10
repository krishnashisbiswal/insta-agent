"""
Security and Token Encryption at Rest (Hardened).

Guarantees:
- Fail-closed behavior: In production, missing TOKEN_ENCRYPTION_KEY raises RuntimeError.
- Zero hardcoded production secrets.
- Multi-key rotation support via MultiFernet.
- Explicit invalid ciphertext and corruption handling.
- Zero plaintext credential logging.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from typing import List, Optional, Tuple
from cryptography.fernet import Fernet, MultiFernet, InvalidToken

logger = logging.getLogger(__name__)


def is_production() -> bool:
    env = os.getenv("ENVIRONMENT", "").strip().lower()
    return env in ("production", "prod", "staging")


def get_encryption_keys() -> List[bytes]:
    """
    Retrieve encryption keys. Supports comma-separated keys for zero-downtime rotation.
    First key is primary (used for encryption), subsequent keys are fallback (for decryption).
    """
    raw_keys_str = os.getenv("TOKEN_ENCRYPTION_KEY", "").strip()

    if not raw_keys_str:
        if is_production():
            raise RuntimeError(
                "CRITICAL SECURITY FAILURE: TOKEN_ENCRYPTION_KEY environment variable is missing "
                "in production environment! System fails closed to protect tenant credentials."
            )
        # Development / local test fallback only (never used in production)
        logger.warning(
            "TOKEN_ENCRYPTION_KEY not set. Using ephemeral test key for local development. "
            "DO NOT USE IN PRODUCTION."
        )
        test_seed = "insta-agent-ephemeral-dev-test-seed-key"
        digest = hashlib.sha256(test_seed.encode("utf-8")).digest()
        return [base64.urlsafe_b64encode(digest)]

    # Parse comma-separated keys
    key_list: List[bytes] = []
    for k in raw_keys_str.split(","):
        k = k.strip()
        if not k:
            continue
        try:
            # Validate if it's already a valid 32-byte url-safe base64 key
            Fernet(k.encode("utf-8"))
            key_list.append(k.encode("utf-8"))
        except Exception:
            # If a passphrase was provided, derive 32-byte key
            digest = hashlib.sha256(k.encode("utf-8")).digest()
            key_list.append(base64.urlsafe_b64encode(digest))

    if not key_list:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY was provided but contains no valid keys.")

    return key_list


class TokenEncryptor:
    """
    Handles authenticated encryption and decryption of tenant tokens with rotation support.
    """

    def __init__(self, keys: Optional[List[bytes]] = None):
        self._keys = keys or get_encryption_keys()
        self._fernets = [Fernet(k) for k in self._keys]
        self._multi_fernet = MultiFernet(self._fernets)

    def encrypt(self, plaintext: str) -> str:
        """Encrypts string with primary key."""
        if not plaintext:
            return ""
        encrypted_bytes = self._multi_fernet.encrypt(plaintext.encode("utf-8"))
        return encrypted_bytes.decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        """Decrypts ciphertext using primary key or any valid rotation fallback key."""
        if not ciphertext:
            return ""
        try:
            decrypted_bytes = self._multi_fernet.decrypt(ciphertext.encode("utf-8"))
            return decrypted_bytes.decode("utf-8")
        except InvalidToken as exc:
            logger.error("Failed to decrypt token: Invalid or corrupted ciphertext.")
            raise ValueError("Corrupted or unauthorized token ciphertext") from exc

    def rotate(self, ciphertext: str) -> Tuple[str, bool]:
        """
        Re-encrypts ciphertext with current primary key if it was encrypted with an older key.
        Returns: (new_ciphertext, was_rotated)
        """
        if not ciphertext:
            return "", False
        try:
            new_bytes = self._multi_fernet.rotate(ciphertext.encode("utf-8"))
            new_str = new_bytes.decode("utf-8")
            return new_str, (new_str != ciphertext)
        except InvalidToken as exc:
            raise ValueError("Cannot rotate token: Invalid or corrupted ciphertext") from exc


_default_encryptor: Optional[TokenEncryptor] = None


def get_encryptor() -> TokenEncryptor:
    global _default_encryptor
    if _default_encryptor is None:
        _default_encryptor = TokenEncryptor()
    return _default_encryptor


def encrypt_token(token: str) -> str:
    return get_encryptor().encrypt(token)


def decrypt_token(cipher_token: str) -> str:
    return get_encryptor().decrypt(cipher_token)


def rotate_token(cipher_token: str) -> Tuple[str, bool]:
    return get_encryptor().rotate(cipher_token)


# Aliases
get_encryption_suite = get_encryptor
rotate_keys = rotate_token
reencrypt_token = lambda c: rotate_token(c)[0]

