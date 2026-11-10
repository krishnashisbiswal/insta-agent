import pytest
from fastapi.testclient import TestClient
from app.api.main import app
from app.security.encryption import encrypt_token, decrypt_token
from app.models.saas_models import init_db, Organization, User, InstagramAccount, get_db_session

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


def test_multi_account_creation_and_isolation():
    import uuid
    org_alpha = f"org_{uuid.uuid4().hex[:8]}"
    org_beta = f"org_{uuid.uuid4().hex[:8]}"

    # 1. Create Tech Account in org_alpha
    payload_tech = {
        "org_id": org_alpha,
        "username": "tech_lead_daily",
        "instagram_user_id": "ig_1001",
        "access_token": "token_tech_123",
        "niche_id": "tech_ai",
        "brand_handle": "@techleaddaily",
        "auto_publish": False,
        "daily_post_limit": 3,
        "preferred_format": "REEL",
    }
    r1 = client.post("/api/accounts", json=payload_tech)
    assert r1.status_code == 201
    d1 = r1.json()
    acc_id_tech = d1["account_id"]
    assert acc_id_tech.startswith("acc_")
    assert d1["niche_id"] == "tech_ai"
    assert d1["has_token"] is True

    # 2. Create Fitness Account for org_beta
    payload_fit = {
        "org_id": org_beta,
        "username": "hypertrophy_hacks",
        "instagram_user_id": "ig_2002",
        "access_token": "token_fit_456",
        "niche_id": "fitness_wellness",
        "brand_handle": "@hypertrophyhacks",
        "auto_publish": False,
        "daily_post_limit": 1,
        "preferred_format": "CAROUSEL",
    }
    r2 = client.post("/api/accounts", json=payload_fit)
    assert r2.status_code == 201
    d2 = r2.json()
    acc_id_fit = d2["account_id"]
    assert acc_id_fit != acc_id_tech
    assert d2["niche_id"] == "fitness_wellness"

    # 3. Test Org Isolation in listing
    r_list_alpha = client.get(f"/api/accounts?org_id={org_alpha}")
    assert r_list_alpha.status_code == 200
    alpha_accs = r_list_alpha.json()
    assert len(alpha_accs) == 1
    assert alpha_accs[0]["account_id"] == acc_id_tech
    assert all(a["org_id"] == org_alpha for a in alpha_accs)

    r_list_beta = client.get(f"/api/accounts?org_id={org_beta}")
    assert r_list_beta.status_code == 200
    beta_accs = r_list_beta.json()
    assert len(beta_accs) == 1
    assert beta_accs[0]["account_id"] == acc_id_fit
    assert all(a["org_id"] == org_beta for a in beta_accs)
    assert alpha_accs[0]["account_id"] == acc_id_tech

    # 4. Generate content for Tech Account
    gen_payload = {
        "account_id": acc_id_tech,
        "topic": "Python 3.14 Features Explained",
    }
    r_gen = client.post("/api/content/generate", json=gen_payload)
    assert r_gen.status_code == 202
    gen_data = r_gen.json()
    assert "job_id" in gen_data
    assert gen_data["status"] == "QUEUED"
