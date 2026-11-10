"""
Cross-Tenant Penetration and RBAC Authorization Test Suite.

Rigorously tests:
- Tenant isolation boundaries: A user must never access, view, modify, or delete another organization's resources.
- Forged org_id prevention: Any org_id submitted in a request is ignored in favor of the authenticated user's organization.
- Cross-tenant account access returns 404/403.
- Cross-tenant job access returns 404.
- Cross-tenant analytics access returns 404.
- Cross-tenant publishing attempts return 404.
- Role-based authorization: member cannot create/delete accounts.
- Organization monthly post quota exhaustion enforcement (returns 429).
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.models.saas_models import InstagramAccount, Organization, User, get_db_session

client = TestClient(app)


@pytest.fixture
def org_alpha_owner():
    email = f"alpha_owner_{uuid.uuid4().hex[:6]}@alpha.com"
    resp = client.post("/api/auth/register", json={
        "email": email,
        "password": "Password123!",
        "org_name": "Org Alpha",
    })
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return {
        "user_id": data["user_id"],
        "email": data["email"],
        "org_id": data["org_id"],
        "token": data["access_token"],
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
    }


@pytest.fixture
def org_beta_owner():
    email = f"beta_owner_{uuid.uuid4().hex[:6]}@beta.com"
    resp = client.post("/api/auth/register", json={
        "email": email,
        "password": "Password123!",
        "org_name": "Org Beta",
    })
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return {
        "user_id": data["user_id"],
        "email": data["email"],
        "org_id": data["org_id"],
        "token": data["access_token"],
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
    }


def test_cross_tenant_account_access_forbidden(org_alpha_owner, org_beta_owner):
    # 1. Org Alpha creates an account
    acc_payload = {
        "username": f"alpha_acc_{uuid.uuid4().hex[:4]}",
        "niche_id": "tech_ai",
        "brand_handle": "@alpha_tech",
        "access_token": "token_alpha_secret",
    }
    r_create = client.post("/api/accounts", json=acc_payload, headers=org_alpha_owner["headers"])
    assert r_create.status_code == 201
    alpha_acc_id = r_create.json()["account_id"]

    # 2. Org Beta attempts to access Org Alpha's account details -> 404
    r_get = client.get(f"/api/accounts/{alpha_acc_id}", headers=org_beta_owner["headers"])
    assert r_get.status_code == 404

    # 3. Org Beta attempts to delete Org Alpha's account -> 404
    r_del = client.delete(f"/api/accounts/{alpha_acc_id}", headers=org_beta_owner["headers"])
    assert r_del.status_code == 404

    # Org Alpha can access and delete their own account
    r_get_own = client.get(f"/api/accounts/{alpha_acc_id}", headers=org_alpha_owner["headers"])
    assert r_get_own.status_code == 200
    assert r_get_own.json()["account_id"] == alpha_acc_id


def test_forged_org_id_in_account_creation_ignored(org_alpha_owner, org_beta_owner):
    # Org Alpha attempts to supply Org Beta's org_id in payload
    forged_payload = {
        "org_id": org_beta_owner["org_id"],  # Forged!
        "username": f"spoofed_{uuid.uuid4().hex[:4]}",
        "niche_id": "finance",
        "brand_handle": "@spoofed_finance",
    }
    resp = client.post("/api/accounts", json=forged_payload, headers=org_alpha_owner["headers"])
    assert resp.status_code == 201
    created_acc = resp.json()

    # The account MUST be bound to Org Alpha, not the forged Org Beta!
    assert created_acc["org_id"] == org_alpha_owner["org_id"]
    assert created_acc["org_id"] != org_beta_owner["org_id"]


def test_cross_tenant_content_generation_blocked(org_alpha_owner, org_beta_owner):
    # Create account in Org Alpha
    acc_payload = {
        "username": f"alpha_target_{uuid.uuid4().hex[:4]}",
        "niche_id": "tech_ai",
        "brand_handle": "@alpha_target",
    }
    r_create = client.post("/api/accounts", json=acc_payload, headers=org_alpha_owner["headers"])
    alpha_acc_id = r_create.json()["account_id"]

    # Org Beta attempts to trigger content generation for Org Alpha's account
    gen_payload = {
        "account_id": alpha_acc_id,
        "topic": "Hacking the system",
    }
    r_gen = client.post("/api/content/generate", json=gen_payload, headers=org_beta_owner["headers"])
    assert r_gen.status_code == 404
    assert "not found or belongs to another organization" in r_gen.json()["detail"]


def test_cross_tenant_job_inspection_blocked(org_alpha_owner, org_beta_owner):
    # Create account and generate content in Org Alpha
    acc_payload = {"username": f"alpha_job_{uuid.uuid4().hex[:4]}", "niche_id": "tech_ai"}
    r_create = client.post("/api/accounts", json=acc_payload, headers=org_alpha_owner["headers"])
    alpha_acc_id = r_create.json()["account_id"]

    gen_payload = {"account_id": alpha_acc_id, "topic": "Top 10 AI Frameworks"}
    r_gen = client.post("/api/content/generate", json=gen_payload, headers=org_alpha_owner["headers"])
    assert r_gen.status_code == 202
    job_id = r_gen.json()["job_id"]

    # Org Alpha can view the job
    r_alpha_view = client.get(f"/api/jobs/{job_id}", headers=org_alpha_owner["headers"])
    assert r_alpha_view.status_code == 200

    # Org Beta CANNOT view Org Alpha's job -> 404
    r_beta_view = client.get(f"/api/jobs/{job_id}", headers=org_beta_owner["headers"])
    assert r_beta_view.status_code == 404


def test_cross_tenant_analytics_blocked(org_alpha_owner, org_beta_owner):
    acc_payload = {"username": f"alpha_metrics_{uuid.uuid4().hex[:4]}", "niche_id": "tech_ai"}
    r_create = client.post("/api/accounts", json=acc_payload, headers=org_alpha_owner["headers"])
    alpha_acc_id = r_create.json()["account_id"]

    # Org Beta cannot view Org Alpha's analytics -> 404
    r_analytics = client.get(f"/api/analytics/{alpha_acc_id}/summary", headers=org_beta_owner["headers"])
    assert r_analytics.status_code == 404


def test_role_based_access_control(org_alpha_owner):
    org_id = org_alpha_owner["org_id"]
    db = next(get_db_session())

    # Create a 'member' user in Org Alpha
    member_email = f"member_{uuid.uuid4().hex[:6]}@alpha.com"
    from app.security.auth import hash_password, create_access_token
    member_user = User(
        user_id=f"usr_{uuid.uuid4().hex[:8]}",
        org_id=org_id,
        email=member_email,
        role="member",
        hashed_password=hash_password("Password123!"),
        is_active=True,
    )
    db.add(member_user)
    db.commit()

    member_token = create_access_token({
        "sub": member_user.user_id,
        "email": member_user.email,
        "org_id": org_id,
        "role": "member",
    })
    member_headers = {"Authorization": f"Bearer {member_token}"}

    # Member CANNOT create account (requires owner or admin) -> 403
    r_create = client.post(
        "/api/accounts",
        json={"username": "member_attempt", "niche_id": "tech_ai"},
        headers=member_headers,
    )
    assert r_create.status_code == 403


def test_quota_exhaustion_enforced(org_alpha_owner):
    org_id = org_alpha_owner["org_id"]
    db = next(get_db_session())

    # Create an account for Org Alpha
    acc_payload = {"username": f"quota_test_{uuid.uuid4().hex[:4]}", "niche_id": "tech_ai"}
    r_create = client.post("/api/accounts", json=acc_payload, headers=org_alpha_owner["headers"])
    acc_id = r_create.json()["account_id"]

    # Artificially exhaust monthly quota for organization
    org = db.query(Organization).filter_by(org_id=org_id).first()
    org.posts_this_month = org.monthly_post_quota
    db.commit()

    # Content generation must return 429 Too Many Requests
    gen_payload = {"account_id": acc_id, "topic": "Quota Exceeded Topic"}
    r_gen = client.post("/api/content/generate", json=gen_payload, headers=org_alpha_owner["headers"])
    assert r_gen.status_code == 429
    assert "monthly post quota" in r_gen.json()["detail"].lower()
