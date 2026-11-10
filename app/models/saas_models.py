"""
Multi-Tenant SaaS Database Models (SQLAlchemy 2.0 - Hardened).

Enforces strict tenant isolation across organizations, accounts, publishing jobs,
distributed execution leases, audit trails, and encrypted credentials at rest.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Generator, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    Index,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
    Session,
)

from app.security.encryption import encrypt_token, decrypt_token
from config.settings import STORAGE_DIR

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class Organization(Base):
    __tablename__ = "organizations"

    org_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="starter")  # starter, pro, agency, enterprise
    monthly_budget_usd: Mapped[float] = mapped_column(Float, default=100.0)
    monthly_post_quota: Mapped[int] = mapped_column(Integer, default=60)
    posts_this_month: Mapped[int] = mapped_column(Integer, default=0)
    quota_reset_at: Mapped[float] = mapped_column(Float, default=time.time)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)

    users: Mapped[List["User"]] = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    accounts: Mapped[List["InstagramAccount"]] = relationship("InstagramAccount", back_populates="organization", cascade="all, delete-orphan")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="organization", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(64), ForeignKey("organizations.org_id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="member")  # owner, admin, member, analyst
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="users")


class NicheProfileModel(Base):
    __tablename__ = "niche_profiles"

    niche_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    org_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("organizations.org_id", ondelete="CASCADE"), nullable=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    target_audience: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(64), default="English")
    tone: Mapped[str] = mapped_column(String(255), default="")
    content_pillars_json: Mapped[str] = mapped_column(Text, default="[]")
    visual_style: Mapped[str] = mapped_column(Text, default="")
    audio_style: Mapped[str] = mapped_column(String(255), default="")
    cta_presets_json: Mapped[str] = mapped_column(Text, default="[]")
    glossary_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class InstagramAccount(Base):
    __tablename__ = "instagram_accounts"

    account_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(64), ForeignKey("organizations.org_id", ondelete="CASCADE"), nullable=False)
    username: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    instagram_user_id: Mapped[str] = mapped_column(String(128), default="")
    encrypted_access_token: Mapped[str] = mapped_column(Text, default="")
    encrypted_refresh_token: Mapped[str] = mapped_column(Text, default="")
    token_expires_at: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    scopes_json: Mapped[str] = mapped_column(Text, default='["instagram_basic","instagram_content_publish"]')
    reauth_required: Mapped[bool] = mapped_column(Boolean, default=False)
    niche_id: Mapped[str] = mapped_column(String(64), default="tech_ai")
    brand_handle: Mapped[str] = mapped_column(String(128), default="")
    target_audience: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(64), default="English")
    auto_publish: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_post_limit: Mapped[int] = mapped_column(Integer, default=2)
    preferred_format: Mapped[str] = mapped_column(String(32), default="REEL")
    consecutive_publish_errors: Mapped[int] = mapped_column(Integer, default=0)
    last_published_at: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="accounts")
    jobs: Mapped[List["PublishingJobModel"]] = relationship("PublishingJobModel", back_populates="account", cascade="all, delete-orphan")

    def set_access_token(self, plaintext_token: str) -> None:
        self.encrypted_access_token = encrypt_token(plaintext_token)

    def get_access_token(self) -> str:
        return decrypt_token(self.encrypted_access_token)

    def set_refresh_token(self, plaintext_token: str) -> None:
        self.encrypted_refresh_token = encrypt_token(plaintext_token)

    def get_refresh_token(self) -> str:
        return decrypt_token(self.encrypted_refresh_token)

    @property
    def is_token_expired(self) -> bool:
        if not self.token_expires_at:
            return False
        return time.time() >= self.token_expires_at


class PublishingJobModel(Base):
    __tablename__ = "publishing_jobs"

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(64), ForeignKey("instagram_accounts.account_id", ondelete="CASCADE"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    niche_id: Mapped[str] = mapped_column(String(64), default="tech_ai")
    content_format: Mapped[str] = mapped_column(String(32), default="REEL")
    state: Mapped[str] = mapped_column(String(32), index=True, default="CREATED")
    topic: Mapped[str] = mapped_column(String(512), nullable=False)
    script_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rendered_assets_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta_container_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    meta_media_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    meta_permalink: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_category: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # transient, permanent, policy, rate_limit
    history_json: Mapped[str] = mapped_column(Text, default="[]")

    # Distributed Execution Lease & Worker Concurrency
    claimed_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # worker_id
    claimed_at: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lease_expires_at: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    scheduled_at: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time)

    account: Mapped["InstagramAccount"] = relationship("InstagramAccount", back_populates="jobs")

    @property
    def instagram_container_id(self) -> Optional[str]:
        return self.meta_container_id

    @instagram_container_id.setter
    def instagram_container_id(self, val: Optional[str]) -> None:
        self.meta_container_id = val

    @property
    def instagram_media_id(self) -> Optional[str]:
        return self.meta_media_id

    @instagram_media_id.setter
    def instagram_media_id(self, val: Optional[str]) -> None:
        self.meta_media_id = val

    @property
    def instagram_permalink(self) -> Optional[str]:
        return self.meta_permalink

    @instagram_permalink.setter
    def instagram_permalink(self, val: Optional[str]) -> None:
        self.meta_permalink = val

    @property
    def history(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self.history_json) if self.history_json else []
        except Exception:
            return []

    @history.setter
    def history(self, val: List[Dict[str, Any]]) -> None:
        self.history_json = json.dumps(val)

    __table_args__ = (
        Index("idx_account_state", "account_id", "state"),
        Index("idx_lease", "state", "lease_expires_at"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(64), ForeignKey("organizations.org_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    timestamp: Mapped[float] = mapped_column(Float, default=time.time)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="audit_logs")


# ---------------------------------------------------------------------------
# DATABASE INITIALIZATION AND SESSION FACTORY
# ---------------------------------------------------------------------------
_engine = None
_SessionFactory = None


def get_db_url() -> str:
    db_url = os.getenv("DATABASE_URL", "").strip()
    if db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return db_url
    sqlite_path = STORAGE_DIR / "insta_agent_saas.db"
    return f"sqlite:///{sqlite_path}"


def init_db(db_url: Optional[str] = None):
    global _engine, _SessionFactory
    url = db_url or get_db_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    _engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
    _SessionFactory = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=_engine)
    logger.info(f"Database initialized with URL: {url.split('@')[-1] if '@' in url else url}")
    return _engine


def get_db_session() -> Generator[Session, None, None]:
    global _SessionFactory
    if _SessionFactory is None:
        init_db()
    session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
