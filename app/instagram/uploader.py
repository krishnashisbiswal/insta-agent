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
    PublishingAuthError,
    PublishingConfigError,
    PublishingNetworkError,
    PublishingRateLimitError,
    PublishingUncertainOutcomeError,
    PublishingValidationError,
)
from app.publishing.state_machine import compute_video_fingerprint
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
        self._instagrapi_client = None

    def has_direct_credentials(self) -> bool:
        """Check if Direct Instagram account credentials or session are configured."""
        has_session = bool(self.session_id or self.session_data or IG_SESSION_FILE.exists())
        return bool((self.username and self.password) or has_session)

    def has_graph_credentials(self) -> bool:
        """Check if Meta Graph API credentials are configured."""
        return bool(self.user_id and self.access_token)

    def has_credentials(self) -> bool:
        """Check if any publishing credentials exist."""
        return self.has_direct_credentials() or self.has_graph_credentials()

    def get_preferred_method(self) -> str:
        """Determine whether to use direct instagrapi or official Graph API."""
        if INSTAGRAM_UPLOAD_METHOD == "direct" and self.has_direct_credentials():
            return "direct"
        if INSTAGRAM_UPLOAD_METHOD == "graph_api" and self.has_graph_credentials():
            return "graph_api"
        # Auto-detect: prefer direct if username/password is present, otherwise graph_api
        if self.has_direct_credentials():
            return "direct"
        if self.has_graph_credentials():
            return "graph_api"
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
        if session_data_env and (not IG_SESSION_FILE.exists() or IG_SESSION_FILE.stat().st_size == 0):
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
                IG_SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
                IG_SESSION_FILE.write_text(raw_json, encoding="utf-8")
                print(f"[INSTAGRAM DIRECT] Restored session file from INSTAGRAM_SESSION_DATA.")
            except Exception as e:
                logger.warning(f"Failed restoring session data: {e}")

        # Try to reuse saved session if available
        if IG_SESSION_FILE.exists():
            try:
                print(f"[INSTAGRAM DIRECT] Loading saved session from {IG_SESSION_FILE.name}...")
                cl.load_settings(str(IG_SESSION_FILE))
                # Validate if loaded session is still active
                try:
                    cl.get_timeline_feed()
                    print(f"[INSTAGRAM DIRECT] Saved session is valid and active!")
                    self._instagrapi_client = cl
                    return cl
                except Exception:
                    print("[INSTAGRAM DIRECT] Cached session expired. Re-authenticating with credentials...")
                    if self.username and self.password:
                        cl.login(self.username, self.password)
                        cl.dump_settings(str(IG_SESSION_FILE))
                        self._instagrapi_client = cl
                        return cl
            except Exception as exc:
                logger.warning(f"Could not reuse session file: {exc}. Logging in fresh...")

        # Login with session ID if provided
        if self.session_id:
            print("[INSTAGRAM DIRECT] Authenticating via session ID...")
            cl.login_by_sessionid(self.session_id)
        elif self.username and self.password:
            print(f"[INSTAGRAM DIRECT] Authenticating @{self.username}...")
            cl.login(self.username, self.password)
        else:
            raise RuntimeError(
                "Missing valid Instagram credentials. Provide INSTAGRAM_SESSION_DATA, INSTAGRAM_SESSION_ID, "
                "or INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in .env or GitHub Secrets"
            )

        # Save session to avoid repeated logins
        try:
            IG_SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
            cl.dump_settings(str(IG_SESSION_FILE))
            print(f"[INSTAGRAM DIRECT] Session cached to {IG_SESSION_FILE.name}")
        except Exception as exc:
            logger.warning(f"Failed to cache session: {exc}")

        self._instagrapi_client = cl
        return cl

    def upload_reel_direct(
        self,
        video_path: Path,
        caption: str,
        min_size_bytes: int = 250,
    ) -> Dict[str, Any]:
        """
        Uploads a Reel directly using Instagram account credentials.
        No Meta Developer App needed.
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

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
            "media_id": media_id,
            "media_code": media_code,
            "media_url": media_url,
            "status": "PUBLISHED",
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
    ) -> Dict[str, Any]:
        """
        Uploads an MP4 video directly to Instagram using the official Resumable Upload API.
        Streams video bytes directly to Meta servers via MetaInstagramClient.
        """
        if not self.has_graph_credentials():
            raise PublishingAuthError(
                "Instagram credentials missing. Set INSTAGRAM_USER_ID and INSTAGRAM_ACCESS_TOKEN in .env"
            )

        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Pre-publish validation
        val_report = PrePublishValidator.validate_reel(video_path, caption, min_size_bytes=250)
        if not val_report.is_valid:
            val_report.raise_if_invalid()

        from app.instagram.meta_graph_api import MetaInstagramClient
        client = MetaInstagramClient(
            instagram_account_id=self.user_id,
            access_token=self.access_token,
        )

        return client.publish_reel_resumable(
            video_path=video_path,
            caption=caption,
            share_to_feed=share_to_feed,
            max_poll_seconds=max_poll_seconds,
        )

    # -----------------------------------------------------------------------
    # METHOD 3: UNIFIED DISPATCHER & DRY-RUN MODE
    # -----------------------------------------------------------------------
    def upload_reel(
        self,
        video_path: Path,
        caption: str,
        force_dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Unified upload dispatcher. Automatically chooses between:
        1. Direct account upload (instagrapi)
        2. Official Meta Graph API
        3. Dry-Run Preview
        """
        if force_dry_run or not self.has_credentials():
            return self.dry_run_preview(video_path, caption)

        method = self.get_preferred_method()
        if method == "direct":
            return self.upload_reel_direct(video_path, caption)
        elif method == "graph_api":
            return self.upload_reel_resumable(video_path, caption)
        else:
            return self.dry_run_preview(video_path, caption)

    def dry_run_preview(
        self,
        video_path: Path,
        caption: str,
    ) -> Dict[str, Any]:
        """
        Validate video and caption locally without uploading to Instagram.
        Generates manifest and validation report.
        """
        video_path = Path(video_path)
        exists = video_path.exists()
        file_size_mb = video_path.stat().st_size / (1024 * 1024) if exists else 0.0

        has_caption = bool(caption and caption.strip())
        caption_len = len(caption) if caption else 0

        manifest = {
            "mode": "DRY_RUN",
            "video_path": str(video_path),
            "video_exists": exists,
            "file_size_mb": round(file_size_mb, 2),
            "video_specs_valid": exists and file_size_mb > 0.1 and file_size_mb < 300,
            "caption": caption,
            "caption_length": caption_len,
            "caption_within_limit": caption_len <= 2200,
            "credentials_configured": self.has_credentials(),
            "detected_upload_method": self.get_preferred_method(),
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
) -> Dict[str, Any]:
    """Convenience wrapper for Instagram publishing."""
    uploader = InstagramUploader()
    return uploader.upload_reel(video_path, caption, force_dry_run=force_dry_run)


if __name__ == "__main__":
    uploader = InstagramUploader()
    status = uploader.verify_credentials()
    print("Instagram Publishing Configuration Status:", status)
