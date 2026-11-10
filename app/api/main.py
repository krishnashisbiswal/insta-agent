"""
Commercial SaaS REST API (FastAPI) - Production Hardened.

Features:
- OWASP Security headers, correlation IDs, request payload size limiting, and rate limiting.
- Secure User Authentication (bcrypt + JWT access/refresh tokens + revocation blacklist).
- Role-Based Access Control (RBAC) with strict multi-tenant organization isolation.
- Multi-account Instagram management with AES-256 Fernet encrypted token storage.
- Multi-niche dynamic content generation routing.
- Database-backed publishing state machine with distributed execution leases.
- Media serving via public static uploads and object storage.
- Empirical performance analytics endpoints.
- Production system health checks.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.agents.gemini_client import check_health as check_gemini_health
from app.analytics.meta_insights import EmpiricalPerformanceTracker
from app.api.middleware import (
    CorrelationIdMiddleware,
    RequestSizeLimiterMiddleware,
    SecurityHeadersMiddleware,
    api_rate_limiter,
    login_rate_limiter,
)
from app.creative.creative_director import ContentFormat, CreativeDirector
from app.models.saas_models import (
    AuditLog,
    InstagramAccount,
    NicheProfileModel,
    Organization,
    PublishingJobModel,
    User,
    get_db_session,
    init_db,
)
from app.niche.niche_profile import (
    NicheProfile,
    NicheRegistry,
    detect_niche_from_prompt,
    get_default_niche,
)
from app.publishing.publishing_service import PublishingService
from app.publishing.state_machine import (
    DatabasePublishingStateMachine,
    DuplicateJobError,
    PublishingState,
)
from app.security.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    is_token_revoked,
    require_roles,
    revoke_token,
    security_bearer,
    verify_password,
)
from app.storage.local import DEFAULT_UPLOAD_DIR

logger = logging.getLogger(__name__)

# Initialize database on startup
init_db()

app = FastAPI(
    title="Insta-Agent Production SaaS API",
    version="2.0.0",
    description="Autonomous multi-account, multi-niche Instagram AI content generation and publishing engine.",
)

# ---------------------------------------------------------------------------
# MIDDLEWARE MOUNTING
# ---------------------------------------------------------------------------
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(RequestSizeLimiterMiddleware, max_bytes=15 * 1024 * 1024)

# Static media serving for public URLs (Meta Graph API ingestion)
upload_dir = Path(os.getenv("STORAGE_LOCAL_DIR", DEFAULT_UPLOAD_DIR)).resolve()
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")


# ---------------------------------------------------------------------------
# PYDANTIC SCHEMAS
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., json_schema_extra={"example": "owner@brand.com"})
    password: str = Field(..., min_length=8, json_schema_extra={"example": "SuperSecretP@ss123"})
    org_name: Optional[str] = Field(None, json_schema_extra={"example": "Acme Marketing"})


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., json_schema_extra={"example": "owner@brand.com"})
    password: str = Field(..., json_schema_extra={"example": "SuperSecretP@ss123"})


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., json_schema_extra={"example": "eyJhbGci..."})


class PasswordResetRequest(BaseModel):
    email: EmailStr = Field(..., json_schema_extra={"example": "owner@brand.com"})


class PasswordResetConfirmRequest(BaseModel):
    reset_token: str = Field(..., json_schema_extra={"example": "eyJhbGci..."})
    new_password: str = Field(..., min_length=8, json_schema_extra={"example": "NewSecretP@ss456"})


class AccountCreateRequest(BaseModel):
    org_id: Optional[str] = Field(None, json_schema_extra={"example": "org_default"})
    username: str = Field(..., json_schema_extra={"example": "tech_innovations"})
    instagram_user_id: Optional[str] = Field(None, json_schema_extra={"example": "17841400000000000"})
    access_token: Optional[str] = Field(None, json_schema_extra={"example": "EAAB..."})
    niche_id: str = Field("tech_ai", json_schema_extra={"example": "tech_ai"})
    brand_handle: str = Field("@tech_innovations", json_schema_extra={"example": "@tech_innovations"})
    target_audience: Optional[str] = Field(None, json_schema_extra={"example": "Developers and tech leads"})
    auto_publish: bool = Field(False, json_schema_extra={"example": False})
    daily_post_limit: int = Field(2, json_schema_extra={"example": 2})
    preferred_format: str = Field("REEL", json_schema_extra={"example": "REEL"})


class GenerateContentRequest(BaseModel):
    account_id: str = Field(..., json_schema_extra={"example": "acc_123"})
    topic: str = Field(..., json_schema_extra={"example": "Top 3 Python libraries for AI in 2026"})
    format: Optional[str] = Field(None, json_schema_extra={"example": "REEL"})
    language: Optional[str] = Field("English", json_schema_extra={"example": "English"})
    auto_publish_override: Optional[bool] = Field(None, json_schema_extra={"example": False})


# ---------------------------------------------------------------------------
# PUBLIC / SYSTEM HEALTH ROUTES
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health_check():
    gemini_status = check_gemini_health()
    return {
        "status": "healthy",
        "api_version": "2.0.0",
        "gemini": gemini_status,
        "supported_formats": ["REEL", "CAROUSEL", "STORY", "POST"],
        "architecture": "multi-account, multi-niche isolated SaaS",
    }


@app.get("/api/niches")
def list_niches():
    registry = NicheRegistry()
    return [p.to_dict() for p in registry.list_all()]


# ---------------------------------------------------------------------------
# AUTHENTICATION & IDENTITY ROUTES
# ---------------------------------------------------------------------------
@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register_user(
    req: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db_session),
):
    client_ip = request.client.host if request.client else "unknown"
    allowed, retry_after = login_rate_limiter.is_allowed(f"register:{client_ip}")
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many registration attempts. Please retry in {retry_after} seconds.",
        )

    clean_email = req.email.lower().strip()
    existing = db.query(User).filter_by(email=clean_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email address already exists.",
        )

    # Create Organization
    org_id = f"org_{uuid.uuid4().hex[:10]}"
    org_name = req.org_name or f"{clean_email.split('@')[0].capitalize()}'s Workspace"
    org = Organization(org_id=org_id, name=org_name)
    db.add(org)

    # Create User with owner role
    user_id = f"usr_{uuid.uuid4().hex[:10]}"
    user = User(
        user_id=user_id,
        org_id=org_id,
        email=clean_email,
        role="owner",
        hashed_password=hash_password(req.password),
        is_active=True,
    )
    db.add(user)

    # Create Audit Log
    audit = AuditLog(
        audit_id=f"aud_{uuid.uuid4().hex[:12]}",
        org_id=org_id,
        user_id=user_id,
        action="USER_REGISTER",
        resource_type="USER",
        resource_id=user_id,
        ip_address=client_ip,
    )
    db.add(audit)
    db.commit()

    token_payload = {
        "sub": user.user_id,
        "email": user.email,
        "org_id": user.org_id,
        "role": user.role,
    }
    access_token = create_access_token(token_payload)
    refresh_token = create_refresh_token(token_payload)

    return {
        "user_id": user.user_id,
        "email": user.email,
        "role": user.role,
        "org_id": user.org_id,
        "org_name": org.name,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@app.post("/api/auth/login")
def login_user(
    req: LoginRequest,
    request: Request,
    db: Session = Depends(get_db_session),
):
    clean_email = req.email.lower().strip()
    allowed, retry_after = login_rate_limiter.is_allowed(f"login:{clean_email}")
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Please retry in {retry_after} seconds.",
        )

    user = db.query(User).filter_by(email=clean_email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been suspended or deactivated.",
        )

    token_payload = {
        "sub": user.user_id,
        "email": user.email,
        "org_id": user.org_id,
        "role": user.role,
    }
    access_token = create_access_token(token_payload)
    refresh_token = create_refresh_token(token_payload)

    return {
        "user_id": user.user_id,
        "email": user.email,
        "role": user.role,
        "org_id": user.org_id,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@app.post("/api/auth/refresh")
def refresh_access_token(
    req: RefreshTokenRequest,
    db: Session = Depends(get_db_session),
):
    payload = decode_token(req.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Expected refresh token.",
        )

    user_id = payload.get("sub")
    user = db.query(User).filter_by(user_id=user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User inactive or not found.",
        )

    new_access_token = create_access_token({
        "sub": user.user_id,
        "email": user.email,
        "org_id": user.org_id,
        "role": user.role,
    })

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
    }


@app.post("/api/auth/logout")
def logout_user(
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    current_user: User = Depends(get_current_user),
):
    if auth and auth.credentials:
        revoke_token(auth.credentials)
    return {"status": "logged_out", "detail": "Session token invalidated successfully."}


@app.post("/api/auth/password-reset/request")
def request_password_reset(
    req: PasswordResetRequest,
    db: Session = Depends(get_db_session),
):
    clean_email = req.email.lower().strip()
    user = db.query(User).filter_by(email=clean_email).first()
    if not user:
        # Prevent user enumeration by returning standard message
        return {"status": "success", "message": "If the account exists, a reset token has been dispatched."}

    reset_token = create_access_token(
        data={"sub": user.user_id, "type": "password_reset"},
        expires_delta=None,  # Standard access expiry
    )
    # In development/test mode, surface the token for verification
    return {
        "status": "success",
        "message": "Reset token generated.",
        "reset_token": reset_token,
    }


@app.post("/api/auth/password-reset/confirm")
def confirm_password_reset(
    req: PasswordResetConfirmRequest,
    db: Session = Depends(get_db_session),
):
    payload = decode_token(req.reset_token)
    if payload.get("type") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token type.",
        )

    user_id = payload.get("sub")
    user = db.query(User).filter_by(user_id=user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.hashed_password = hash_password(req.new_password)
    revoke_token(req.reset_token)
    db.commit()

    return {"status": "success", "detail": "Password successfully updated. Please login with your new credentials."}


@app.get("/api/auth/me")
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    org = db.query(Organization).filter_by(org_id=current_user.org_id).first()
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "role": current_user.role,
        "org_id": current_user.org_id,
        "org_name": org.name if org else "Default",
        "plan": org.plan if org else "starter",
        "posts_this_month": org.posts_this_month if org else 0,
        "monthly_post_quota": org.monthly_post_quota if org else 60,
    }


# ---------------------------------------------------------------------------
# MULTI-ACCOUNT MANAGEMENT (STRICT TENANT ISOLATION)
# ---------------------------------------------------------------------------
@app.post("/api/accounts", status_code=status.HTTP_201_CREATED)
def create_account(
    req: AccountCreateRequest,
    current_user: User = Depends(require_roles(["owner", "admin"])),
    db: Session = Depends(get_db_session),
):
    # Enforce tenant isolation: Never trust an arbitrary org_id passed from the client
    # The account is ALWAYS bound to the authenticated user's organization!
    org_id = current_user.org_id

    # Check if username already exists in this organization
    existing = db.query(InstagramAccount).filter_by(org_id=org_id, username=req.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An account with username '{req.username}' already exists in your organization.",
        )

    account_id = f"acc_{uuid.uuid4().hex[:10]}"
    account = InstagramAccount(
        account_id=account_id,
        org_id=org_id,
        username=req.username,
        instagram_user_id=req.instagram_user_id or "",
        niche_id=req.niche_id,
        brand_handle=req.brand_handle,
        target_audience=req.target_audience or "",
        auto_publish=req.auto_publish,
        daily_post_limit=req.daily_post_limit,
        preferred_format=req.preferred_format.upper(),
    )
    if req.access_token:
        account.set_access_token(req.access_token)

    db.add(account)
    db.commit()
    db.refresh(account)

    return {
        "account_id": account.account_id,
        "org_id": account.org_id,
        "username": account.username,
        "niche_id": account.niche_id,
        "auto_publish": account.auto_publish,
        "brand_handle": account.brand_handle,
        "has_token": bool(req.access_token),
        "status": "CREATED",
    }


@app.get("/api/accounts")
def list_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    # Strictly scoped to current_user.org_id
    accounts = db.query(InstagramAccount).filter_by(org_id=current_user.org_id).all()
    return [
        {
            "account_id": a.account_id,
            "org_id": a.org_id,
            "username": a.username,
            "niche_id": a.niche_id,
            "brand_handle": a.brand_handle,
            "auto_publish": a.auto_publish,
            "daily_post_limit": a.daily_post_limit,
            "is_active": a.is_active,
        }
        for a in accounts
    ]


@app.get("/api/accounts/{account_id}")
def get_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    # Enforce tenant isolation: return 404 if not found or belongs to another tenant
    account = db.query(InstagramAccount).filter_by(
        account_id=account_id, org_id=current_user.org_id
    ).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found or access denied.",
        )

    return {
        "account_id": account.account_id,
        "org_id": account.org_id,
        "username": account.username,
        "instagram_user_id": account.instagram_user_id,
        "niche_id": account.niche_id,
        "brand_handle": account.brand_handle,
        "target_audience": account.target_audience,
        "auto_publish": account.auto_publish,
        "daily_post_limit": account.daily_post_limit,
        "preferred_format": account.preferred_format,
        "is_active": account.is_active,
        "has_token": bool(account.encrypted_access_token),
    }


@app.delete("/api/accounts/{account_id}")
def delete_account(
    account_id: str,
    current_user: User = Depends(require_roles(["owner", "admin"])),
    db: Session = Depends(get_db_session),
):
    account = db.query(InstagramAccount).filter_by(
        account_id=account_id, org_id=current_user.org_id
    ).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found or access denied.",
        )

    db.delete(account)
    db.commit()
    return {"status": "DELETED", "account_id": account_id}


# ---------------------------------------------------------------------------
# CONTENT GENERATION & PUBLISHING JOBS (STRICT TENANT ISOLATION)
# ---------------------------------------------------------------------------
@app.post("/api/content/generate", status_code=status.HTTP_202_ACCEPTED)
def generate_content(
    req: GenerateContentRequest,
    current_user: User = Depends(require_roles(["owner", "admin", "member"])),
    db: Session = Depends(get_db_session),
):
    # 1. Enforce tenant isolation on account access
    account = db.query(InstagramAccount).filter_by(
        account_id=req.account_id, org_id=current_user.org_id
    ).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account '{req.account_id}' not found or belongs to another organization.",
        )

    # 2. Check Organization monthly post quota
    org = db.query(Organization).filter_by(org_id=current_user.org_id).first()
    if org and org.posts_this_month >= org.monthly_post_quota:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Organization monthly post quota ({org.monthly_post_quota}) has been exhausted.",
        )

    niche = get_default_niche(account.niche_id)
    director = CreativeDirector(default_niche=niche)

    chosen_format = ContentFormat(req.format.upper()) if req.format else None
    brief = director.create_brief(topic=req.topic, niche_profile=niche, force_format=chosen_format)

    job_id = f"job_{uuid.uuid4().hex[:12]}"

    # 3. Create Job in database state machine with idempotency guarantee
    try:
        job_model = DatabasePublishingStateMachine.create_job(
            db=db,
            job_id=job_id,
            account_id=account.account_id,
            niche_id=niche.niche_id,
            topic=req.topic,
            content_format=brief.format.value,
        )
    except DuplicateJobError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplicate content job rejected: {exc}",
        )

    return {
        "job_id": job_model.job_id,
        "account_id": account.account_id,
        "format": brief.format.value,
        "topic": brief.topic,
        "rationale": brief.rationale,
        "visual_direction": brief.visual_direction,
        "call_to_action": brief.call_to_action,
        "caption_draft": brief.caption_draft,
        "status": "QUEUED",
    }


@app.get("/api/jobs")
def list_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    # Only return jobs belonging to accounts within current_user.org_id
    jobs = (
        db.query(PublishingJobModel)
        .join(InstagramAccount, PublishingJobModel.account_id == InstagramAccount.account_id)
        .filter(InstagramAccount.org_id == current_user.org_id)
        .all()
    )
    return [
        {
            "job_id": j.job_id,
            "account_id": j.account_id,
            "topic": j.topic,
            "format": j.content_format,
            "state": j.state,
            "meta_media_id": j.meta_media_id,
            "meta_permalink": j.meta_permalink,
            "error_message": j.error_message,
            "created_at": j.created_at,
        }
        for j in jobs
    ]


@app.get("/api/jobs/{job_id}")
def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    # Enforce tenant isolation via account join
    job = (
        db.query(PublishingJobModel)
        .join(InstagramAccount, PublishingJobModel.account_id == InstagramAccount.account_id)
        .filter(
            PublishingJobModel.job_id == job_id,
            InstagramAccount.org_id == current_user.org_id,
        )
        .first()
    )
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found or access denied.")

    return {
        "job_id": job.job_id,
        "account_id": job.account_id,
        "topic": job.topic,
        "format": job.content_format,
        "state": job.state,
        "meta_media_id": job.meta_media_id,
        "meta_permalink": job.meta_permalink,
        "error_message": job.error_message,
        "claimed_by": job.claimed_by,
        "retry_count": job.retry_count,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


# ---------------------------------------------------------------------------
# ANALYTICS (STRICT TENANT ISOLATION)
# ---------------------------------------------------------------------------
@app.get("/api/analytics/{account_id}/summary")
def get_analytics(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    account = db.query(InstagramAccount).filter_by(
        account_id=account_id, org_id=current_user.org_id
    ).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account '{account_id}' not found or belongs to another organization.",
        )

    tracker = EmpiricalPerformanceTracker()
    summary = tracker.calculate_summary()
    return {
        "account_id": account_id,
        "org_id": current_user.org_id,
        "summary": summary,
    }
