"""
Storage Package for Media Uploads and CDN/S3 URL Generation.
"""

from __future__ import annotations

import os
from typing import Optional

from app.storage.base import StorageAdapter
from app.storage.local import LocalStorageAdapter

_adapter: Optional[StorageAdapter] = None


def get_storage_adapter() -> StorageAdapter:
    """
    Returns configured storage adapter based on STORAGE_BACKEND environment variable.
    Options:
    - 'local' (default): Serves files locally via FastAPI /static/ mount.
    - 's3': Uploads files to AWS S3, Cloudflare R2, MinIO, etc.
    """
    global _adapter
    if _adapter is not None:
        return _adapter

    backend = os.getenv("STORAGE_BACKEND", "local").strip().lower()

    if backend == "s3":
        from app.storage.s3 import S3StorageAdapter
        _adapter = S3StorageAdapter()
    else:
        _adapter = LocalStorageAdapter()

    return _adapter


__all__ = [
    "StorageAdapter",
    "LocalStorageAdapter",
    "get_storage_adapter",
]
