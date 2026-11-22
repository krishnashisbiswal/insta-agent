import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.publishing.pre_publish_validator import PrePublishValidator
from app.publishing.publishing_errors import (
    DuplicatePublishPreventedError,
    HardUploadGateError,
    PublishingAuthError,
    PublishingConfigError,
    PublishingNetworkError,
    PublishingRateLimitError,
    PublishingUncertainOutcomeError,
    PublishingValidationError,
)
from app.publishing.state_machine import compute_video_fingerprint
from app.video.video_quality_gate import ValidationReport, VideoQualityGate
from config.settings import (
    GRAPH_API_BASE_URL,
    IG_SESSION_FILE,
    INSTAGRAM_ACCESS_TOKEN,
    INSTAGRAM_PASSWORD,
    INSTAGRAM_SESSION_DATA,
    INSTAGRAM_SESSION_ID,
    INSTAGRAM_UPLOAD_METHOD,
    INSTAGRAM_USER_ID,
    INSTAGRAM_USERNAME,
    OUTPUT_DIR,
)

logger = logging.getLogger(__name__)


class InstagramUploader:
    """
    Unified Instagram Reel Publisher.
    Supports:
    1. Direct Account Upload via instagrapi (username/password or session - no Meta app needed!)
    2. Official Meta Graph API Resumable Upload (for verified business/creator accounts)
    3. Safe Dry-Run Mode (validates video and generates manifests without publishing)
    """

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        session_id: Optional[str] = None,
        session_data: Optional[str] = None,
        user_id: Optional[str] = None,
        access_token: Optional[str] = None,
        session_file: Optional[Path] = None,
    ):
        self.username = (username if username is not None else INSTAGRAM_USERNAME).strip()
        self.password = (password if password is not None else INSTAGRAM_PASSWORD).strip()
        self.session_id = (session_id if session_id is not None else INSTAGRAM_SESSION_ID).strip()
        self.session_data = (
            session_data
            if session_data is not None
            else (INSTAGRAM_SESSION_DATA or os.getenv("INSTAGRAM_SESSION_DATA", ""))
        ).strip()
        self.user_id = (user_id if user_id is not None else INSTAGRAM_USER_ID).strip()
        self.access_token = (access_token if access_token is not None else INSTAGRAM_ACCESS_TOKEN).strip()
        self.session_file = Path(session_file) if session_file is not None else IG_SESSION_FILE
        self._instagrapi_client = None

    def has_direct_credentials(self) -> bool:
        """Check if Direct Instagram account credentials or session are configured."""
        has_session = bool(
            self.session_id
            or self.session_data
            or (self.session_file and self.session_file.exists() and self.session_file.stat().st_size > 10 and bool(self.username or self.session_id or self.session_data))
        )
        return bool((self.username and self.password) or has_session)

    def has_graph_credentials(self) -> bool:
        """Check if Meta Graph API credentials are configured."""
        return bool(self.user_id and self.access_token)

    def has_credentials(self) -> bool:
        """Check if any publishing credentials exist."""
        return self.has_direct_credentials() or self.has_graph_credentials()

    def get_preferred_method(self) -> str:
        """
        Determine whether to use official Meta Graph API or direct instagrapi.
        Prioritizes official Meta Graph API for production reliability.
        """
        upload_method = os.getenv("INSTAGRAM_UPLOAD_METHOD", INSTAGRAM_UPLOAD_METHOD).strip().lower()
        if upload_method == "graph_api":
            if self.has_graph_credentials():
                return "graph_api"
            raise PublishingConfigError(
                "INSTAGRAM_UPLOAD_METHOD is set to 'graph_api' but INSTAGRAM_USER_ID or INSTAGRAM_ACCESS_TOKEN is missing."
            )
        if upload_method == "direct":
            if self.has_direct_credentials():
                return "direct"
            raise PublishingConfigError(
                "INSTAGRAM_UPLOAD_METHOD is set to 'direct' but direct credentials/session are missing."
            )
        # Auto-detect: Prioritize official Meta Graph API for production stability
        if self.has_graph_credentials():
            return "graph_api"
        if self.has_direct_credentials():
            return "direct"
        return "dry_run"

    # -----------------------------------------------------------------------
    # METHOD 1: DIRECT INSTAGRAM ACCOUNT UPLOAD (instagrapi)
    # -----------------------------------------------------------------------
    def _init_direct_client(self):
        """Initialize and authenticate instagrapi Client with session persistence."""
        from instagrapi import Client

        if self._instagrapi_client is not None:
            return self._instagrapi_client

        cl = Client()
        cl.delay_range = [1, 3]

        # Check if full session data was passed via environment variable (e.g. GitHub Actions)
        session_data_env = self.session_data or os.getenv("INSTAGRAM_SESSION_DATA", "").strip()
        if session_data_env and (not self.session_file.exists() or self.session_file.stat().st_size == 0):
            try:
                raw_json = session_data_env
                if not session_data_env.startswith("{"):
                    try:
                        import base64
                        decoded = base64.b64decode(session_data_env).decode("utf-8")
                        if decoded.startswith("{"):
                            raw_json = decoded
                    except Exception:
                        pass
                self.session_file.parent.mkdir(parents=True, exist_ok=True)
                self.session_file.write_text(raw_json, encoding="utf-8")
                print(f"[INSTAGRAM DIRECT] Restored session file from INSTAGRAM_SESSION_DATA.")
            except Exception as e:
                logger.warning(f"Failed restoring session data: {e}")

        # Try to reuse saved session if available (only if direct credentials or session were provided)
        if self.session_file.exists() and bool(self.username or self.session_id or self.session_data):
            try:
                print(f"[INSTAGRAM DIRECT] Loading saved session from {self.session_file.name}...")
                cl.load_settings(str(self.session_file))
                # Validate if loaded session is still active
                try:
                    cl.get_timeline_feed()
                    print(f"[INSTAGRAM DIRECT] Saved session is valid and active!")
                    self._instagrapi_client = cl
                    return cl
                except Exception as sess_exc:
                    print(f"[INSTAGRAM DIRECT] Cached session expired or invalid ({sess_exc}). Re-authenticating with credentials...")
                    if self.username and self.password:
                        try:
                            cl.login(self.username, self.password)
                            cl.dump_settings(str(self.session_file))
                            self._instagrapi_client = cl
                            return cl
                        except Exception as login_exc:
                            login_str = str(login_exc).lower()
                            if "qe/expose" in login_str or "404" in login_str:
                                raise PublishingAuthError(
                                    f"Direct Instagram login failed at /api/v1/qe/expose/ endpoint (404 Not Found): {login_exc}. "
                                    f"Instagram has blocked or deprecated this private mobile API endpoint. "
                                    f"To resolve, configure official Meta Graph API credentials: INSTAGRAM_USER_ID and INSTAGRAM_ACCESS_TOKEN."
                                ) from login_exc
                            raise PublishingAuthError(f"Direct Instagram authentication failure: {login_exc}") from login_exc
            except PublishingAuthError:
                raise
            except Exception as exc:
                logger.warning(f"Could not reuse session file: {exc}. Logging in fresh...")

        # Login with session ID if provided
        try:
            if self.session_id:
                print("[INSTAGRAM DIRECT] Authenticating via session ID...")
                cl.login_by_sessionid(self.session_id)
            elif self.username and self.password:
                print(f"[INSTAGRAM DIRECT] Authenticating @{self.username}...")
                cl.login(self.username, self.password)
            else:
                raise PublishingConfigError(
                    "Missing valid Instagram credentials. Provide INSTAGRAM_USER_ID & INSTAGRAM_ACCESS_TOKEN (Graph API), "
                    "or INSTAGRAM_SESSION_DATA, INSTAGRAM_SESSION_ID, or INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in .env or GitHub Secrets."
                )
        except (PublishingAuthError, PublishingConfigError):
            raise
        except Exception as exc:
            exc_str = str(exc).lower()
            if "qe/expose" in exc_str or "404" in exc_str:
                raise PublishingAuthError(
                    f"Direct Instagram login failed at /api/v1/qe/expose/ endpoint (404 Not Found): {exc}. "
                    f"Instagram has blocked or deprecated this private mobile API endpoint. "
                    f"To resolve, configure official Meta Graph API credentials: INSTAGRAM_USER_ID and INSTAGRAM_ACCESS_TOKEN."
                ) from exc
            if "login" in exc_str or "checkpoint" in exc_str or "challenge" in exc_str or "password" in exc_str:
                raise PublishingAuthError(f"Direct Instagram authentication failure: {exc}") from exc
            raise PublishingNetworkError(f"Direct Instagram login network failure: {exc}") from exc

        # Save session to avoid repeated logins
        try:
            self.session_file.parent.mkdir(parents=True, exist_ok=True)
            cl.dump_settings(str(self.session_file))
            print(f"[INSTAGRAM DIRECT] Session cached to {self.session_file.name}")
        except Exception as exc:
            logger.warning(f"Failed to cache session: {exc}")

        self._instagrapi_client = cl
        return cl

    def enforce_hard_upload_gate(
        self,
        video_path: Path,
        validation_report: Optional[ValidationReport] = None,
        job_id: Optional[str] = None,
    ) -> None:
        """
        Hard Pre-Upload Quality Gate.
        Aborts upload immediately if:
        1. File does not exist or was modified after validation.
        2. Validation report is missing or status != 'VALIDATED'.
        3. Fresh SHA-256 hash does not match validated hash.
        4. Artifact does not belong to the active production job.
        """
        is_ok, reason = VideoQualityGate.verify_artifact_integrity_before_upload(
            video_path=video_path,
            expected_report=validation_report,
            job_id=job_id,
        )
        if not is_ok:
            logger.error(f"[HARD UPLOAD GATE REJECTION] {reason}")
            raise HardUploadGateError(
                f"Hard Upload Gate Aborted: {reason}",
                details={"video_path": str(video_path), "job_id": job_id, "rejection_reason": reason},
            )

    def upload_reel_direct(
        self,
        video_path: Path,
        caption: str,
        min_size_bytes: int = 250,
        validation_report: Optional[ValidationReport] = None,
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Uploads a Reel directly using Instagram account credentials.
        No Meta Developer App needed.
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Hard Upload Quality Gate: strictly verify before any upload
        self.enforce_hard_upload_gate(video_path, validation_report=validation_report, job_id=job_id)

        # Pre-publish content and media validation gate
        val_report = PrePublishValidator.validate_reel(video_path, caption, min_size_bytes=min_size_bytes)
        if not val_report.is_valid:
            val_report.raise_if_invalid()

        print(f"\n[INSTAGRAM DIRECT] Uploading Reel directly: {video_path.name}...")
        
        # 1. Guarantee video metadata is sanitized with standard faststart headers
        try:
            from app.video.cinematic_composer import sanitize_video_metadata
            video_path = sanitize_video_metadata(video_path)
        except Exception as e:
            logger.warning(f"Could not sanitize video metadata: {e}")

        cl = self._init_direct_client()

        # 2. Upload clip with capped retries and reconciliation protection
        max_retries = 3
        media = None
        for attempt in range(1, max_retries + 1):
            try:
                media = cl.clip_upload(
                    path=str(video_path),
                    caption=caption,
                )
                break
            except Exception as exc:
                exc_str = str(exc).lower()
                if "please wait" in exc_str or "few minutes" in exc_str or "rate limit" in exc_str:
                    logger.warning(f"[INSTAGRAM DIRECT] Rate limit detected (attempt {attempt}/{max_retries}): {exc}")
                    if attempt >= max_retries:
                        raise PublishingRateLimitError(f"Direct Instagram rate limit: {exc}")
                    time.sleep(5.0 * attempt)
                elif "login" in exc_str or "checkpoint" in exc_str or "challenge" in exc_str:
                    raise PublishingAuthError(f"Direct Instagram authentication failure: {exc}")
                else:
                    logger.warning(f"[INSTAGRAM DIRECT] Upload notice (attempt {attempt}/{max_retries}): {exc}")
                    # Reconciliation probe: check if clip was actually posted on Instagram
                    try:
                        clips = cl.user_clips(cl.user_id, amount=1)
                        if clips and (caption[:30].strip().lower() in (getattr(clips[0], "caption_text", "") or "").lower()):
                            logger.info(f"[INSTAGRAM DIRECT] Reconciliation match found clip {clips[0].code}!")
                            media = clips[0]
                            break
                    except Exception:
                        pass
                    if attempt >= max_retries:
                        raise PublishingNetworkError(f"Direct upload failed after {max_retries} attempts: {exc}")
                    time.sleep(2.0 * attempt)

        media_id = getattr(media, "id", str(media.pk if hasattr(media, "pk") else "uploaded"))
        media_code = getattr(media, "code", "")
        media_url = f"https://www.instagram.com/reel/{media_code}/" if media_code else ""

        print(f"\n[INSTAGRAM DIRECT] SUCCESS! Reel uploaded successfully!")
        if media_url:
            print(f"Reel Link: {media_url}")

        return {
            "success": True,
            "method": "DIRECT_INSTAGRAPI",
            "media_id": str(media_id),
            "media_code": media_code,
            "media_url": media_url,
            "status": "PUBLISHED_VERIFIED",
            "publishing_outcome": "PUBLISHED_VERIFIED",
        }

    # -----------------------------------------------------------------------
    # METHOD 2: OFFICIAL META GRAPH API (RESUMABLE UPLOAD)
    # -----------------------------------------------------------------------
    def upload_reel_resumable(
        self,
        video_path: Path,
        caption: str,
        share_to_feed: bool = True,
        max_poll_seconds: int = 180,
        validation_report: Optional[ValidationReport] = None,
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Uploads an MP4 video directly to Instagram using the official Resumable Upload API.
        Streams video bytes directly to Meta servers via MetaInstagramClient.
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Hard Upload Quality Gate: strictly verify before any upload
        self.enforce_hard_upload_gate(video_path, validation_report=validation_report, job_id=job_id)

        if not self.has_graph_credentials():
            raise PublishingAuthError(
                "Instagram credentials missing. Set INSTAGRAM_USER_ID and INSTAGRAM_ACCESS_TOKEN in .env"
            )

        # Pre-publish validation
        val_report = PrePublishValidator.validate_reel(video_path, caption, min_size_bytes=250)
        if not val_report.is_valid:
            val_report.raise_if_invalid()

        from app.instagram.meta_graph_api import MetaInstagramClient
        client = MetaInstagramClient(
            instagram_account_id=self.user_id,
            access_token=self.access_token,
        )

        res = client.publish_reel_resumable(
            video_path=video_path,
            caption=caption,
            share_to_feed=share_to_feed,
            max_poll_seconds=max_poll_seconds,
        )

        media_id = res.get("media_id")
        permalink = res.get("permalink", f"https://www.instagram.com/reel/{media_id}" if media_id else "")
        return {
            "success": True,
            "method": "GRAPH_API_RESUMABLE",
            "media_id": str(media_id) if media_id else None,
            "container_id": res.get("container_id", ""),
            "media_url": permalink,
            "permalink": permalink,
            "status": "PUBLISHED_VERIFIED",
            "publishing_outcome": "PUBLISHED_VERIFIED",
            "reconciled": res.get("reconciled", False),
        }

    # -----------------------------------------------------------------------
    # METHOD 3: UNIFIED DISPATCHER & DRY-RUN MODE
    # -----------------------------------------------------------------------
    def upload_reel(
        self,
        video_path: Path,
        caption: str,
        force_dry_run: bool = False,
        validation_report: Optional[ValidationReport] = None,
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Unified upload dispatcher. Automatically chooses between:
        1. Official Meta Graph API (preferred for production)
        2. Direct account upload (instagrapi)
        3. Dry-Run Preview
        """
        # Hard Upload Quality Gate: strictly verify before any upload or dry-run dispatch
        self.enforce_hard_upload_gate(video_path, validation_report=validation_report, job_id=job_id)

        if force_dry_run:
            return self.dry_run_preview(video_path, caption, validation_report=validation_report, job_id=job_id)

        if not self.has_credentials():
            raise PublishingConfigError(
                "No Instagram credentials configured. Set INSTAGRAM_USER_ID & INSTAGRAM_ACCESS_TOKEN (Graph API) "
                "or INSTAGRAM_USERNAME & INSTAGRAM_PASSWORD / INSTAGRAM_SESSION_DATA (Direct)."
            )

        method = self.get_preferred_method()
        if method == "graph_api":
            return self.upload_reel_resumable(video_path, caption, validation_report=validation_report, job_id=job_id)
        elif method == "direct":
            return self.upload_reel_direct(video_path, caption, validation_report=validation_report, job_id=job_id)
        else:
            return self.dry_run_preview(video_path, caption, validation_report=validation_report, job_id=job_id)

    def dry_run_preview(
        self,
        video_path: Path,
        caption: str,
        validation_report: Optional[ValidationReport] = None,
        job_id: Optional[str] = None,
        require_validation: bool = False,
    ) -> Dict[str, Any]:
        """
        Validate video and caption locally without uploading to Instagram.
        Generates manifest and validation report.
        """
        video_path = Path(video_path)
        exists = video_path.exists()
        file_size_mb = video_path.stat().st_size / (1024 * 1024) if exists else 0.0

        # Hard Upload Quality Gate: verify if validation report supplied or explicitly required
        if require_validation or validation_report is not None:
            self.enforce_hard_upload_gate(video_path, validation_report=validation_report, job_id=job_id)

        has_caption = bool(caption and caption.strip())
        caption_len = len(caption) if caption else 0

        manifest = {
            "mode": "DRY_RUN",
            "status": "DRY_RUN",
            "publishing_outcome": "DRY_RUN",
            "success": True,
            "video_path": str(video_path),
            "video_exists": exists,
            "file_size_mb": round(file_size_mb, 2),
            "video_specs_valid": exists and file_size_mb > 0.1 and file_size_mb < 300,
            "caption": caption,
            "caption_length": caption_len,
            "caption_within_limit": caption_len <= 2200,
            "credentials_configured": self.has_credentials(),
            "detected_upload_method": self.get_preferred_method() if self.has_credentials() else "dry_run",
            "validation_report": validation_report.to_dict() if validation_report else None,
            "job_id": job_id,
        }

        manifest_file = OUTPUT_DIR / "latest_upload_manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        return manifest

    def verify_credentials(self) -> Dict[str, Any]:
        """Verify credential setup and report available methods."""
        direct_ok = self.has_direct_credentials()
        graph_ok = self.has_graph_credentials()

        return {
            "direct_login_configured": direct_ok,
            "username": self.username if direct_ok else None,
            "graph_api_configured": graph_ok,
            "user_id": self.user_id if graph_ok else None,
            "preferred_method": self.get_preferred_method(),
        }


def upload_or_preview_reel(
    video_path: Path,
    caption: str,
    force_dry_run: bool = False,
    validation_report: Optional[ValidationReport] = None,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Convenience wrapper for Instagram publishing."""
    uploader = InstagramUploader()
    return uploader.upload_reel(
        video_path=video_path,
        caption=caption,
        force_dry_run=force_dry_run,
        validation_report=validation_report,
        job_id=job_id,
    )


if __name__ == "__main__":
    uploader = InstagramUploader()
    status = uploader.verify_credentials()
    print("Instagram Publishing Configuration Status:", status)
