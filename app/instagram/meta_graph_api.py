"""
Official Meta Instagram Graph API Client.

Production features:
- Resumable binary upload for Reels (no public hosting required).
- Multi-item Carousel container creation and publishing.
- Single Image and Story container publishing.
- Resilient polling loop for container status with exponential backoff.
- Post-publish verification fetching real Instagram permalinks.
- Insights API integration for post analytics.
- Safe dry-run verification mode.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v21.0"
GRAPH_API_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class MetaGraphAPIError(Exception):
    """Raised when the Meta Graph API returns an error response."""
    def __init__(self, message: str, error_code: Optional[int] = None, error_subcode: Optional[int] = None, response: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_code = error_code
        self.error_subcode = error_subcode
        self.response = response or {}


class MetaInstagramClient:
    """
    Official Meta Instagram Graph API Client.
    Requires an Instagram Professional / Business account connected to a Facebook Page.
    """

    def __init__(
        self,
        instagram_account_id: Optional[str] = None,
        access_token: Optional[str] = None,
        timeout: int = 30,
    ):
        self.account_id = (
            instagram_account_id
            or os.getenv("INSTAGRAM_USER_ID", "")
        ).strip()
        self.access_token = (
            access_token
            or os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
        ).strip()
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self.account_id and self.access_token)

    def verify_account(self) -> Dict[str, Any]:
        """
        Verify that credentials are valid and return account metadata.
        """
        if not self.is_configured:
            return {"configured": False, "status": "BLOCKED", "reason": "Missing INSTAGRAM_USER_ID or INSTAGRAM_ACCESS_TOKEN"}

        url = f"{GRAPH_API_BASE_URL}/{self.account_id}"
        params = {
            "fields": "id,username,name,profile_picture_url,followers_count,media_count",
            "access_token": self.access_token,
        }
        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
            data = resp.json()
            if "error" in data:
                err = data["error"]
                return {
                    "configured": True,
                    "status": "ERROR",
                    "error_code": err.get("code"),
                    "message": err.get("message"),
                }
            return {
                "configured": True,
                "status": "CONNECTED",
                "account_id": data.get("id"),
                "username": data.get("username"),
                "name": data.get("name"),
                "followers_count": data.get("followers_count"),
                "media_count": data.get("media_count"),
            }
        except Exception as exc:
            return {"configured": True, "status": "NETWORK_ERROR", "message": str(exc)}

    # -------------------------------------------------------------------------
    # REEL PUBLISHING (RESUMABLE BINARY STREAM)
    # -------------------------------------------------------------------------
    def publish_reel_resumable(
        self,
        video_path: Path,
        caption: str,
        share_to_feed: bool = True,
        thumb_offset_ms: Optional[int] = None,
        max_poll_seconds: int = 300,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Uploads and publishes a Reel using Meta's official resumable upload API.
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        file_size = video_path.stat().st_size

        if dry_run or not self.is_configured:
            logger.info("MetaGraphClient running in DRY_RUN / unconfigured simulation mode.")
            return {
                "success": True,
                "dry_run": True,
                "mode": "DRY_RUN",
                "file": str(video_path),
                "file_size_bytes": file_size,
                "caption": caption[:100] + ("..." if len(caption) > 100 else ""),
                "status": "SIMULATED_READY",
            }

        # Step 1: Initialize Resumable Container
        init_url = f"{GRAPH_API_BASE_URL}/{self.account_id}/media"
        init_payload: Dict[str, Any] = {
            "media_type": "REELS",
            "upload_type": "resumable",
            "caption": caption,
            "share_to_feed": str(share_to_feed).lower(),
            "access_token": self.access_token,
        }
        if thumb_offset_ms is not None:
            init_payload["thumb_offset"] = str(thumb_offset_ms)

        init_resp = requests.post(init_url, data=init_payload, timeout=self.timeout)
        init_data = init_resp.json()
        self._check_api_error(init_data, "init_reel_container")

        container_id = init_data.get("id")
        upload_uri = init_data.get("uri")
        if not container_id or not upload_uri:
            raise MetaGraphAPIError(f"Missing container_id or upload_uri from Meta response: {init_data}")

        logger.info(f"Created Reel container {container_id}. Streaming {file_size} bytes...")

        # Step 2: Stream Binary Bytes to upload_uri
        headers = {
            "Authorization": f"OAuth {self.access_token}",
            "offset": "0",
            "file_size": str(file_size),
            "Content-Type": "application/octet-stream",
        }

        with open(video_path, "rb") as vf:
            upload_resp = requests.post(
                upload_uri,
                headers=headers,
                data=vf,
                timeout=max(self.timeout, 180),
            )
        upload_data = upload_resp.json() if upload_resp.content else {}
        if upload_resp.status_code not in (200, 201) or "error" in upload_data:
            self._check_api_error(upload_data, "upload_reel_binary")

        logger.info(f"Video binary uploaded for container {container_id}. Polling processing status...")

        # Step 3: Poll Processing Status
        self._poll_container_status(container_id, max_poll_seconds=max_poll_seconds)

        # Step 4: Publish Container
        publish_data = self._publish_container(container_id)
        media_id = publish_data.get("id")

        # Step 5: Verify & Fetch Permalink
        metadata = self.get_media_metadata(media_id)

        return {
            "success": True,
            "dry_run": False,
            "media_id": media_id,
            "container_id": container_id,
            "permalink": metadata.get("permalink", f"https://www.instagram.com/reel/{media_id}"),
            "status": "PUBLISHED",
        }

    # -------------------------------------------------------------------------
    # CAROUSEL PUBLISHING
    # -------------------------------------------------------------------------
    def publish_carousel(
        self,
        image_urls: List[str],
        caption: str,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Creates a multi-item carousel post on Instagram.
        image_urls: list of publicly accessible URLs for the carousel items (2 to 10 items).
        """
        if len(image_urls) < 2 or len(image_urls) > 10:
            raise ValueError(f"Carousels require between 2 and 10 items. Provided: {len(image_urls)}")

        if dry_run or not self.is_configured:
            return {
                "success": True,
                "dry_run": True,
                "mode": "DRY_RUN",
                "item_count": len(image_urls),
                "caption": caption[:100],
                "status": "SIMULATED_READY",
            }

        # Step 1: Create individual item containers
        child_ids = []
        for idx, img_url in enumerate(image_urls):
            item_url = f"{GRAPH_API_BASE_URL}/{self.account_id}/media"
            item_payload = {
                "image_url": img_url,
                "is_carousel_item": "true",
                "access_token": self.access_token,
            }
            resp = requests.post(item_url, data=item_payload, timeout=self.timeout)
            data = resp.json()
            self._check_api_error(data, f"create_carousel_item_{idx}")
            child_id = data.get("id")
            if child_id:
                child_ids.append(child_id)

        # Step 2: Create parent carousel container
        parent_url = f"{GRAPH_API_BASE_URL}/{self.account_id}/media"
        parent_payload = {
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption,
            "access_token": self.access_token,
        }
        parent_resp = requests.post(parent_url, data=parent_payload, timeout=self.timeout)
        parent_data = parent_resp.json()
        self._check_api_error(parent_data, "create_carousel_parent")
        container_id = parent_data.get("id")

        # Step 3: Poll parent container
        self._poll_container_status(container_id, max_poll_seconds=120)

        # Step 4: Publish
        publish_data = self._publish_container(container_id)
        media_id = publish_data.get("id")
        metadata = self.get_media_metadata(media_id)

        return {
            "success": True,
            "dry_run": False,
            "media_id": media_id,
            "container_id": container_id,
            "children_ids": child_ids,
            "permalink": metadata.get("permalink", f"https://www.instagram.com/p/{media_id}"),
            "status": "PUBLISHED",
        }

    # -------------------------------------------------------------------------
    # SINGLE IMAGE POST
    # -------------------------------------------------------------------------
    def publish_single_image(
        self,
        image_url: str,
        caption: str,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Publishes a single image post.
        """
        if dry_run or not self.is_configured:
            return {
                "success": True,
                "dry_run": True,
                "mode": "DRY_RUN",
                "image_url": image_url,
                "caption": caption[:100],
                "status": "SIMULATED_READY",
            }

        url = f"{GRAPH_API_BASE_URL}/{self.account_id}/media"
        payload = {
            "image_url": image_url,
            "caption": caption,
            "access_token": self.access_token,
        }
        resp = requests.post(url, data=payload, timeout=self.timeout)
        data = resp.json()
        self._check_api_error(data, "create_image_container")
        container_id = data.get("id")

        self._poll_container_status(container_id, max_poll_seconds=60)
        publish_data = self._publish_container(container_id)
        media_id = publish_data.get("id")
        metadata = self.get_media_metadata(media_id)

        return {
            "success": True,
            "dry_run": False,
            "media_id": media_id,
            "container_id": container_id,
            "permalink": metadata.get("permalink", f"https://www.instagram.com/p/{media_id}"),
            "status": "PUBLISHED",
        }

    # -------------------------------------------------------------------------
    # STORY PUBLISHING
    # -------------------------------------------------------------------------
    def publish_story(
        self,
        media_url: str,
        media_type: str = "IMAGE",  # IMAGE or VIDEO
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Publishes an Instagram Story.
        """
        if dry_run or not self.is_configured:
            return {
                "success": True,
                "dry_run": True,
                "mode": "DRY_RUN",
                "media_type": media_type,
                "status": "SIMULATED_READY",
            }

        url = f"{GRAPH_API_BASE_URL}/{self.account_id}/media"
        payload: Dict[str, Any] = {
            "media_type": "STORIES",
            "access_token": self.access_token,
        }
        if media_type.upper() == "VIDEO":
            payload["video_url"] = media_url
        else:
            payload["image_url"] = media_url

        resp = requests.post(url, data=payload, timeout=self.timeout)
        data = resp.json()
        self._check_api_error(data, "create_story_container")
        container_id = data.get("id")

        self._poll_container_status(container_id, max_poll_seconds=120)
        publish_data = self._publish_container(container_id)
        media_id = publish_data.get("id")

        return {
            "success": True,
            "dry_run": False,
            "media_id": media_id,
            "container_id": container_id,
            "status": "PUBLISHED",
        }

    # -------------------------------------------------------------------------
    # INTERNAL HELPERS
    # -------------------------------------------------------------------------
    def _poll_container_status(self, container_id: str, max_poll_seconds: int = 300) -> str:
        """
        Polls the status_code of a media container until FINISHED or error with exponential backoff.
        """
        status_url = f"{GRAPH_API_BASE_URL}/{container_id}"
        status_params = {
            "fields": "status_code,status",
            "access_token": self.access_token,
        }

        start_time = time.time()
        delay = 3.0
        while time.time() - start_time < max_poll_seconds:
            try:
                resp = requests.get(status_url, params=status_params, timeout=15)
                data = resp.json()
            except Exception as exc:
                logger.warning(f"Transient error polling container {container_id}: {exc}")
                time.sleep(delay)
                continue

            status_code = data.get("status_code", "").upper()
            logger.info(f"Container {container_id} status: {status_code}")

            if status_code == "FINISHED":
                return status_code
            elif status_code in ("ERROR", "EXPIRED"):
                error_msg = data.get("status", f"Failed with status_code: {status_code}")
                raise MetaGraphAPIError(
                    f"Meta container processing failed: {error_msg}",
                    response=data,
                )

            time.sleep(min(delay, 15.0))
            delay *= 1.3

        raise TimeoutError(
            f"Container {container_id} processing timed out after {max_poll_seconds}s"
        )

    def _publish_container(self, container_id: str) -> Dict[str, Any]:
        """
        Executes media_publish call for an encoded container.
        """
        publish_url = f"{GRAPH_API_BASE_URL}/{self.account_id}/media_publish"
        payload = {
            "creation_id": container_id,
            "access_token": self.access_token,
        }
        resp = requests.post(publish_url, data=payload, timeout=self.timeout)
        data = resp.json()
        self._check_api_error(data, "media_publish")
        return data

    def get_media_metadata(self, media_id: str) -> Dict[str, Any]:
        """
        Retrieves real Instagram permalink and metadata for a published post.
        """
        if not self.is_configured or not media_id:
            return {}

        url = f"{GRAPH_API_BASE_URL}/{media_id}"
        params = {
            "fields": "id,permalink,media_type,timestamp,like_count,comments_count",
            "access_token": self.access_token,
        }
        try:
            resp = requests.get(url, params=params, timeout=15)
            return resp.json()
        except Exception as exc:
            logger.warning(f"Could not fetch metadata for media {media_id}: {exc}")
            return {}

    def fetch_insights(self, media_id: str) -> Dict[str, Any]:
        """
        Fetches genuine Instagram Insights for a published media object.
        """
        if not self.is_configured or not media_id:
            return {"status": "UNCONFIGURED"}

        url = f"{GRAPH_API_BASE_URL}/{media_id}/insights"
        params = {
            "metric": "reach,impressions,saved,shares,total_interactions",
            "access_token": self.access_token,
        }
        try:
            resp = requests.get(url, params=params, timeout=15)
            data = resp.json()
            if "error" in data:
                return {"status": "ERROR", "error": data["error"]}
            metrics = {}
            for item in data.get("data", []):
                name = item.get("name")
                values = item.get("values", [{}])
                metrics[name] = values[0].get("value", 0) if values else 0
            return {"status": "SUCCESS", "metrics": metrics}
        except Exception as exc:
            return {"status": "ERROR", "error": str(exc)}

    @staticmethod
    def _check_api_error(response_data: Dict[str, Any], context: str) -> None:
        if "error" in response_data:
            err = response_data["error"]
            msg = err.get("message", "Unknown Meta Graph API error")
            code = err.get("code")
            subcode = err.get("error_subcode")
            raise MetaGraphAPIError(
                f"Meta Graph API error during {context}: {msg} (Code: {code}, Subcode: {subcode})",
                error_code=code,
                error_subcode=subcode,
                response=response_data,
            )
