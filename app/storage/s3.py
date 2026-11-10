"""
Cloud Object Storage Adapter (AWS S3, Cloudflare R2, MinIO, Wasabi).

Uses boto3 client for uploading media assets to public cloud buckets
and generating direct HTTPS URLs for Meta Instagram Graph API consumption.
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Optional

from app.storage.base import StorageAdapter

logger = logging.getLogger(__name__)


class S3StorageAdapter(StorageAdapter):
    """
    S3-compatible cloud storage adapter.
    Supports AWS S3, Cloudflare R2, MinIO, and other S3-compatible APIs.
    """

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        public_url_prefix: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: Optional[str] = None,
    ):
        try:
            import boto3
            from botocore.config import Config
        except ImportError:
            raise ImportError(
                "boto3 is required for S3StorageAdapter. Install it via 'pip install boto3'."
            )

        self.bucket_name = bucket_name or os.getenv("S3_BUCKET_NAME", "")
        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME is required for S3StorageAdapter")

        self.endpoint_url = endpoint_url or os.getenv("S3_ENDPOINT_URL")
        self.public_url_prefix = (
            public_url_prefix or os.getenv("S3_PUBLIC_URL_PREFIX") or ""
        ).rstrip("/")
        self.region_name = region_name or os.getenv("AWS_DEFAULT_REGION", "us-east-1")

        self.client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=self.region_name,
            config=Config(signature_version="s3v4"),
        )

    def upload_file(self, local_path: Path | str, remote_key: Optional[str] = None) -> str:
        src = Path(local_path).resolve()
        if not src.exists():
            raise FileNotFoundError(f"Local file '{src}' does not exist.")

        key = remote_key or f"media/{uuid.uuid4().hex[:12]}_{src.name}"

        # Determine MIME content type
        content_type = "application/octet-stream"
        suffix = src.suffix.lower()
        if suffix in (".jpg", ".jpeg"):
            content_type = "image/jpeg"
        elif suffix == ".png":
            content_type = "image/png"
        elif suffix == ".mp4":
            content_type = "video/mp4"

        try:
            self.client.upload_file(
                Filename=str(src),
                Bucket=self.bucket_name,
                Key=key,
                ExtraArgs={"ContentType": content_type, "ACL": "public-read"},
            )
            logger.info(f"S3StorageAdapter: Uploaded {src.name} to {self.bucket_name}/{key}")
            return self.get_url(key)
        except Exception as exc:
            logger.error(f"S3StorageAdapter: Upload failed: {exc}")
            raise

    def get_url(self, remote_key: str) -> str:
        if self.public_url_prefix:
            return f"{self.public_url_prefix}/{remote_key}"
        if self.endpoint_url:
            return f"{self.endpoint_url.rstrip('/')}/{self.bucket_name}/{remote_key}"
        return f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com/{remote_key}"

    def delete_file(self, remote_key: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=remote_key)
            return True
        except Exception as exc:
            logger.warning(f"S3StorageAdapter: Failed to delete {remote_key}: {exc}")
            return False
