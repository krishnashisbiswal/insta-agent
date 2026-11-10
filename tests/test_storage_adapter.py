"""
Storage Adapter Verification Suite.

Tests:
- LocalStorageAdapter file upload and URL generation.
- Public URL format verification.
- Safe file naming and directory traversal protection.
- Deletion of stored assets.
- FastAPI static file serving integration for Meta Graph API ingestion.
"""

from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from app.api.main import app
from app.storage.local import LocalStorageAdapter

client = TestClient(app)


def test_local_storage_adapter_lifecycle(tmp_path):
    storage_dir = tmp_path / "public_uploads"
    adapter = LocalStorageAdapter(base_dir=storage_dir, base_url="https://media.instaagent.com")

    # Create dummy image
    test_file = tmp_path / "carousel_slide_1.jpg"
    test_file.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 256)  # JPEG magic bytes

    # 1. Upload
    url = adapter.upload_file(test_file)
    assert url.startswith("https://media.instaagent.com/static/uploads/")
    assert "carousel_slide_1.jpg" in url

    # 2. File exists in destination directory
    key = url.split("/")[-1]
    dest_file = storage_dir / key
    assert dest_file.exists()
    assert dest_file.read_bytes() == test_file.read_bytes()

    # 3. Delete
    deleted = adapter.delete_file(key)
    assert deleted is True
    assert not dest_file.exists()

    # 4. Deleting non-existent file returns False safely
    assert adapter.delete_file("non_existent_key.jpg") is False


def test_storage_directory_traversal_protection(tmp_path):
    storage_dir = tmp_path / "public_uploads"
    adapter = LocalStorageAdapter(base_dir=storage_dir)

    test_file = tmp_path / "safe.jpg"
    test_file.write_bytes(b"content")

    # Attempting to supply a malicious remote key with directory traversal
    malicious_key = "../../etc/passwd"
    url = adapter.upload_file(test_file, remote_key=malicious_key)

    # Remote key should be sanitized to base filename
    assert "passwd" in url
    assert ".." not in url
    assert not (tmp_path / "etc" / "passwd").exists()
    assert (storage_dir / "passwd").exists()


def test_fastapi_static_file_serving(tmp_path):
    from app.storage.local import DEFAULT_UPLOAD_DIR
    upload_dir = Path(DEFAULT_UPLOAD_DIR).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)

    sample_media = upload_dir / "test_serve_slide.jpg"
    sample_content = b"\xFF\xD8\xFF\xE0MockImagePayload"
    sample_media.write_bytes(sample_content)

    # Request via FastAPI static mount
    resp = client.get("/static/uploads/test_serve_slide.jpg")
    assert resp.status_code == 200
    assert resp.content == sample_content

    # Clean up
    if sample_media.exists():
        sample_media.unlink()
