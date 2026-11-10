"""
Commercial SaaS REST API (FastAPI).

Features:
- Multi-account management with encrypted token storage.
- Multi-niche support and dynamic content generation router.
- Publishing queue and state machine inspection.
- Empirical analytics endpoints.
- Production readiness and system health checks.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.gemini_client import check_health as check_gemini_health
from app.analytics.meta_insights import EmpiricalPerformanceTracker
from app.creative.creative_director import ContentFormat, CreativeDirector
from app.models.saas_models import (
    InstagramAccount,
    NicheProfileModel,
    Organization,
    PublishingJobModel,
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
from app.publishing.state_machine import PublishingState

logger = logging.getLogger(__name__)

# Initialize database on startup
init_db()

app = FastAPI(
    title="Insta-Agent Production SaaS API",
    version="2.0.0",
    description="Autonomous multi-account, multi-niche Instagram AI content generation and publishing engine.",
)


# ---------------------------------------------------------------------------
# PYDANTIC SCHEMAS
# ---------------------------------------------------------------------------
class AccountCreateRequest(BaseModel):
    org_id: str = Field(..., json_schema_extra={"example": "org_default"})
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
    format: Optional[str] = Field(None, json_schema_extra={"example": "REEL"})  # REEL, CAROUSEL, STORY, POST
    language: Optional[str] = Field("English", json_schema_extra={"example": "English"})
    auto_publish_override: Optional[bool] = Field(None, json_schema_extra={"example": False})


# ---------------------------------------------------------------------------
# API ROUTES
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


# --- Multi-Account Management ---
@app.post("/api/accounts", status_code=status.HTTP_201_CREATED)
def create_account(
    req: AccountCreateRequest,
    db: Session = Depends(get_db_session),
):
    # Ensure organization exists
    org = db.query(Organization).filter_by(org_id=req.org_id).first()
    if not org:
        org = Organization(org_id=req.org_id, name=f"Organization {req.org_id}")
        db.add(org)
        db.commit()

    account_id = f"acc_{uuid.uuid4().hex[:10]}"
    account = InstagramAccount(
        account_id=account_id,
        org_id=req.org_id,
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
        "username": account.username,
        "niche_id": account.niche_id,
        "auto_publish": account.auto_publish,
        "brand_handle": account.brand_handle,
        "has_token": bool(req.access_token),
        "status": "CREATED",
    }


@app.get("/api/accounts")
def list_accounts(
    org_id: Optional[str] = None,
    db: Session = Depends(get_db_session),
):
    query = db.query(InstagramAccount)
    if org_id:
        query = query.filter_by(org_id=org_id)
    accounts = query.all()
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


# --- Niche Profiles ---
@app.get("/api/niches")
def list_niches():
    registry = NicheRegistry()
    return [p.to_dict() for p in registry.list_all()]


# --- Content Generation & Scheduling ---
@app.post("/api/content/generate", status_code=status.HTTP_202_ACCEPTED)
def generate_content(
    req: GenerateContentRequest,
    db: Session = Depends(get_db_session),
):
    account = db.query(InstagramAccount).filter_by(account_id=req.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail=f"Account '{req.account_id}' not found.")

    niche = get_default_niche(account.niche_id)
    director = CreativeDirector(default_niche=niche)

    chosen_format = ContentFormat(req.format.upper()) if req.format else None
    brief = director.create_brief(topic=req.topic, niche_profile=niche, force_format=chosen_format)

    job_id = f"job_{uuid.uuid4().hex[:12]}"
    ps = PublishingService()
    idempotency_key = ps.state_machine.compute_idempotency_key(
        account_id=account.account_id,
        niche_id=niche.niche_id,
        topic=req.topic,
        content_format=brief.format.value,
    )

    # Save to database
    job_model = PublishingJobModel(
        job_id=job_id,
        account_id=account.account_id,
        idempotency_key=idempotency_key,
        niche_id=niche.niche_id,
        content_format=brief.format.value,
        state=PublishingState.CREATED.value,
        topic=req.topic,
    )
    db.add(job_model)
    db.commit()

    return {
        "job_id": job_id,
        "account_id": account.account_id,
        "format": brief.format.value,
        "topic": brief.topic,
        "rationale": brief.rationale,
        "visual_direction": brief.visual_direction,
        "call_to_action": brief.call_to_action,
        "caption_draft": brief.caption_draft,
        "status": "QUEUED",
    }


@app.get("/api/jobs/{job_id}")
def get_job(
    job_id: str,
    db: Session = Depends(get_db_session),
):
    job = db.query(PublishingJobModel).filter_by(job_id=job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    return {
        "job_id": job.job_id,
        "account_id": job.account_id,
        "topic": job.topic,
        "format": job.content_format,
        "state": job.state,
        "meta_media_id": job.meta_media_id,
        "meta_permalink": job.meta_permalink,
        "error_message": job.error_message,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


# --- Analytics ---
@app.get("/api/analytics/{account_id}/summary")
def get_analytics(account_id: str):
    tracker = EmpiricalPerformanceTracker()
    summary = tracker.calculate_summary()
    return {
        "account_id": account_id,
        "summary": summary,
    }
