"""
Tests for Centralized FFmpeg Resolver (app.utils.ffmpeg_resolver).
Validates resolution order, execution validation, caching, environment fallbacks,
error diagnostics, and edge cases across operating systems.
"""

import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.utils import ffmpeg_resolver
from app.utils.ffmpeg_resolver import (
    get_ffmpeg_binary,
    get_ffmpeg_diagnostics,
    get_ffmpeg_version,
    is_ffmpeg_available,
)


@pytest.fixture(autouse=True)
def reset_resolver_cache():
    """Reset the module-level resolver cache before each test."""
    with ffmpeg_resolver._lock:
        ffmpeg_resolver._cached_ffmpeg_binary = None
        ffmpeg_resolver._cached_ffmpeg_version = None
        ffmpeg_resolver._cached_diagnostics = None
    yield
    with ffmpeg_resolver._lock:
        ffmpeg_resolver._cached_ffmpeg_binary = None
        ffmpeg_resolver._cached_ffmpeg_version = None
        ffmpeg_resolver._cached_diagnostics = None


def test_real_environment_ffmpeg_is_available():
    """Verifies that the current test environment successfully resolves a working FFmpeg binary."""
    assert is_ffmpeg_available() is True
    bin_path = get_ffmpeg_binary()
    assert bin_path is not None
    assert Path(bin_path).exists()
    ver = get_ffmpeg_version()
    assert ver is not None
    assert "ffmpeg version" in ver.lower()


def test_explicit_configuration_valid(tmp_path):
    """Priority 1: Explicit valid configured path via FFMPEG_BINARY must take precedence."""
    mock_bin = tmp_path / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    mock_bin.write_text("#!/bin/sh\nexit 0\n")

    with patch.dict(os.environ, {"FFMPEG_BINARY": str(mock_bin)}):
        with patch("app.utils.ffmpeg_resolver._validate_binary", return_value=(True, "ffmpeg version 7.0-test", None)):
            bin_path = get_ffmpeg_binary(force_refresh=True)
            assert bin_path == str(mock_bin.resolve())
            assert get_ffmpeg_version() == "ffmpeg version 7.0-test"


def test_explicit_configuration_invalid_falls_back(tmp_path):
    """Priority 1 fallback: If explicit configured path is invalid, fall back to next candidates."""
    invalid_path = str(tmp_path / "non_existent_ffmpeg_bin")

    with patch.dict(os.environ, {"FFMPEG_BINARY": invalid_path}):
        # Mock _validate_binary so that invalid_path fails, but imageio_ffmpeg succeeds
        def mock_validate(path):
            if path == invalid_path:
                return False, None, "File does not exist"
            return True, "ffmpeg version 9.0-fallback", None

        with patch("app.utils.ffmpeg_resolver._validate_binary", side_effect=mock_validate):
            with patch("shutil.which", return_value=None):
                with patch("imageio_ffmpeg.get_ffmpeg_exe", return_value=str(tmp_path / "valid_imageio_bin")):
                    bin_path = get_ffmpeg_binary(force_refresh=True)
                    assert bin_path == str((tmp_path / "valid_imageio_bin").resolve())


def test_system_ffmpeg_available():
    """Priority 2: System PATH via shutil.which('ffmpeg') when no explicit env var is set."""
    with patch.dict(os.environ, {"FFMPEG_BINARY": "", "FFMPEG_PATH": ""}, clear=False):
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("app.utils.ffmpeg_resolver._validate_binary", return_value=(True, "ffmpeg version 6.1-system", None)):
                bin_path = get_ffmpeg_binary(force_refresh=True)
                assert bin_path == str(Path("/usr/bin/ffmpeg").resolve())


def test_imageio_ffmpeg_fallback_when_system_path_missing(tmp_path):
    """Priority 3: imageio_ffmpeg bundled binary when system PATH is missing."""
    img_bin = str(tmp_path / "bundled_ffmpeg")

    with patch.dict(os.environ, {"FFMPEG_BINARY": "", "FFMPEG_PATH": ""}, clear=False):
        with patch("shutil.which", return_value=None):
            with patch("imageio_ffmpeg.get_ffmpeg_exe", return_value=img_bin):
                with patch("app.utils.ffmpeg_resolver._validate_binary", return_value=(True, "ffmpeg version 9.0-bundled", None)):
                    bin_path = get_ffmpeg_binary(force_refresh=True)
                    assert bin_path == str(Path(img_bin).resolve())


def test_no_ffmpeg_available():
    """When all resolution options fail, returns None and detailed diagnostics."""
    with patch.dict(os.environ, {"FFMPEG_BINARY": "", "FFMPEG_PATH": ""}, clear=False):
        with patch("shutil.which", return_value=None):
            with patch("imageio_ffmpeg.get_ffmpeg_exe", return_value=None):
                with patch("os.path.isfile", return_value=False):
                    bin_path = get_ffmpeg_binary(force_refresh=True)
                    assert bin_path is None
                    assert is_ffmpeg_available() is False
                    assert get_ffmpeg_version() is None

                    diag = get_ffmpeg_diagnostics()
                    assert diag["resolved"] is False
                    assert diag["binary_path"] is None


def test_binary_execution_failure(tmp_path):
    """When a binary exists but fails with non-zero exit code or timeout, it is rejected."""
    bad_bin = tmp_path / "corrupted_ffmpeg.exe"
    bad_bin.write_text("corrupted")

    # Mock subprocess.run returning exit code 127
    mock_proc = MagicMock()
    mock_proc.returncode = 127
    mock_proc.stdout = ""
    mock_proc.stderr = "Command not found or permission denied"

    with patch("subprocess.run", return_value=mock_proc):
        is_valid, ver, err = ffmpeg_resolver._validate_binary(str(bad_bin))
        assert is_valid is False
        assert ver is None
        assert "Execution failed" in err


def test_caching_behavior():
    """Verify that resolution is cached and does not run validation repeatedly."""
    with patch("app.utils.ffmpeg_resolver._validate_binary", return_value=(True, "ffmpeg version 8.0-cached", None)) as mock_val:
        b1 = get_ffmpeg_binary(force_refresh=True)
        b2 = get_ffmpeg_binary(force_refresh=False)
        assert b1 == b2
        # Should only have validated the first candidate during the first call
        assert mock_val.call_count == 1
