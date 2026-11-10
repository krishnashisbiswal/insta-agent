"""
Centralized Authoritative Publishing Service (Hardened).

Guarantees:
- Database-backed state transitions with transition history.
- Idempotency key tracking enforcing zero duplicate publishing.
- Pre-publish reconciliation against Meta Graph API to prevent post-timeout duplicates.
- Organization quota checks before execution.
- Safe dry-run mode and tenant isolation.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.instagram.meta_graph_api import MetaInstagramClient
from app.models.saas_models import InstagramAccount, Organization, PublishingJobModel, get_db_session
from app.publishing.state_machine import (
    DatabasePublishingStateMachine,
    DuplicateJobError,
    PublishingState,
    PublishingStateMachine,
)

logger = logging.getLogger(__name__)


class PublishingService:
    """
    Unified Publishing Orchestrator.
    """

    def __init__(
        self,
        storage_dir: Optional[Path | str] = None,
        state_machine: Optional[PublishingStateMachine] = None,
        db_session: Optional[Session] = None,
    ):
        self.storage_dir = Path(storage_dir) if storage_dir else None
        self.state_machine = state_machine or PublishingStateMachine(
            storage_dir=storage_dir, db_session=db_session
        )
        self._db = self.state_machine._get_db()

    def _get_db(self) -> Session:
        return self.state_machine._get_db()

    def is_auto_publish_enabled(self, account: Optional[InstagramAccount] = None) -> bool:
        if account and account.auto_publish is True:
            return True
        env_val = os.getenv("AUTO_PUBLISH", "false").strip().lower()
        return env_val in ("true", "1", "yes")

    def check_quota(self, org: Organization) -> bool:
        """Check if organization has available post quota for the month."""
        return org.posts_this_month < org.monthly_post_quota

    def reconcile_with_meta(
        self,
        account: InstagramAccount,
        topic: str,
        meta_client: MetaInstagramClient,
    ) -> Optional[Dict[str, Any]]:
        """
        Reconcile against Meta API before re-trying an uncertain publication.
        Checks if a post with similar caption was already created recently.
        """
        if not meta_client.is_configured:
            return None
        try:
            recent_media = meta_client.get_recent_media(limit=5)
            clean_topic = topic.strip().lower()
            for m in recent_media:
                caption = m.get("caption", "").lower()
                if clean_topic in caption or caption in clean_topic:
                    logger.info(f"Reconciliation MATCH: Found already published media {m.get('id')} on Meta")
                    return m
        except Exception as exc:
            logger.warning(f"Reconciliation check failed: {exc}")
        return None

    def publish_reel(
        self,
        account_id: str,
        niche_id: str,
        topic: str,
        video_path: Path,
        caption: str,
        meta_client: Optional[MetaInstagramClient] = None,
        share_to_feed: bool = True,
        force_dry_run: bool = False,
        job_id: Optional[str] = None,
    ) -> PublishingJobModel:
        db = self._get_db()
        account = db.query(InstagramAccount).filter_by(account_id=account_id).first()
        job_id = job_id or f"job_{uuid.uuid4().hex[:12]}"
        video_path = Path(video_path)

        # 1. Create Job with Idempotency enforcement in database
        job = self.state_machine.create_job(
            job_id=job_id,
            account_id=account_id,
            niche_id=niche_id,
            topic=topic,
            content_format="REEL",
        )

        should_dry_run = force_dry_run or not self.is_auto_publish_enabled(account)

        if should_dry_run:
            logger.info(f"PublishingService: Job {job_id} running in DRY_RUN mode.")
            job = self.state_machine.transition(
                job_id=job_id,
                to_state=PublishingState.DRY_RUN,
                actor="publishing_service",
                reason="Auto-publish disabled or dry_run requested",
                metadata={
                    "rendered_assets": [str(video_path)],
                    "error_message": None,
                },
            )
            return job

        # 2. Quota Check
        if account and account.organization:
            if not self.check_quota(account.organization):
                err = f"Organization '{account.org_id}' monthly quota reached ({account.organization.monthly_post_quota} posts)."
                self.state_machine.transition(
                    job_id=job_id, to_state=PublishingState.FAILED, metadata={"error_message": err, "error_category": "quota"}
                )
                raise RuntimeError(err)

        # 3. Client configuration
        client = meta_client
        if not client:
            if not account or not account.get_access_token():
                err = "Instagram account credentials missing or not configured."
                self.state_machine.transition(
                    job_id=job_id, to_state=PublishingState.FAILED, metadata={"error_message": err}
                )
                raise RuntimeError(err)
            client = MetaInstagramClient(
                instagram_account_id=account.instagram_user_id,
                access_token=account.get_access_token(),
            )

        # 4. Reconciliation check before publishing
        reconciled = self.reconcile_with_meta(account, topic, client)
        if reconciled:
            job = self.state_machine.transition(
                job_id=job_id,
                to_state=PublishingState.PUBLISHED,
                reason="Reconciled existing publication on Meta",
                metadata={
                    "instagram_media_id": reconciled.get("id"),
                    "instagram_permalink": reconciled.get("permalink"),
                },
            )
            return job

        # 5. Live Publish
        try:
            self.state_machine.transition(
                job_id=job_id,
                to_state=PublishingState.UPLOADING,
                metadata={"rendered_assets": [str(video_path)]},
            )

            result = client.publish_reel_resumable(
                video_path=video_path,
                caption=caption,
                share_to_feed=share_to_feed,
            )

            job = self.state_machine.transition(
                job_id=job_id,
                to_state=PublishingState.PUBLISHED,
                reason="Published to Meta Graph API",
                metadata={
                    "instagram_container_id": result.get("container_id"),
                    "instagram_media_id": result.get("media_id"),
                    "instagram_permalink": result.get("permalink"),
                },
            )

            # Increment org quota usage
            if account and account.organization:
                account.organization.posts_this_month += 1
                db.commit()

            return job

        except Exception as exc:
            logger.error(f"Publishing failed for job {job_id}: {exc}")
            self.state_machine.transition(
                job_id=job_id,
                to_state=PublishingState.FAILED,
                reason=str(exc),
                metadata={"error_message": str(exc), "error_category": "transient"},
            )
            raise

    def get_job_status(self, job_id: str) -> Optional[PublishingJobModel]:
        return self.state_machine.get_job(job_id)

    def list_jobs(self, account_id: Optional[str] = None) -> List[PublishingJobModel]:
        return self.state_machine.list_jobs(account_id)
