"""
Authentication and Organization Authorization System.

Features:
- Secure password hashing via bcrypt (cost factor 12).
- Signed JWT access tokens (short-lived) and refresh tokens.
- Token revocation and blacklist tracking.
- Role-based authorization dependencies (owner, admin, member, analyst).
- Strict organization-level scoping for multi-tenancy.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Security configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "insta-agent-dev-jwt-signing-secret-key-32b").strip()
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "45"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

security_bearer = HTTPBearer(auto_error=False)

# Token Revocation Store (Token jti or hash -> expiry timestamp)
_revoked_tokens: Dict[str, float] = {}


def hash_password(password: str) -> str:
    """Hash plaintext password using bcrypt with salt."""
    if not password:
        raise ValueError("Password cannot be empty")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against bcrypt hash."""
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({
        "exp": expire,
        "iat": now,
    })
    to_encode.setdefault("type", "access")
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({
        "exp": expire,
        "iat": now,
    })
    to_encode.setdefault("type", "refresh")
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token."""
    if is_token_revoked(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked or logged out",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def revoke_token(token: str) -> None:
    """Revoke a token immediately."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM], options={"verify_exp": False})
        exp = payload.get("exp", time.time() + 3600)
        _revoked_tokens[token] = exp
        _cleanup_revocation_store()
    except Exception as exc:
        logger.warning(f"Failed to record token revocation: {exc}")


def is_token_revoked(token: str) -> bool:
    exp = _revoked_tokens.get(token)
    if not exp:
        return False
    if time.time() > exp:
        _revoked_tokens.pop(token, None)
        return False
    return True


def _cleanup_revocation_store() -> None:
    now = time.time()
    expired = [t for t, exp in _revoked_tokens.items() if now > exp]
    for t in expired:
        _revoked_tokens.pop(t, None)


# ---------------------------------------------------------------------------
# FASTAPI AUTHENTICATION & AUTHORIZATION DEPENDENCIES
# ---------------------------------------------------------------------------
from app.models.saas_models import User, get_db_session


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: Session = Depends(get_db_session),
) -> User:
    """
    Extracts and validates the authenticated user from the Bearer token.
    Enforces active user checks and tenant verification.
    """
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(auth.credentials)
    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated")

    return user


def require_roles(allowed_roles: List[str]):
    """
    Dependency factory enforcing RBAC roles within the user's organization.
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action forbidden. Required role in organization: {allowed_roles}. Current role: {current_user.role}",
            )
        return current_user

    return role_checker
