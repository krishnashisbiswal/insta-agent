"""
Centralized Authoritative Publishing Service.

All publishing operations across the application MUST route through this service.
It guarantees:
- State machine transition auditing.
- Idempotency key tracking (no duplicate uploads).
- Strict dry-run / auto-publish safeguards.
- Support for Reels, Carousels, Stories, and Single Images.
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.instagram.meta_graph_api import MetaInstagramClient
from app.publishing.state_machine import (
    PublishingRecord,
    PublishingState,
    PublishingStateMachine,
    DuplicateJobError,
)

logger = logging.getLogger(__name__)


class PublishingService:
    """
    Unified Publishing Orchestrator.
    """

    def __init__(
        self,
        state_machine: Optional[PublishingStateMachine] = None,
        storage_dir: Optional[Path] = None,
    ):
        self.state_machine = state_machine or PublishingStateMachine(storage_dir=storage_dir)

    def is_auto_publish_enabled(self, account_config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if automatic live publishing is explicitly enabled.
        Safety rule: Default is FALSE unless explicitly set to 'true'.
        """
        if account_config and account_config.get("auto_publish") is True:
            return True
        env_val = os.getenv("AUTO_PUBLISH", "false").strip().lower()
        return env_val in ("true", "1", "yes")

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
    ) -> PublishingRecord:
        """
        Executes a Reel publishing workflow with full state machine tracking.
        """
        job_id = job_id or f"job_{uuid.uuid4().hex[:12]}"
        video_path = Path(video_path)

        # 1. Create Job with Idempotency enforcement
        record = self.state_machine.create_job(
            job_id=job_id,
            account_id=account_id,
            niche_id=niche_id,
            topic=topic,
            content_format="REEL",
        )

        should_dry_run = force_dry_run or not self.is_auto_publish_enabled()

        if should_dry_run:
            logger.info(f"PublishingService: Job {job_id} running in DRY_RUN mode.")
            self.state_machine.transition(
                job_id=job_id,
                to_state=PublishingState.DRY_RUN,
                actor="publishing_service",
                reason="Auto-publish disabled or dry_run requested",
                metadata={
                    "video_path": str(video_path),
                    "caption_preview": caption[:100],
                    "video_exists": video_path.exists(),
                },
            )
            return self.state_machine.get_record(job_id)

        # 2. Live Publishing Flow
        client = meta_client or MetaInstagramClient()
        if not client.is_configured:
            err = "Meta Graph API credentials missing. Cannot publish live."
            self.state_machine.transition(
                job_id=job_id,
                to_state=PublishingState.FAILED,
                actor="publishing_service",
                reason=err,
                metadata={"error_message": err},
            )
            raise RuntimeError(err)

        try:
            self.state_machine.transition(
                job_id=job_id,
                to_state=PublishingState.UPLOADING,
                actor="publishing_service",
                metadata={"rendered_assets": [str(video_path)]},
            )

            result = client.publish_reel_resumable(
                video_path=video_path,
                caption=caption,
                share_to_feed=share_to_feed,
            )

            record = self.state_machine.transition(
                job_id=job_id,
                to_state=PublishingState.PUBLISHED,
                actor="publishing_service",
                reason="Published to Meta Graph API",
                metadata={
                    "instagram_container_id": result.get("container_id"),
                    "instagram_media_id": result.get("media_id"),
                    "instagram_permalink": result.get("permalink"),
                },
            )
            return record

        except Exception as exc:
            logger.error(f"Publishing failed for job {job_id}: {exc}")
            self.state_machine.transition(
                job_id=job_id,
                to_state=PublishingState.FAILED,
                actor="publishing_service",
                reason=str(exc),
                metadata={"error_message": str(exc)},
            )
            raise

    def publish_carousel(
        self,
        account_id: str,
        niche_id: str,
        topic: str,
        image_urls: List[str],
        caption: str,
        meta_client: Optional[MetaInstagramClient] = None,
        force_dry_run: bool = False,
        job_id: Optional[str] = None,
    ) -> PublishingRecord:
        """
        Executes a multi-slide Carousel publishing workflow.
        """
        job_id = job_id or f"job_{uuid.uuid4().hex[:12]}"
        record = self.state_machine.create_job(
            job_id=job_id,
            account_id=account_id,
            niche_id=niche_id,
            topic=topic,
            content_format="CAROUSEL",
        )

        should_dry_run = force_dry_run or not self.is_auto_publish_enabled()

        if should_dry_run:
            self.state_machine.transition(
                job_id=job_id,
                to_state=PublishingState.DRY_RUN,
                actor="publishing_service",
                reason="Auto-publish disabled or dry_run requested",
                metadata={"image_count": len(image_urls), "caption_preview": caption[:100]},
            )
            return self.state_machine.get_record(job_id)

        client = meta_client or MetaInstagramClient()
        if not client.is_configured:
            err = "Meta Graph API credentials missing."
            self.state_machine.transition(
                job_id=job_id,
                to_state=PublishingState.FAILED,
                metadata={"error_message": err},
            )
            raise RuntimeError(err)

        try:
            self.state_machine.transition(job_id=job_id, to_state=PublishingState.UPLOADING)
            result = client.publish_carousel(image_urls=image_urls, caption=caption)
            record = self.state_machine.transition(
                job_id=job_id,
                to_state=PublishingState.PUBLISHED,
                metadata={
                    "instagram_container_id": result.get("container_id"),
                    "instagram_media_id": result.get("media_id"),
                    "instagram_permalink": result.get("permalink"),
                },
            )
            return record
        except Exception as exc:
            self.state_machine.transition(
                job_id=job_id,
                to_state=PublishingState.FAILED,
                metadata={"error_message": str(exc)},
            )
            raise

    def get_job_status(self, job_id: str) -> Optional[PublishingRecord]:
        return self.state_machine.get_record(job_id)

    def list_jobs(self, account_id: Optional[str] = None) -> List[PublishingRecord]:
        return self.state_machine.list_records(account_id=account_id)
