import os
import subprocess
import tempfile
import sys
from pathlib import Path
import pytest
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import imageio_ffmpeg
from moviepy import ColorClip
from app.video.cinematic_composer import sanitize_and_spoof_camera_metadata
from app.video.dynamic_visual_engine import DynamicVisualEngine


def test_sanitize_and_spoof_camera_metadata(tmp_path):
    # Create a 1-second test MP4
    test_mp4 = tmp_path / "raw_synthetic_video.mp4"
    clip = ColorClip(size=(360, 640), color=(10, 20, 30), duration=0.8)
    clip.fps = 24
    clip.write_videofile(str(test_mp4), fps=24, codec="libx264", preset="ultrafast", logger=None)

    # Sanitize and spoof camera metadata
    clean_mp4 = sanitize_and_spoof_camera_metadata(test_mp4)
    assert clean_mp4.exists()
    assert clean_mp4.stat().st_size > 1000

    # Probe with ffmpeg to verify Lavf encoder is gone and Apple iPhone tags are present
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    res = subprocess.run([ffmpeg_exe, "-i", str(clean_mp4)], stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    probe_output = res.stderr

    # Assert no Lavf or Lavc encoder strings remain
    assert "Lavf" not in probe_output
    assert "Lavc" not in probe_output

    # Assert Apple QuickTime handler is injected
    assert "Core Media Video" in probe_output


def test_save_clean_photographic_image_strips_metadata(tmp_path):
    # Create an image with fake EXIF / metadata
    raw_img = Image.new("RGB", (200, 200), color=(100, 150, 200))
    target_jpg = tmp_path / "sanitized_photo.jpg"

    # Save via DynamicVisualEngine
    saved_path = DynamicVisualEngine.save_clean_photographic_image(raw_img, target_jpg)
    assert saved_path.exists()

    # Re-open and check that no EXIF or proprietary chunks exist
    reopened = Image.open(saved_path)
    exif = reopened.getexif()
    assert len(exif) == 0
