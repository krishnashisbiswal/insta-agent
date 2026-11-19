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
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.instagram.meta_graph_api import MetaInstagramClient
from app.models.saas_models import InstagramAccount, Organization, PublishingJobModel, get_db_session
from app.publishing.pre_publish_validator import PrePublishValidator
from app.publishing.publishing_errors import (
    DuplicatePublishPreventedError,
    PublishingAuthError,
    PublishingConfigError,
    PublishingError,
    PublishingNetworkError,
    PublishingRateLimitError,
    PublishingUncertainOutcomeError,
    PublishingValidationError,
)
from app.publishing.state_machine import (
    DatabasePublishingStateMachine,
    DuplicateJobError,
    PublishingState,
    PublishingStateMachine,
    compute_content_fingerprint,
    compute_video_fingerprint,
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
            import re
            recent_media = meta_client.get_recent_media(limit=5)
            clean_topic = topic.strip().lower()
            topic_words = set(re.findall(r"\w+", clean_topic)) - {"the", "a", "an", "in", "on", "of", "and", "or", "to", "for", "with", "analysis", "breakdown"}
            for m in recent_media:
                caption = m.get("caption", "").lower()
                if clean_topic in caption or caption in clean_topic:
                    logger.info(f"Reconciliation MATCH: Found already published media {m.get('id')} on Meta")
                    return m
                # Check significant keyword overlap
                caption_words = set(re.findall(r"\w+", caption))
                common_words = topic_words.intersection(caption_words)
                if len(common_words) >= 2:
                    logger.info(f"Reconciliation MATCH (Keyword overlap {common_words}): Found media {m.get('id')} on Meta")
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
        min_size_bytes: int = 250,
    ) -> PublishingJobModel:
        db = self._get_db()
        account = db.query(InstagramAccount).filter_by(account_id=account_id).first()
        job_id = job_id or f"job_{uuid.uuid4().hex[:12]}"
        attempt_id = f"att_{uuid.uuid4().hex[:8]}"
        video_path = Path(video_path)

        logger.info(f"[PUBLISH:START] Job {job_id} initiated for account '{account_id}' (Topic: '{topic[:50]}')")

        # 1. Pre-Publish Content & Media Quality Validation Gate
        val_report = PrePublishValidator.validate_reel(
            video_path=video_path,
            caption=caption,
            min_size_bytes=min_size_bytes,
        )
        if not val_report.is_valid:
            logger.error(f"[PUBLISH:VALIDATION_FAILED] Job {job_id}: {val_report.errors}")
            val_report.raise_if_invalid()

        logger.info(f"[PUBLISH:VALIDATION_PASSED] Job {job_id} passed technical and content checks.")

        # 2. Compute fingerprints for duplicate prevention
        video_fingerprint = compute_video_fingerprint(video_path)
        content_fingerprint = compute_content_fingerprint(topic, caption)

        # 3. Create Job with Idempotency enforcement in database
        try:
            job = self.state_machine.create_job(
                job_id=job_id,
                account_id=account_id,
                niche_id=niche_id,
                topic=topic,
                content_format="REEL",
                video_fingerprint=video_fingerprint,
                content_fingerprint=content_fingerprint,
                attempt_id=attempt_id,
            )
        except DuplicateJobError as dje:
            logger.warning(f"[PUBLISH:DUPLICATE_PREVENTED] Job {job_id} blocked: {dje}")
            raise

        should_dry_run = force_dry_run or not self.is_auto_publish_enabled(account)

        if should_dry_run:
            logger.info(f"[PUBLISH:DRY_RUN] Job {job_id} executing in DRY_RUN simulation mode.")
            job = self.state_machine.transition(
                job_id=job_id,
                to_state=PublishingState.DRY_RUN,
                actor="publishing_service",
                reason="Auto-publish disabled or dry_run requested",
                metadata={
                    "rendered_assets": [str(video_path)],
                    "video_fingerprint": video_fingerprint,
                    "content_fingerprint": content_fingerprint,
                    "error_message": None,
                },
            )
            return job

        # 4. Quota Check
        if account and account.organization:
            if not self.check_quota(account.organization):
                err = f"Organization '{account.org_id}' monthly quota reached ({account.organization.monthly_post_quota} posts)."
                self.state_machine.transition(
                    job_id=job_id,
                    to_state=PublishingState.FAILED,
                    metadata={"error_message": err, "error_category": "quota"},
                )
                raise PublishingConfigError(err)

        # 5. Client Configuration & Credential Check
        client = meta_client
        if not client:
            if not account or not account.get_access_token():
                err = "Instagram account credentials missing or not configured."
                self.state_machine.transition(
                    job_id=job_id,
                    to_state=PublishingState.FAILED,
                    metadata={"error_message": err, "error_category": "auth"},
                )
                raise PublishingAuthError(err)
            client = MetaInstagramClient(
                instagram_account_id=account.instagram_user_id,
                access_token=account.get_access_token(),
            )

        # 6. Pre-Publish Reconciliation check against Meta
        reconciled = self.reconcile_with_meta(account, topic, client)
        if reconciled:
            logger.info(f"[PUBLISH:RECONCILED] Found existing live publication on Meta for job {job_id}: {reconciled.get('id')}")
            self.state_machine.transition(
                job_id=job_id,
                to_state=PublishingState.UPLOADING,
                actor="publishing_service",
                reason="Pre-publish reconciliation confirmed publication on Meta",
            )
            job = self.state_machine.transition(
                job_id=job_id,
                to_state=PublishingState.PUBLISHED,
                reason="Reconciled existing publication on Meta",
                metadata={
                    "instagram_media_id": reconciled.get("id"),
                    "instagram_permalink": reconciled.get("permalink"),
                    "video_fingerprint": video_fingerprint,
                    "content_fingerprint": content_fingerprint,
                },
            )
            return job

        # 7. Live Publish with Capped Retry & Backoff
        max_attempts = 3
        attempt = 0
        result: Optional[Dict[str, Any]] = None

        while attempt < max_attempts:
            attempt += 1
            try:
                logger.info(f"[PUBLISH:UPLOAD_START] Job {job_id} (Attempt {attempt}/{max_attempts})...")
                self.state_machine.transition(
                    job_id=job_id,
                    to_state=PublishingState.UPLOADING,
                    actor="publishing_service",
                    metadata={
                        "rendered_assets": [str(video_path)],
                        "attempt_id": attempt_id,
                    },
                )

                result = client.publish_reel_resumable(
                    video_path=video_path,
                    caption=caption,
                    share_to_feed=share_to_feed,
                )
                break  # Successful upload and publish

            except PublishingRateLimitError as rle:
                logger.warning(f"[PUBLISH:RATE_LIMIT] Job {job_id} encountered rate limit: {rle}")
                if attempt >= max_attempts:
                    self.state_machine.transition(
                        job_id=job_id,
                        to_state=PublishingState.FAILED,
                        reason=str(rle),
                        metadata={"error_message": str(rle), "error_category": "rate_limit"},
                    )
                    raise
                delay = rle.retry_after_seconds or (2.0 * attempt)
                time.sleep(min(delay, 15.0))

            except PublishingUncertainOutcomeError as uoe:
                logger.warning(f"[PUBLISH:UNCERTAIN] Job {job_id} encountered uncertain outcome: {uoe}. Reconciling...")
                reconciled = self.reconcile_with_meta(account, topic, client)
                if reconciled:
                    result = {
                        "container_id": uoe.container_id or reconciled.get("id"),
                        "media_id": reconciled.get("id"),
                        "permalink": reconciled.get("permalink"),
                    }
                    break

                # Safely transition to UNCERTAIN state to prevent duplicate publication
                self.state_machine.transition(
                    job_id=job_id,
                    to_state=PublishingState.UNCERTAIN,
                    actor="publishing_service",
                    reason="Uncertain outcome during publish container execution",
                    metadata={
                        "error_message": str(uoe),
                        "error_category": "uncertain_outcome",
                        "recovery_state": "reconciliation_pending",
                        "instagram_container_id": uoe.container_id,
                    },
                )
                raise

            except (PublishingAuthError, PublishingValidationError, PublishingConfigError) as perm_err:
                # Permanent failure: DO NOT retry
                logger.error(f"[PUBLISH:PERMANENT_ERROR] Job {job_id} failed permanently: {perm_err}")
                self.state_machine.transition(
                    job_id=job_id,
                    to_state=PublishingState.FAILED,
                    actor="publishing_service",
                    reason=str(perm_err),
                    metadata={
                        "error_message": str(perm_err),
                        "error_category": perm_err.error_category,
                    },
                )
                raise

            except Exception as exc:
                logger.warning(f"[PUBLISH:RETRY] Job {job_id} transient error (attempt {attempt}/{max_attempts}): {exc}")
                if attempt >= max_attempts:
                    # Final attempt failed - check reconciliation before marking FAILED
                    reconciled = self.reconcile_with_meta(account, topic, client)
                    if reconciled:
                        result = {
                            "container_id": reconciled.get("id"),
                            "media_id": reconciled.get("id"),
                            "permalink": reconciled.get("permalink"),
                        }
                        break

                    self.state_machine.transition(
                        job_id=job_id,
                        to_state=PublishingState.FAILED,
                        actor="publishing_service",
                        reason=str(exc),
                        metadata={"error_message": str(exc), "error_category": "transient"},
                    )
                    raise
                time.sleep(1.5 * attempt)

        # 8. Record Successful Publication
        if not result:
            raise RuntimeError(f"Publishing failed for job {job_id}: no result produced.")

        job = self.state_machine.transition(
            job_id=job_id,
            to_state=PublishingState.PUBLISHED,
            actor="publishing_service",
            reason="Published to Meta Graph API",
            metadata={
                "instagram_container_id": result.get("container_id"),
                "instagram_media_id": result.get("media_id"),
                "instagram_permalink": result.get("permalink"),
                "video_fingerprint": video_fingerprint,
                "content_fingerprint": content_fingerprint,
            },
        )

        logger.info(f"[PUBLISH:SUCCESS] Job {job_id} published successfully! Media ID: {result.get('media_id')} Permalink: {result.get('permalink')}")

        # Increment org quota usage
        if account and account.organization:
            account.organization.posts_this_month += 1
            db.commit()

        return job

    def recover_job(
        self,
        job_id: str,
        meta_client: Optional[MetaInstagramClient] = None,
    ) -> Optional[PublishingJobModel]:
        """
        Safely recovers an interrupted or uncertain publishing job.
        Checks Meta reconciliation to confirm whether publication actually succeeded.
        """
        job = self.get_job_status(job_id)
        if not job:
            return None

        if job.state == PublishingState.PUBLISHED.value:
            logger.info(f"[PUBLISH:RECOVERY] Job {job_id} is already in terminal PUBLISHED state.")
            return job

        db = self._get_db()
        account = db.query(InstagramAccount).filter_by(account_id=job.account_id).first()
        client = meta_client
        if not client and account and account.get_access_token():
            client = MetaInstagramClient(
                instagram_account_id=account.instagram_user_id,
                access_token=account.get_access_token(),
            )

        if client and client.is_configured:
            reconciled = self.reconcile_with_meta(account, job.topic, client)
            if reconciled:
                logger.info(f"[PUBLISH:RECOVERY_SUCCESS] Reconciled job {job_id} on Meta: {reconciled.get('id')}")
                return self.state_machine.transition(
                    job_id=job_id,
                    to_state=PublishingState.PUBLISHED,
                    actor="recovery_agent",
                    reason="Recovered via Meta reconciliation",
                    metadata={
                        "instagram_media_id": reconciled.get("id"),
                        "instagram_permalink": reconciled.get("permalink"),
                        "recovery_state": "reconciled_published",
                    },
                )

        if job.state == PublishingState.UNCERTAIN.value:
            logger.warning(f"[PUBLISH:RECOVERY] Job {job_id} could not be reconciled. Leaving in UNCERTAIN state to prevent duplicate.")
        return job

    def get_job_status(self, job_id: str) -> Optional[PublishingJobModel]:
        return self.state_machine.get_job(job_id)

    def list_jobs(self, account_id: Optional[str] = None) -> List[PublishingJobModel]:
        return self.state_machine.list_jobs(account_id)
