"""
Tests for Instagram session credential handling and auto-restoration.
Ensures GitHub Actions runner and cloud containers seamlessly authenticate
via INSTAGRAM_SESSION_DATA even when no raw password is provided.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.instagram.uploader import InstagramUploader
from config.settings import STORAGE_DIR


def test_has_direct_credentials_with_session_data(monkeypatch):
    uploader = InstagramUploader(
        username="testuser",
        password="",
        session_id="",
        session_data='{"sessionid": "mock_cookie_val"}',
        user_id="",
        access_token="",
    )
    assert uploader.has_direct_credentials() is True
    assert uploader.get_preferred_method() == "direct"


def test_has_direct_credentials_with_session_id(monkeypatch):
    uploader = InstagramUploader(
        username="testuser",
        password="",
        session_id="mock_session_id_123",
        session_data="",
        user_id="",
        access_token="",
    )
    assert uploader.has_direct_credentials() is True
    assert uploader.get_preferred_method() == "direct"


def test_has_direct_credentials_fallback_to_dry_run_when_empty(monkeypatch, tmp_path):
    fake_session_file = tmp_path / "non_existent_session.json"
    with patch("app.instagram.uploader.IG_SESSION_FILE", fake_session_file):
        uploader = InstagramUploader(
            username="",
            password="",
            session_id="",
            session_data="",
            user_id="",
            access_token="",
        )
        assert uploader.has_direct_credentials() is False
        assert uploader.get_preferred_method() == "dry_run"


def test_session_data_restores_file(monkeypatch, tmp_path):
    test_session_file = tmp_path / "test_ig_session.json"
    dummy_payload = '{"cookies": {"ds_user_id": "12345"}}'
    monkeypatch.setenv("INSTAGRAM_SESSION_DATA", dummy_payload)

    with patch("app.instagram.uploader.IG_SESSION_FILE", test_session_file):
        with patch("instagrapi.Client") as MockClient:
            mock_instance = MagicMock()
            MockClient.return_value = mock_instance
            mock_instance.get_timeline_feed.return_value = {"status": "ok"}

            uploader = InstagramUploader()
            client = uploader._init_direct_client()
            assert test_session_file.exists()
            assert test_session_file.read_text(encoding="utf-8") == dummy_payload
            mock_instance.load_settings.assert_called_once_with(str(test_session_file))
