"""
Local Filesystem Storage Adapter.

Stores files locally and serves them via FastAPI's static file mount.
Used for local development, staging, and environments with a reverse proxy or tunnel.
"""

from __future__ import annotations

import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

from app.storage.base import StorageAdapter

logger = logging.getLogger(__name__)

DEFAULT_UPLOAD_DIR = Path("storage") / "public" / "uploads"


class LocalStorageAdapter(StorageAdapter):
    """
    Saves files locally and generates URLs reachable via FastAPI static mount.
    """

    def __init__(
        self,
        base_dir: Optional[Path | str] = None,
        base_url: Optional[str] = None,
    ):
        self.base_dir = Path(base_dir or os.getenv("STORAGE_LOCAL_DIR", DEFAULT_UPLOAD_DIR)).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        # Base URL for serving media publicly (e.g. https://api.instaagent.com or http://localhost:8000)
        self.base_url = (base_url or os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")).rstrip("/")

    def upload_file(self, local_path: Path | str, remote_key: Optional[str] = None) -> str:
        src = Path(local_path).resolve()
        if not src.exists() or not src.is_file():
            raise FileNotFoundError(f"Local file '{src}' does not exist.")

        key = remote_key or f"{uuid.uuid4().hex[:12]}_{src.name}"
        # Prevent directory traversal attacks
        safe_key = Path(key).name
        dest = self.base_dir / safe_key

        shutil.copy2(src, dest)
        logger.info(f"LocalStorageAdapter: Copied {src.name} -> {dest}")
        return self.get_url(safe_key)

    def get_url(self, remote_key: str) -> str:
        safe_key = Path(remote_key).name
        return f"{self.base_url}/static/uploads/{safe_key}"

    def delete_file(self, remote_key: str) -> bool:
        safe_key = Path(remote_key).name
        target = self.base_dir / safe_key
        if target.exists() and target.is_file():
            try:
                target.unlink()
                logger.info(f"LocalStorageAdapter: Deleted {safe_key}")
                return True
            except OSError as exc:
                logger.warning(f"LocalStorageAdapter: Failed to delete {safe_key}: {exc}")
                return False
        return False
