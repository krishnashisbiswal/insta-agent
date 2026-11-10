"""
Base Storage Adapter Interface for Insta-Agent.

Enables seamless swapping between local filesystem serving and cloud object storage
(AWS S3, Cloudflare R2, MinIO, Google Cloud Storage) for hosting public media assets
required by Meta Instagram Graph API (carousels, images, and videos).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class StorageAdapter(ABC):
    """Abstract storage adapter interface."""

    @abstractmethod
    def upload_file(self, local_path: Path | str, remote_key: Optional[str] = None) -> str:
        """
        Uploads a local file and returns an HTTPS/public accessible URL.

        :param local_path: Local filesystem path to the file.
        :param remote_key: Optional target key or filename in the bucket/storage.
        :return: Publicly accessible URL string suitable for Meta Graph API.
        """
        pass

    @abstractmethod
    def get_url(self, remote_key: str) -> str:
        """
        Retrieves the public URL for a given remote key.
        """
        pass

    @abstractmethod
    def delete_file(self, remote_key: str) -> bool:
        """
        Deletes a file from storage by key.
        :return: True if successfully deleted, False otherwise.
        """
        pass
