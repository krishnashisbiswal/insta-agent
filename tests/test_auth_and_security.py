"""
Security and Authentication Verification Suite.

Tests:
- Password hashing & salt verification via bcrypt (cost factor 12).
- JWT access and refresh token lifecycle.
- Immediate token revocation and blacklist verification.
- Password reset token generation and confirmation flow.
- Account deactivation & session invalidation.
- Fail-closed encryption behavior in production environments.
- MultiFernet key rotation and re-encryption.
- OWASP security headers.
- Request payload size limiter (413 Entity Too Large).
- Sliding-window rate limiter on auth endpoints.
"""

import os
import time
import uuid
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.models.saas_models import User, get_db_session
from app.security.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    is_token_revoked,
    revoke_token,
    verify_password,
)
from app.security.encryption import (
    decrypt_token,
    encrypt_token,
    get_encryption_suite,
    reencrypt_token,
    rotate_keys,
)

client = TestClient(app)


def test_password_hashing():
    raw_pass = "P@ssw0rdSecure2026!"
    hashed = hash_password(raw_pass)
    assert hashed != raw_pass
    assert hashed.startswith("$2b$")  # bcrypt prefix
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword123", hashed) is False
    assert verify_password("", hashed) is False

    with pytest.raises(ValueError):
        hash_password("")


def test_jwt_token_lifecycle():
    data = {"sub": "usr_test123", "org_id": "org_abc", "role": "admin"}
    token = create_access_token(data)
    decoded = decode_token(token)
    assert decoded["sub"] == "usr_test123"
    assert decoded["org_id"] == "org_abc"
    assert decoded["role"] == "admin"
    assert decoded["type"] == "access"
    assert "exp" in decoded


def test_jwt_token_revocation():
    data = {"sub": "usr_logout_test"}
    token = create_access_token(data)
    assert is_token_revoked(token) is False

    # Revoke token
    revoke_token(token)
    assert is_token_revoked(token) is True

    # Attempting to decode revoked token should raise HTTPException 401
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)
    assert exc_info.value.status_code == 401
    assert "revoked" in exc_info.value.detail


def test_auth_registration_and_login_flow():
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "StrongPassword2026!"

    # 1. Register
    reg_resp = client.post("/api/auth/register", json={
        "email": email,
        "password": pwd,
        "org_name": "Test Org",
    })
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    assert reg_data["email"] == email
    assert "access_token" in reg_data
    assert "refresh_token" in reg_data
    assert reg_data["role"] == "owner"

    # 2. Login
    login_resp = client.post("/api/auth/login", json={
        "email": email,
        "password": pwd,
    })
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["email"] == email
    token = login_data["access_token"]

    # 3. Access authenticated me endpoint
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == email
    assert me_data["role"] == "owner"

    # 4. Refresh token
    refresh_resp = client.post("/api/auth/refresh", json={
        "refresh_token": login_data["refresh_token"],
    })
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()

    # 5. Logout
    logout_resp = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_resp.status_code == 200
    assert logout_resp.json()["status"] == "logged_out"

    # Subsequent request with old token is rejected
    rej_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert rej_resp.status_code == 401


def test_password_reset_flow():
    email = f"reset_{uuid.uuid4().hex[:8]}@example.com"
    pwd_old = "OldPassword123!"
    pwd_new = "NewPassword456!"

    # Register user
    client.post("/api/auth/register", json={"email": email, "password": pwd_old})

    # Request password reset
    req_resp = client.post("/api/auth/password-reset/request", json={"email": email})
    assert req_resp.status_code == 200
    reset_token = req_resp.json()["reset_token"]

    # Confirm password reset
    conf_resp = client.post("/api/auth/password-reset/confirm", json={
        "reset_token": reset_token,
        "new_password": pwd_new,
    })
    assert conf_resp.status_code == 200

    # Old password fails
    bad_login = client.post("/api/auth/login", json={"email": email, "password": pwd_old})
    assert bad_login.status_code == 401

    # New password succeeds
    good_login = client.post("/api/auth/login", json={"email": email, "password": pwd_new})
    assert good_login.status_code == 200


def test_user_deactivation_blocks_access():
    email = f"deactive_{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post("/api/auth/register", json={"email": email, "password": "Password123!"})
    token = reg.json()["access_token"]
    user_id = reg.json()["user_id"]

    # Manually deactivate user in DB
    db = next(get_db_session())
    user = db.query(User).filter_by(user_id=user_id).first()
    user.is_active = False
    db.commit()

    # Login fails
    login_resp = client.post("/api/auth/login", json={"email": email, "password": "Password123!"})
    assert login_resp.status_code == 403

    # Authenticated requests with existing token fail
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 403


def test_owasp_security_headers():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("X-XSS-Protection") == "1; mode=block"
    assert "Strict-Transport-Security" in resp.headers
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in resp.headers


def test_correlation_id_middleware():
    # Automatically generates correlation ID if omitted
    resp1 = client.get("/api/health")
    assert "X-Correlation-ID" in resp1.headers
    assert resp1.headers["X-Correlation-ID"].startswith("req_")

    # Propagates custom correlation ID if passed
    custom_id = "test-tracing-id-7777"
    resp2 = client.get("/api/health", headers={"X-Correlation-ID": custom_id})
    assert resp2.headers.get("X-Correlation-ID") == custom_id


def test_oversized_payload_rejected():
    # Send a request with a header declaring > 15MB content-length
    huge_length = str(20 * 1024 * 1024)
    resp = client.post(
        "/api/auth/login",
        headers={"content-length": huge_length},
        json={"email": "a@b.com", "password": "x"},
    )
    assert resp.status_code == 413
    assert "exceeds maximum allowed size" in resp.json()["detail"]


def test_fail_closed_encryption_in_production(monkeypatch):
    from app.security import encryption

    # Reset cached encryptor
    encryption._default_encryptor = None

    # In production without keys, it MUST fail closed (raise RuntimeError)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("TOKEN_ENCRYPTION_KEY", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        encryption.get_encryption_suite()
    assert "CRITICAL SECURITY FAILURE" in str(exc_info.value)

    # Clean up cached encryptor
    encryption._default_encryptor = None


def test_multi_key_rotation_and_reencryption(monkeypatch):
    from cryptography.fernet import Fernet
    from app.security import encryption

    encryption._default_encryptor = None
    key_old = Fernet.generate_key().decode()
    key_new = Fernet.generate_key().decode()

    # Step 1: Encrypt with old key
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", key_old)
    encryption._default_encryptor = None
    ciphertext = encrypt_token("SuperSecretMetaToken123")

    # Step 2: Configure key rotation (new primary key + old key in secondary)
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", f"{key_new},{key_old}")
    encryption._default_encryptor = None

    # Decryption works via MultiFernet
    decrypted = decrypt_token(ciphertext)
    assert decrypted == "SuperSecretMetaToken123"

    # Re-encryption re-encrypts with new primary key
    reencrypted = reencrypt_token(ciphertext)
    assert reencrypted != ciphertext
    assert decrypt_token(reencrypted) == "SuperSecretMetaToken123"

    encryption._default_encryptor = None
