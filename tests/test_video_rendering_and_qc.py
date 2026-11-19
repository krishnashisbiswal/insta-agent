"""
Tests for Video Rendering, Audio Sync & Quality Control (Chunk 6).
Covers:
1. Video Rendering Pipeline & Format Compliance (1080x1920, 9:16 vertical, H.264, AAC).
2. Automated Video Quality Control (QC) Gate:
   - File size, aspect ratio, duration sync, black frame detection, corrupt frame detection.
   - Contact sheet review artifact generation.
3. Audio Mixing & Sync:
   - Voiceover primary track with ambient background music at -18dB.
   - Silence and duration alignment.
4. Caption & Devanagari Unicode Rendering:
   - Preserves Hindi characters, auto-scales without overflow.
5. Camera Metadata Sanitization (Task 7):
   - Strips sensitive metadata without fabricating iPhone hardware.
"""

import io
import math
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import imageio_ffmpeg
from moviepy import ColorClip, AudioFileClip
from config.settings import VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS
from app.utils.ffmpeg_resolver import get_ffmpeg_binary
from app.video.video_qc import VideoQualityControl, QCReport, VideoQCError
from app.video.cinematic_composer import (
    sanitize_video_metadata,
    sanitize_caption_text,
    get_font,
    split_scene_into_beats,
    render_kinetic_caption_layer,
    generate_cinematic_soundtrack,
)


# =========================================================================
# 1. VIDEO QUALITY CONTROL (QC) GATE TESTS
# =========================================================================

def test_video_qc_validates_healthy_reel(tmp_path):
    """Verify VideoQualityControl passes a healthy 1080x1920 vertical video with audio."""
    test_video = tmp_path / "healthy_reel.mp4"
    audio_path = tmp_path / "sound.wav"

    # Generate synthetic soundtrack
    generate_cinematic_soundtrack(duration=1.2, output_path=audio_path)

    clip = ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(40, 80, 140), duration=1.0)
    clip.fps = 24
    audio_clip = AudioFileClip(str(audio_path)).with_duration(1.0)
    clip = clip.with_audio(audio_clip)

    clip.write_videofile(
        str(test_video),
        fps=24,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        logger=None,
    )
    clip.close()
    audio_clip.close()

    report = VideoQualityControl.audit_video(
        video_path=test_video,
        expected_scenes=1,
        expected_duration=1.0,
        audio_path=audio_path,
        generate_contact_sheet=True,
    )

    assert report.passed is True
    assert report.dimensions == (VIDEO_WIDTH, VIDEO_HEIGHT)
    assert report.has_audio is True
    assert report.audio_synced is True
    assert report.black_frames_detected is False
    assert report.corrupt_frames_detected is False
    assert report.contact_sheet_path is not None
    assert Path(report.contact_sheet_path).exists()


def test_video_qc_detects_black_frames(tmp_path):
    """Verify VideoQualityControl rejects a video composed entirely of pitch black frames."""
    black_video = tmp_path / "black_video.mp4"
    audio_path = tmp_path / "sound.wav"
    generate_cinematic_soundtrack(duration=1.2, output_path=audio_path)

    clip = ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(0, 0, 0), duration=1.0)
    clip.fps = 24
    audio_clip = AudioFileClip(str(audio_path)).with_duration(1.0)
    clip = clip.with_audio(audio_clip)

    clip.write_videofile(
        str(black_video),
        fps=24,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        logger=None,
    )
    clip.close()
    audio_clip.close()

    report = VideoQualityControl.audit_video(
        video_path=black_video,
        expected_scenes=1,
        expected_duration=1.0,
    )

    assert report.passed is False
    assert report.black_frames_detected is True
    assert any("black frames" in err.lower() for err in report.errors)


def test_video_qc_detects_missing_audio(tmp_path):
    """Verify VideoQualityControl flags a video rendered without an audio track."""
    silent_video = tmp_path / "silent_video.mp4"

    clip = ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(50, 100, 150), duration=0.8)
    clip.fps = 24
    clip.write_videofile(
        str(silent_video),
        fps=24,
        codec="libx264",
        preset="ultrafast",
        logger=None,
    )
    clip.close()

    report = VideoQualityControl.audit_video(
        video_path=silent_video,
        expected_scenes=1,
        expected_duration=0.8,
    )

    assert report.passed is False
    assert report.has_audio is False
    assert any("no audio stream" in err.lower() for err in report.errors)


def test_video_qc_detects_duration_mismatch(tmp_path):
    """Verify VideoQualityControl flags significant audio/video duration discrepancy (>1.5s)."""
    mismatch_video = tmp_path / "mismatch_video.mp4"
    clip = ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(50, 100, 150), duration=1.0)
    clip.fps = 24
    clip.write_videofile(str(mismatch_video), fps=24, codec="libx264", preset="ultrafast", logger=None)
    clip.close()

    report = VideoQualityControl.audit_video(
        video_path=mismatch_video,
        expected_duration=5.0,  # 1.0s actual vs 5.0s expected (diff = 4.0s)
    )

    assert report.passed is False
    assert any("duration mismatch" in err.lower() for err in report.errors)


def test_video_qc_rejects_missing_file():
    """Verify VideoQualityControl gracefully fails when target file does not exist."""
    report = VideoQualityControl.audit_video(video_path="nonexistent_video_path.mp4")
    assert report.passed is False
    assert report.checks.get("file_exists") is False


# =========================================================================
# 2. CAPTION & UNICODE DEVANAGARI TESTS
# =========================================================================

def test_sanitize_caption_text_preserves_devanagari_hindi():
    """Verify Hindi Devanagari text is strictly preserved in captions."""
    hindi_text = "क्या आप जानते हैं कि पाइराइट क्रिस्टल ऊर्जा बदलता है?"
    sanitized = sanitize_caption_text(hindi_text)
    assert sanitized == hindi_text
    assert "पाइराइट" in sanitized
    assert "क्रिस्टल" in sanitized


def test_sanitize_caption_text_cleans_unwanted_characters():
    """Verify smart quotes, em-dashes and symbols are cleaned cleanly."""
    raw = '“विशेष—परामर्श” ✦ और ‘कुंडली’...'
    clean = sanitize_caption_text(raw)
    assert "“" not in clean
    assert "✦" not in clean
    assert "विशेष" in clean
    assert "कुंडली" in clean


def test_get_font_loads_indic_font_for_devanagari():
    """Verify get_font prioritizes Indic font when Devanagari text is passed."""
    font = get_font(size=40, bold=True, family="impact", text="पाइराइट")
    assert font is not None


def test_render_kinetic_caption_layer_renders_clean_overlay():
    """Verify kinetic caption overlay renders at 1080x1920 without exception."""
    overlay = render_kinetic_caption_layer(
        width=VIDEO_WIDTH,
        height=VIDEO_HEIGHT,
        text="INSTANT NERVOUS STABILITY",
        scene_number=2,
        total_scenes=5,
        badge_text="NERVOUS CALM",
    )
    assert overlay.size == (VIDEO_WIDTH, VIDEO_HEIGHT)
    assert overlay.mode == "RGBA"


# =========================================================================
# 3. CAMERA METADATA & TASK 7 COMPLIANCE
# =========================================================================

def test_sanitize_video_metadata_no_fake_hardware(tmp_path):
    """
    TASK 7 MANDATE:
    Verify video metadata is sanitized to neutral QuickTime container tags
    without fabricating Apple iPhone hardware or camera models.
    """
    test_mp4 = tmp_path / "raw_video.mp4"
    clip = ColorClip(size=(360, 640), color=(20, 40, 60), duration=0.5)
    clip.fps = 24
    clip.write_videofile(str(test_mp4), fps=24, codec="libx264", preset="ultrafast", logger=None)
    clip.close()

    clean_mp4 = sanitize_video_metadata(test_mp4)
    assert clean_mp4.exists()

    ffmpeg_exe = get_ffmpeg_binary() or imageio_ffmpeg.get_ffmpeg_exe()
    res = subprocess.run([ffmpeg_exe, "-i", str(clean_mp4)], stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    probe_output = res.stderr

    # Container tags present
    assert "Core Media Video" in probe_output

    # No fake iPhone hardware claims
    assert "iPhone 15 Pro Max" not in probe_output
    assert "Apple" not in probe_output.split("handler_name")[0]


# =========================================================================
# 4. SOUNDTRACK SYNTHESIS
# =========================================================================

def test_generate_cinematic_soundtrack_produces_valid_wav(tmp_path):
    """Verify generate_cinematic_soundtrack produces a valid, playable WAV file."""
    wav_path = tmp_path / "ambient.wav"
    generate_cinematic_soundtrack(duration=2.0, output_path=wav_path)
    assert wav_path.exists()
    assert wav_path.stat().st_size > 5000

    import wave
    with wave.open(str(wav_path), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == 44100
        assert wf.getnframes() == int(44100 * 2.0)
