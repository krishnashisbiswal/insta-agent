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

from config.settings import (
    GRAPH_API_BASE_URL,
    IG_SESSION_FILE,
    INSTAGRAM_ACCESS_TOKEN,
    INSTAGRAM_PASSWORD,
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
        user_id: Optional[str] = None,
        access_token: Optional[str] = None,
    ):
        self.username = (username or INSTAGRAM_USERNAME).strip()
        self.password = (password or INSTAGRAM_PASSWORD).strip()
        self.session_id = (session_id or INSTAGRAM_SESSION_ID).strip()
        self.user_id = (user_id or INSTAGRAM_USER_ID).strip()
        self.access_token = (access_token or INSTAGRAM_ACCESS_TOKEN).strip()
        self._instagrapi_client = None

    def has_direct_credentials(self) -> bool:
        """Check if Direct Instagram account credentials are configured."""
        return bool((self.username and self.password) or self.session_id)

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

        # Try to reuse saved session if available
        if IG_SESSION_FILE.exists():
            try:
                print(f"[INSTAGRAM DIRECT] Loading saved session from {IG_SESSION_FILE.name}...")
                cl.load_settings(str(IG_SESSION_FILE))
                cl.login(self.username, self.password)
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
            raise RuntimeError("Missing INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in .env")

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
    ) -> Dict[str, Any]:
        """
        Uploads a Reel directly using Instagram account credentials.
        No Meta Developer App needed.
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        print(f"\n[INSTAGRAM DIRECT] Uploading Reel directly: {video_path.name}...")
        cl = self._init_direct_client()

        # Upload clip as an Instagram Reel
        media = cl.clip_upload(
            path=str(video_path),
            caption=caption,
        )

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
        Streams video bytes directly to Meta servers.
        """
        if not self.has_graph_credentials():
            raise RuntimeError(
                "Instagram credentials missing. Set INSTAGRAM_USER_ID and INSTAGRAM_ACCESS_TOKEN in .env"
            )

        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        file_size = video_path.stat().st_size
        print(f"\n[META GRAPH API] Initializing Reel container for: {video_path.name} ({file_size / (1024*1024):.2f} MB)...")

        # Step 1: Create Resumable Container
        init_url = f"{GRAPH_API_BASE_URL}/{self.user_id}/media"
        init_params = {
            "media_type": "REELS",
            "upload_type": "resumable",
            "caption": caption,
            "share_to_feed": str(share_to_feed).lower(),
            "access_token": self.access_token,
        }

        init_resp = requests.post(init_url, data=init_params, timeout=30)
        init_data = init_resp.json()

        if "error" in init_data:
            err_msg = init_data["error"].get("message", "Container creation error")
            raise RuntimeError(f"Meta Graph API error creating Reel container: {err_msg}")

        container_id = init_data.get("id")
        upload_uri = init_data.get("uri")

        if not container_id or not upload_uri:
            raise RuntimeError(f"Unexpected response from Meta API: {init_data}")

        print(f"[META GRAPH API] Container created (ID: {container_id}). Uploading video binary...")

        # Step 2: Upload Binary Bytes to Upload URI
        headers = {
            "Authorization": f"OAuth {self.access_token}",
            "offset": "0",
            "file_size": str(file_size),
            "Content-Type": "application/octet-stream",
        }

        with open(video_path, "rb") as video_file:
            video_bytes = video_file.read()

        upload_resp = requests.post(upload_uri, headers=headers, data=video_bytes, timeout=120)
        upload_data = upload_resp.json()

        if upload_resp.status_code not in (200, 201) or "error" in upload_data:
            raise RuntimeError(f"Failed to upload video bytes to Meta: {upload_data}")

        print("[META GRAPH API] Video binary uploaded successfully. Waiting for Meta encoding...")

        # Step 3: Poll Container Processing Status
        status_url = f"{GRAPH_API_BASE_URL}/{container_id}"
        status_params = {
            "fields": "status_code,status",
            "access_token": self.access_token,
        }

        start_time = time.time()
        while time.time() - start_time < max_poll_seconds:
            poll_resp = requests.get(status_url, params=status_params, timeout=15)
            poll_data = poll_resp.json()

            status_code = poll_data.get("status_code", "").upper()
            logger.info(f"Container {container_id} status: {status_code}")

            if status_code == "FINISHED":
                print("[META GRAPH API] Processing FINISHED! Publishing Reel...")
                break
            elif status_code in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"Meta processing failed with status: {status_code} ({poll_data})")
            else:
                print(f"[META GRAPH API] Status: {status_code or 'IN_PROGRESS'}... Waiting 5s...")
                time.sleep(5)
        else:
            raise TimeoutError(f"Reel processing timed out after {max_poll_seconds}s for container {container_id}")

        # Step 4: Publish Reel
        publish_url = f"{GRAPH_API_BASE_URL}/{self.user_id}/media_publish"
        publish_params = {
            "creation_id": container_id,
            "access_token": self.access_token,
        }

        publish_resp = requests.post(publish_url, data=publish_params, timeout=30)
        publish_data = publish_resp.json()

        if "error" in publish_data:
            raise RuntimeError(f"Meta error publishing Reel: {publish_data['error']}")

        media_id = publish_data.get("id")
        print(f"\n[META GRAPH API] SUCCESS! Reel published with Media ID: {media_id}")

        return {
            "success": True,
            "method": "GRAPH_API",
            "media_id": media_id,
            "container_id": container_id,
            "status": "PUBLISHED",
        }

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
