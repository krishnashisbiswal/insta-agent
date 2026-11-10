import pytest
import uuid
from fastapi.testclient import TestClient
from app.api.main import app
from app.security.encryption import encrypt_token, decrypt_token
from app.models.saas_models import init_db

client = TestClient(app)


def test_token_encryption():
    secret_token = "EAAB1234567890abcdef_secret_access_token"
    encrypted = encrypt_token(secret_token)
    assert encrypted != secret_token
    assert len(encrypted) > 20

    decrypted = decrypt_token(encrypted)
    assert decrypted == secret_token


def test_health_endpoint():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "gemini" in data
    assert "REEL" in data["supported_formats"]


def test_unauthenticated_requests_rejected():
    # Calling protected endpoints without token must return 401
    r1 = client.get("/api/accounts")
    assert r1.status_code == 401

    r2 = client.post("/api/accounts", json={"username": "test"})
    assert r2.status_code == 401

    r3 = client.post("/api/content/generate", json={"account_id": "acc_1", "topic": "AI"})
    assert r3.status_code == 401


def test_multi_account_creation_and_isolation():
    # 1. Register Org Alpha owner
    email_alpha = f"alpha_{uuid.uuid4().hex[:6]}@agency.com"
    r_reg_alpha = client.post("/api/auth/register", json={
        "email": email_alpha,
        "password": "Password123!",
        "org_name": "Agency Alpha",
    })
    assert r_reg_alpha.status_code == 201
    auth_alpha = r_reg_alpha.json()
    token_alpha = auth_alpha["access_token"]
    org_alpha = auth_alpha["org_id"]
    headers_alpha = {"Authorization": f"Bearer {token_alpha}"}

    # 2. Register Org Beta owner
    email_beta = f"beta_{uuid.uuid4().hex[:6]}@fitness.com"
    r_reg_beta = client.post("/api/auth/register", json={
        "email": email_beta,
        "password": "Password123!",
        "org_name": "Fitness Beta",
    })
    assert r_reg_beta.status_code == 201
    auth_beta = r_reg_beta.json()
    token_beta = auth_beta["access_token"]
    org_beta = auth_beta["org_id"]
    headers_beta = {"Authorization": f"Bearer {token_beta}"}

    # 3. Create Tech Account in org_alpha
    payload_tech = {
        "username": "tech_lead_daily",
        "instagram_user_id": "ig_1001",
        "access_token": "token_tech_123",
        "niche_id": "tech_ai",
        "brand_handle": "@techleaddaily",
        "auto_publish": False,
        "daily_post_limit": 3,
        "preferred_format": "REEL",
    }
    r1 = client.post("/api/accounts", json=payload_tech, headers=headers_alpha)
    assert r1.status_code == 201
    d1 = r1.json()
    acc_id_tech = d1["account_id"]
    assert acc_id_tech.startswith("acc_")
    assert d1["niche_id"] == "tech_ai"
    assert d1["has_token"] is True
    assert d1["org_id"] == org_alpha

    # 4. Create Fitness Account in org_beta
    payload_fit = {
        "username": "hypertrophy_hacks",
        "instagram_user_id": "ig_2002",
        "access_token": "token_fit_456",
        "niche_id": "fitness_wellness",
        "brand_handle": "@hypertrophyhacks",
        "auto_publish": False,
        "daily_post_limit": 1,
        "preferred_format": "CAROUSEL",
    }
    r2 = client.post("/api/accounts", json=payload_fit, headers=headers_beta)
    assert r2.status_code == 201
    d2 = r2.json()
    acc_id_fit = d2["account_id"]
    assert acc_id_fit != acc_id_tech
    assert d2["niche_id"] == "fitness_wellness"
    assert d2["org_id"] == org_beta

    # 5. Test Tenant Isolation in listing
    r_list_alpha = client.get("/api/accounts", headers=headers_alpha)
    assert r_list_alpha.status_code == 200
    alpha_accs = r_list_alpha.json()
    assert len(alpha_accs) == 1
    assert alpha_accs[0]["account_id"] == acc_id_tech
    assert all(a["org_id"] == org_alpha for a in alpha_accs)

    r_list_beta = client.get("/api/accounts", headers=headers_beta)
    assert r_list_beta.status_code == 200
    beta_accs = r_list_beta.json()
    assert len(beta_accs) == 1
    assert beta_accs[0]["account_id"] == acc_id_fit
    assert all(a["org_id"] == org_beta for a in beta_accs)

    # 6. Generate content for Tech Account (authorized)
    gen_payload = {
        "account_id": acc_id_tech,
        "topic": "Python 3.14 Features Explained",
    }
    r_gen = client.post("/api/content/generate", json=gen_payload, headers=headers_alpha)
    assert r_gen.status_code == 202
    gen_data = r_gen.json()
    assert "job_id" in gen_data
    assert gen_data["status"] == "QUEUED"
