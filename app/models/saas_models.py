"""
Multi-Tenant SaaS Database Models (SQLAlchemy 2.0).

Enforces strict tenant isolation across organizations, accounts, publishing jobs,
and encrypted credentials at rest.
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
    plan: Mapped[str] = mapped_column(String(50), default="starter")  # starter, pro, agency
    monthly_budget_usd: Mapped[float] = mapped_column(Float, default=100.0)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)

    users: Mapped[List["User"]] = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    accounts: Mapped[List["InstagramAccount"]] = relationship("InstagramAccount", back_populates="organization", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(64), ForeignKey("organizations.org_id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="member")  # owner, admin, member
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="users")


class NicheProfileModel(Base):
    __tablename__ = "niche_profiles"

    niche_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    org_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("organizations.org_id"), nullable=True)
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

    @property
    def content_pillars(self) -> List[str]:
        try:
            return json.loads(self.content_pillars_json)
        except Exception:
            return []

    @property
    def cta_presets(self) -> List[str]:
        try:
            return json.loads(self.cta_presets_json)
        except Exception:
            return []


class InstagramAccount(Base):
    __tablename__ = "instagram_accounts"

    account_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(64), ForeignKey("organizations.org_id"), nullable=False)
    username: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    instagram_user_id: Mapped[str] = mapped_column(String(128), default="")
    encrypted_access_token: Mapped[str] = mapped_column(Text, default="")
    niche_id: Mapped[str] = mapped_column(String(64), default="tech_ai")
    brand_handle: Mapped[str] = mapped_column(String(128), default="")
    target_audience: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(64), default="English")
    auto_publish: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_post_limit: Mapped[int] = mapped_column(Integer, default=2)
    preferred_format: Mapped[str] = mapped_column(String(32), default="REEL")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="accounts")
    jobs: Mapped[List["PublishingJobModel"]] = relationship("PublishingJobModel", back_populates="account", cascade="all, delete-orphan")

    def set_access_token(self, plaintext_token: str) -> None:
        self.encrypted_access_token = encrypt_token(plaintext_token)

    def get_access_token(self) -> str:
        return decrypt_token(self.encrypted_access_token)


class PublishingJobModel(Base):
    __tablename__ = "publishing_jobs"

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(64), ForeignKey("instagram_accounts.account_id"), nullable=False)
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
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time)

    account: Mapped["InstagramAccount"] = relationship("InstagramAccount", back_populates="jobs")

    __table_args__ = (
        Index("idx_account_state", "account_id", "state"),
    )


# ---------------------------------------------------------------------------
# DATABASE INITIALIZATION AND SESSION FACTORY
# ---------------------------------------------------------------------------
_engine = None
_SessionFactory = None


def get_db_url() -> str:
    db_url = os.getenv("DATABASE_URL", "").strip()
    if db_url:
        # Compatibility fix for postgres:// -> postgresql:// in modern SQLAlchemy
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return db_url
    # Local SQLite fallback
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
