"""
Comprehensive Test Suite for Video Quality Gate & Safe Instagram Upload Pipeline.

Validates:
1. Missing file handling.
2. Zero-byte file handling.
3. Corrupt / invalid container handling.
4. Wrong resolution rejection (not 1080x1920).
5. Wrong aspect ratio rejection (not 9:16).
6. Missing audio stream rejection.
7. Silent audio stream rejection.
8. Wrong video codec rejection (not H.264).
9. Wrong pixel format rejection (not yuv420p).
10. Stale artifact rejection (created before job start time).
11. Hash mismatch rejection (file modified post-validation).
12. Replaced artifact rejection (different file swapped in place).
13. Upload attempted without validation report (HardUploadGateError).
14. Upload attempted with rejected report (HardUploadGateError).
15. State machine transition constraints (REJECTED cannot upload; RENDERING cannot skip validation).
16. Valid Reel passing all technical gates and proceeding through upload gate.
"""

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.instagram.uploader import InstagramUploader, upload_or_preview_reel
from app.publishing.publishing_errors import HardUploadGateError, PublishingValidationError
from app.publishing.state_machine import PublishingState, PublishingStateMachine, VALID_TRANSITIONS
from app.storage.production_workspace import ProductionWorkspaceManager, compute_file_sha256
from app.video.ffprobe_inspector import FFprobeInspector, FFprobeMetadata
from app.video.video_quality_gate import ValidationReport, VideoQualityGate, VideoQualityGateError


@pytest.fixture(autouse=True)
def ensure_offline_mode(monkeypatch):
    """Enforce offline testing mode across all tests."""
    monkeypatch.setenv("TESTING", "true")


@pytest.fixture
def temp_job_workspace(tmp_path):
    """Creates a temporary isolated production workspace."""
    ws_dir = tmp_path / "production_20261122_testjob_12345"
    ws_dir.mkdir(parents=True, exist_ok=True)
    video_path = ws_dir / "final_video.mp4"
    val_path = ws_dir / "validation.json"
    return {
        "job_id": "testjob_12345",
        "ws_dir": ws_dir,
        "video_path": video_path,
        "val_path": val_path,
        "job_start": time.time(),
    }


# =====================================================================
# 1. PHYSICAL FILE & LIFECYCLE CHECKS
# =====================================================================

def test_missing_file_rejected(temp_job_workspace):
    """VideoQualityGate rejects non-existent video files."""
    missing_path = temp_job_workspace["ws_dir"] / "non_existent.mp4"
    report = VideoQualityGate.validate_video(
        video_path=missing_path,
        job_id=temp_job_workspace["job_id"],
        job_start_epoch=temp_job_workspace["job_start"],
    )
    assert not report.passed
    assert report.status == "REJECTED"
    assert "file_exists" in report.check_results
    assert not report.check_results["file_exists"]
    assert any("does not exist" in e.lower() for e in report.errors)


def test_zero_byte_file_rejected(temp_job_workspace):
    """VideoQualityGate rejects 0-byte or truncated video files."""
    v_path = temp_job_workspace["video_path"]
    v_path.write_bytes(b"")  # 0 bytes

    report = VideoQualityGate.validate_video(
        video_path=v_path,
        job_id=temp_job_workspace["job_id"],
        job_start_epoch=temp_job_workspace["job_start"],
    )
    assert not report.passed
    assert report.status == "REJECTED"
    assert not report.check_results.get("file_size_valid", False)
    assert any("too small" in e.lower() for e in report.errors)


def test_corrupted_file_rejected(temp_job_workspace, monkeypatch):
    """VideoQualityGate rejects files that fail FFmpeg container decoding."""
    v_path = temp_job_workspace["video_path"]
    # Write garbage bytes that look like a 200KB file
    v_path.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\xFF" * (150 * 1024))

    # Mock FFprobeInspector returning corrupt decoding
    mock_meta = FFprobeMetadata(
        file_path=str(v_path),
        file_exists=True,
        file_size_bytes=v_path.stat().st_size,
        decode_passed=False,
        decode_errors=["Invalid data found when processing input", "moov atom not found"],
        has_video=False,
    )
    monkeypatch.setattr(FFprobeInspector, "probe", lambda *args, **kwargs: mock_meta)

    report = VideoQualityGate.validate_video(
        video_path=v_path,
        job_id=temp_job_workspace["job_id"],
        job_start_epoch=temp_job_workspace["job_start"],
    )
    assert not report.passed
    assert report.status == "REJECTED"
    assert not report.check_results.get("decode_integrity_pass", True)
    assert any("decoding audit failed" in e.lower() for e in report.errors)


def test_stale_artifact_rejected(temp_job_workspace):
    """VideoQualityGate rejects videos created before the current job started."""
    v_path = temp_job_workspace["video_path"]
    v_path.write_bytes(b"dummy video content" * 10000)

    # Set file timestamp to 2 hours ago
    old_time = time.time() - 7200.0
    os.utime(v_path, (old_time, old_time))

    # Job started 10 seconds ago
    job_start = time.time() - 10.0

    report = VideoQualityGate.validate_video(
        video_path=v_path,
        job_id=temp_job_workspace["job_id"],
        job_start_epoch=job_start,
    )
    assert not report.passed
    assert report.status == "REJECTED"
    assert not report.check_results.get("fresh_job_artifact", True)
    assert any("stale artifact" in e.lower() for e in report.errors)


# =====================================================================
# 2. RESOLUTION, ASPECT RATIO & CODEC CHECKS
# =====================================================================

def test_wrong_resolution_rejected(temp_job_workspace, monkeypatch):
    """VideoQualityGate strictly enforces 1080x1920 (rejects 720x1280 or 1920x1080)."""
    v_path = temp_job_workspace["video_path"]
    v_path.write_bytes(b"dummy" * 25000)

    # 720x1280 video mock
    mock_meta = FFprobeMetadata(
        file_path=str(v_path),
        file_exists=True,
        file_size_bytes=v_path.stat().st_size,
        duration_seconds=15.0,
        has_video=True,
        video_streams_count=1,
        video_codec="h264",
        pixel_format="yuv420p",
        width=720,
        height=1280,
        aspect_ratio_float=round(720 / 1280, 4),
        fps=30.0,
        video_bitrate_kbps=2000.0,
        has_audio=True,
        audio_streams_count=1,
        audio_codec="aac",
        audio_sample_rate=44100,
        is_audio_silent=False,
        decode_passed=True,
    )
    monkeypatch.setattr(FFprobeInspector, "probe", lambda *args, **kwargs: mock_meta)
    monkeypatch.setattr(VideoQualityGate, "_audit_visual_luminance", lambda *args, **kwargs: True)

    report = VideoQualityGate.validate_video(
        video_path=v_path,
        job_id=temp_job_workspace["job_id"],
        job_start_epoch=temp_job_workspace["job_start"],
    )
    assert not report.passed
    assert report.status == "REJECTED"
    assert not report.check_results.get("resolution_1080x1920", True)
    assert any("720x1280" in e for e in report.errors)


def test_wrong_aspect_ratio_rejected(temp_job_workspace, monkeypatch):
    """VideoQualityGate rejects horizontal 16:9 or square 1:1 videos."""
    v_path = temp_job_workspace["video_path"]
    v_path.write_bytes(b"dummy" * 25000)

    # 1920x1080 horizontal video mock
    mock_meta = FFprobeMetadata(
        file_path=str(v_path),
        file_exists=True,
        file_size_bytes=v_path.stat().st_size,
        duration_seconds=15.0,
        has_video=True,
        video_streams_count=1,
        video_codec="h264",
        pixel_format="yuv420p",
        width=1920,
        height=1080,
        aspect_ratio_float=round(1920 / 1080, 4),
        fps=30.0,
        video_bitrate_kbps=2500.0,
        has_audio=True,
        audio_streams_count=1,
        audio_codec="aac",
        audio_sample_rate=44100,
        is_audio_silent=False,
        decode_passed=True,
    )
    monkeypatch.setattr(FFprobeInspector, "probe", lambda *args, **kwargs: mock_meta)
    monkeypatch.setattr(VideoQualityGate, "_audit_visual_luminance", lambda *args, **kwargs: True)

    report = VideoQualityGate.validate_video(
        video_path=v_path,
        job_id=temp_job_workspace["job_id"],
        job_start_epoch=temp_job_workspace["job_start"],
    )
    assert not report.passed
    assert report.status == "REJECTED"
    assert not report.check_results.get("aspect_ratio_9_16", True)


def test_wrong_video_codec_rejected(temp_job_workspace, monkeypatch):
    """VideoQualityGate rejects non-H.264 codecs (e.g. HEVC/H.265 or VP9)."""
    v_path = temp_job_workspace["video_path"]
    v_path.write_bytes(b"dummy" * 25000)

    mock_meta = FFprobeMetadata(
        file_path=str(v_path),
        file_exists=True,
        file_size_bytes=v_path.stat().st_size,
        duration_seconds=15.0,
        has_video=True,
        video_streams_count=1,
        video_codec="hevc",  # Non-compliant
        pixel_format="yuv420p",
        width=1080,
        height=1920,
        aspect_ratio_float=round(1080 / 1920, 4),
        fps=30.0,
        video_bitrate_kbps=2000.0,
        has_audio=True,
        audio_streams_count=1,
        audio_codec="aac",
        audio_sample_rate=44100,
        is_audio_silent=False,
        decode_passed=True,
    )
    monkeypatch.setattr(FFprobeInspector, "probe", lambda *args, **kwargs: mock_meta)
    monkeypatch.setattr(VideoQualityGate, "_audit_visual_luminance", lambda *args, **kwargs: True)

    report = VideoQualityGate.validate_video(
        video_path=v_path,
        job_id=temp_job_workspace["job_id"],
        job_start_epoch=temp_job_workspace["job_start"],
    )
    assert not report.passed
    assert not report.check_results.get("video_codec_h264", True)
    assert any("hevc" in e for e in report.errors)


def test_wrong_pixel_format_rejected(temp_job_workspace, monkeypatch):
    """VideoQualityGate rejects non-yuv420p pixel formats (e.g. yuv444p or rgb24)."""
    v_path = temp_job_workspace["video_path"]
    v_path.write_bytes(b"dummy" * 25000)

    mock_meta = FFprobeMetadata(
        file_path=str(v_path),
        file_exists=True,
        file_size_bytes=v_path.stat().st_size,
        duration_seconds=15.0,
        has_video=True,
        video_streams_count=1,
        video_codec="h264",
        pixel_format="yuv444p",  # Non-compliant
        width=1080,
        height=1920,
        aspect_ratio_float=round(1080 / 1920, 4),
        fps=30.0,
        video_bitrate_kbps=2000.0,
        has_audio=True,
        audio_streams_count=1,
        audio_codec="aac",
        audio_sample_rate=44100,
        is_audio_silent=False,
        decode_passed=True,
    )
    monkeypatch.setattr(FFprobeInspector, "probe", lambda *args, **kwargs: mock_meta)
    monkeypatch.setattr(VideoQualityGate, "_audit_visual_luminance", lambda *args, **kwargs: True)

    report = VideoQualityGate.validate_video(
        video_path=v_path,
        job_id=temp_job_workspace["job_id"],
        job_start_epoch=temp_job_workspace["job_start"],
    )
    assert not report.passed
    assert not report.check_results.get("pixel_format_yuv420p", True)
    assert any("yuv444p" in e for e in report.errors)


# =====================================================================
# 3. AUDIO INTEGRITY & SILENCE CHECKS
# =====================================================================

def test_missing_audio_stream_rejected(temp_job_workspace, monkeypatch):
    """VideoQualityGate rejects video when required audio stream is missing."""
    v_path = temp_job_workspace["video_path"]
    v_path.write_bytes(b"dummy" * 25000)

    mock_meta = FFprobeMetadata(
        file_path=str(v_path),
        file_exists=True,
        file_size_bytes=v_path.stat().st_size,
        duration_seconds=15.0,
        has_video=True,
        video_streams_count=1,
        video_codec="h264",
        pixel_format="yuv420p",
        width=1080,
        height=1920,
        aspect_ratio_float=round(1080 / 1920, 4),
        fps=30.0,
        video_bitrate_kbps=2000.0,
        has_audio=False,  # Missing audio
        audio_streams_count=0,
        decode_passed=True,
    )
    monkeypatch.setattr(FFprobeInspector, "probe", lambda *args, **kwargs: mock_meta)
    monkeypatch.setattr(VideoQualityGate, "_audit_visual_luminance", lambda *args, **kwargs: True)

    report = VideoQualityGate.validate_video(
        video_path=v_path,
        job_id=temp_job_workspace["job_id"],
        job_start_epoch=temp_job_workspace["job_start"],
        require_audio=True,
    )
    assert not report.passed
    assert not report.check_results.get("audio_stream_exists", True)
    assert any("no audio stream" in e.lower() for e in report.errors)


def test_silent_audio_rejected(temp_job_workspace, monkeypatch):
    """VideoQualityGate rejects video when audio stream is completely silent."""
    v_path = temp_job_workspace["video_path"]
    v_path.write_bytes(b"dummy" * 25000)

    mock_meta = FFprobeMetadata(
        file_path=str(v_path),
        file_exists=True,
        file_size_bytes=v_path.stat().st_size,
        duration_seconds=15.0,
        has_video=True,
        video_streams_count=1,
        video_codec="h264",
        pixel_format="yuv420p",
        width=1080,
        height=1920,
        aspect_ratio_float=round(1080 / 1920, 4),
        fps=30.0,
        video_bitrate_kbps=2000.0,
        has_audio=True,
        audio_streams_count=1,
        audio_codec="aac",
        audio_sample_rate=44100,
        audio_max_volume_db=-91.0,  # Pure silence
        audio_mean_volume_db=-91.0,
        is_audio_silent=True,
        decode_passed=True,
    )
    monkeypatch.setattr(FFprobeInspector, "probe", lambda *args, **kwargs: mock_meta)
    monkeypatch.setattr(VideoQualityGate, "_audit_visual_luminance", lambda *args, **kwargs: True)

    report = VideoQualityGate.validate_video(
        video_path=v_path,
        job_id=temp_job_workspace["job_id"],
        job_start_epoch=temp_job_workspace["job_start"],
        require_audio=True,
    )
    assert not report.passed
    assert not report.check_results.get("audio_not_silent", True)
    assert any("silent audio" in e.lower() for e in report.errors)


# =====================================================================
# 4. HARD UPLOAD GATE & ARTIFACT INTEGRITY
# =====================================================================

def test_upload_attempt_without_validation_report_aborts(temp_job_workspace):
    """InstagramUploader aborts with HardUploadGateError if no validation report exists."""
    v_path = temp_job_workspace["video_path"]
    v_path.write_bytes(b"some video bytes" * 10000)

    uploader = InstagramUploader()
    with pytest.raises(HardUploadGateError) as exc_info:
        uploader.upload_reel(
            video_path=v_path,
            caption="Test caption #astrology",
            force_dry_run=True,
        )
    assert "Missing validation report" in str(exc_info.value) or "never validated" in str(exc_info.value)


def test_upload_attempt_with_rejected_validation_aborts(temp_job_workspace):
    """InstagramUploader aborts with HardUploadGateError if report is REJECTED."""
    v_path = temp_job_workspace["video_path"]
    v_path.write_bytes(b"some video bytes" * 10000)

    rejected_report = ValidationReport(
        job_id=temp_job_workspace["job_id"],
        video_path=str(v_path.resolve()),
        sha256_hash="dummyhash",
        file_size_bytes=v_path.stat().st_size,
        created_at_epoch=time.time(),
        job_start_epoch=temp_job_workspace["job_start"],
        validation_timestamp=time.time(),
        passed=False,
        status="REJECTED",
        errors=["Resolution is wrong", "Audio missing"],
    )
    rejected_report.save(temp_job_workspace["val_path"])

    uploader = InstagramUploader()
    with pytest.raises(HardUploadGateError) as exc_info:
        uploader.upload_reel(
            video_path=v_path,
            caption="Test caption #astrology",
            force_dry_run=True,
            validation_report=rejected_report,
            job_id=temp_job_workspace["job_id"],
        )
    assert "status is 'REJECTED'" in str(exc_info.value)


def test_file_size_changed_after_validation_aborts_upload(temp_job_workspace):
    """InstagramUploader detects post-validation size modification and aborts."""
    v_path = temp_job_workspace["video_path"]
    v_path.write_bytes(b"original valid bytes" * 10000)
    original_hash = compute_file_sha256(v_path)

    report = ValidationReport(
        job_id=temp_job_workspace["job_id"],
        video_path=str(v_path.resolve()),
        sha256_hash=original_hash,
        file_size_bytes=v_path.stat().st_size,
        created_at_epoch=time.time(),
        job_start_epoch=temp_job_workspace["job_start"],
        validation_timestamp=time.time(),
        passed=True,
        status="VALIDATED",
    )
    report.save(temp_job_workspace["val_path"])

    # File size changed post-validation!
    v_path.write_bytes(b"tampered or overwritten bytes" * 10000)

    uploader = InstagramUploader()
    with pytest.raises(HardUploadGateError) as exc_info:
        uploader.upload_reel(
            video_path=v_path,
            caption="Test caption #astrology",
            force_dry_run=True,
            validation_report=report,
            job_id=temp_job_workspace["job_id"],
        )
    assert "file size changed post-validation" in str(exc_info.value).lower()


def test_hash_mismatch_after_validation_aborts_upload(temp_job_workspace):
    """InstagramUploader detects post-validation byte modification and aborts."""
    v_path = temp_job_workspace["video_path"]
    v_path.write_bytes(b"original valid bytes" * 10000)  # 20 bytes * 10000 = 200,000 bytes
    original_hash = compute_file_sha256(v_path)

    # Valid report for original video
    report = ValidationReport(
        job_id=temp_job_workspace["job_id"],
        video_path=str(v_path.resolve()),
        sha256_hash=original_hash,
        file_size_bytes=v_path.stat().st_size,
        created_at_epoch=time.time(),
        job_start_epoch=temp_job_workspace["job_start"],
        validation_timestamp=time.time(),
        passed=True,
        status="VALIDATED",
    )
    report.save(temp_job_workspace["val_path"])

    # File is modified with identical size (20 bytes) but different bytes!
    v_path.write_bytes(b"modified valid bytes" * 10000)

    uploader = InstagramUploader()
    with pytest.raises(HardUploadGateError) as exc_info:
        uploader.upload_reel(
            video_path=v_path,
            caption="Test caption #astrology",
            force_dry_run=True,
            validation_report=report,
            job_id=temp_job_workspace["job_id"],
        )
    assert "hash mismatch" in str(exc_info.value).lower() or "modified or replaced" in str(exc_info.value).lower()


def test_replaced_artifact_aborts_upload(temp_job_workspace, tmp_path):
    """InstagramUploader detects when a different file is swapped into place."""
    v_path = temp_job_workspace["video_path"]
    v_path.write_bytes(b"video A content" * 10000)
    hash_a = compute_file_sha256(v_path)

    report_a = ValidationReport(
        job_id=temp_job_workspace["job_id"],
        video_path=str(v_path.resolve()),
        sha256_hash=hash_a,
        file_size_bytes=v_path.stat().st_size,
        created_at_epoch=time.time(),
        job_start_epoch=temp_job_workspace["job_start"],
        validation_timestamp=time.time(),
        passed=True,
        status="VALIDATED",
    )

    # Completely different video B swapped into place
    other_file = tmp_path / "video_b.mp4"
    other_file.write_bytes(b"video B completely different" * 12000)
    shutil.copyfile(other_file, v_path)

    uploader = InstagramUploader()
    with pytest.raises(HardUploadGateError):
        uploader.upload_reel(
            video_path=v_path,
            caption="Test caption #astrology",
            force_dry_run=True,
            validation_report=report_a,
            job_id=temp_job_workspace["job_id"],
        )


# =====================================================================
# 5. STATE MACHINE TRANSITION RULES
# =====================================================================

def test_state_machine_transition_constraints():
    """Validates that REJECTED and unvalidated states cannot transition to upload."""
    assert PublishingState.VALIDATED in VALID_TRANSITIONS[PublishingState.VALIDATING]
    assert PublishingState.REJECTED in VALID_TRANSITIONS[PublishingState.VALIDATING]

    # REJECTED cannot transition to UPLOADING or PUBLISHED
    assert PublishingState.UPLOADING not in VALID_TRANSITIONS[PublishingState.REJECTED]
    assert PublishingState.PUBLISHED not in VALID_TRANSITIONS[PublishingState.REJECTED]

    # RENDERING cannot bypass validation and jump straight to VALIDATED or UPLOADING
    assert PublishingState.VALIDATED not in VALID_TRANSITIONS[PublishingState.RENDERING]
    assert PublishingState.UPLOADING not in VALID_TRANSITIONS[PublishingState.RENDERING]

    # Only VALIDATED can transition to UPLOADING
    assert PublishingState.UPLOADING in VALID_TRANSITIONS[PublishingState.VALIDATED]


# =====================================================================
# 6. HAPPY PATH: FULL GATE PASS & DRY-RUN UPLOAD APPROVAL
# =====================================================================

def test_valid_video_passes_gate_and_approves_upload(temp_job_workspace, monkeypatch):
    """A compliant 1080x1920 H.264/AAC video passes all checks and is approved for upload."""
    v_path = temp_job_workspace["video_path"]
    v_path.write_bytes(b"valid video bytes" * 25000)

    mock_meta = FFprobeMetadata(
        file_path=str(v_path.resolve()),
        file_exists=True,
        file_size_bytes=v_path.stat().st_size,
        duration_seconds=28.5,
        has_video=True,
        video_streams_count=1,
        video_codec="h264",
        pixel_format="yuv420p",
        width=1080,
        height=1920,
        aspect_ratio_float=round(1080 / 1920, 4),
        fps=24.0,
        video_bitrate_kbps=4500.0,
        has_audio=True,
        audio_streams_count=1,
        audio_codec="aac",
        audio_sample_rate=44100,
        audio_max_volume_db=-6.2,
        audio_mean_volume_db=-18.4,
        is_audio_silent=False,
        decode_passed=True,
        decode_errors=[],
    )
    monkeypatch.setattr(FFprobeInspector, "probe", lambda *args, **kwargs: mock_meta)
    monkeypatch.setattr(VideoQualityGate, "_audit_visual_luminance", lambda *args, **kwargs: True)

    # Validate video
    val_report = VideoQualityGate.validate_video(
        video_path=v_path,
        job_id=temp_job_workspace["job_id"],
        job_start_epoch=temp_job_workspace["job_start"],
        save_report_path=temp_job_workspace["val_path"],
    )

    assert val_report.passed is True
    assert val_report.status == "VALIDATED"
    assert val_report.check_results["resolution_1080x1920"] is True
    assert val_report.check_results["video_codec_h264"] is True
    assert val_report.check_results["pixel_format_yuv420p"] is True
    assert val_report.check_results["audio_not_silent"] is True
    assert val_report.check_results["decode_integrity_pass"] is True

    # Pre-upload verification gate
    is_ok, reason = VideoQualityGate.verify_artifact_integrity_before_upload(
        video_path=v_path,
        expected_report=val_report,
        job_id=temp_job_workspace["job_id"],
    )
    assert is_ok is True
    assert reason is None

    # Dispatch to InstagramUploader dry run
    uploader = InstagramUploader()
    upload_res = uploader.upload_reel(
        video_path=v_path,
        caption="Sacred Rahu Ketu Axis Insight #vedicastrology #kundli",
        force_dry_run=True,
        validation_report=val_report,
        job_id=temp_job_workspace["job_id"],
    )

    assert upload_res["success"] is True
    assert upload_res["mode"] == "DRY_RUN"
    assert upload_res["video_specs_valid"] is True
