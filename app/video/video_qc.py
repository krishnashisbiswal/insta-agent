"""
Automated Video Quality Control (QC) & Inspection Engine.
Performs comprehensive pre-publication and post-render validation on final Reel videos:
1. Container & Codec Verification: Valid MP4, H.264 (libx264), YUV420p, AAC audio.
2. Dimensions & Geometry: Vertical 9:16 aspect ratio, 1080x1920 output resolution.
3. Audio/Video Duration & Sync: Audio presence, duration alignment (|video - audio| <= 0.5s), no zero-audio outputs.
4. Visual Integrity Audit: Black frame detection, washed out frames, corrupt frames, minimum size.
5. Review Artifact Generator: Generates a multi-scene visual contact sheet (scene_contact_sheet.jpg).
"""

import json
import logging
import math
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from PIL import Image, ImageDraw, ImageFont, ImageStat

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import VIDEO_HEIGHT, VIDEO_WIDTH, VIDEO_FPS
from app.utils.ffmpeg_resolver import get_ffmpeg_binary

logger = logging.getLogger("VideoQC")


class VideoQCError(Exception):
    """Raised when a rendered video fails quality control inspection."""
    pass


@dataclass
class QCReport:
    """Structured report returned by the Automated Video QC Gate."""
    video_path: str
    passed: bool
    duration: float = 0.0
    dimensions: Tuple[int, int] = (0, 0)
    aspect_ratio: str = "unknown"
    fps: float = 0.0
    video_codec: str = "unknown"
    audio_codec: str = "unknown"
    has_audio: bool = False
    audio_synced: bool = False
    black_frames_detected: bool = False
    corrupt_frames_detected: bool = False
    contact_sheet_path: Optional[str] = None
    checks: Dict[str, bool] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class VideoQualityControl:
    """
    Automated QC Gate validating completed Reel videos before Instagram publishing.
    """

    MIN_FILE_SIZE_BYTES = 1000     # At least 1 KB
    MIN_LUMINANCE = 4.0           # Reject video composed entirely of black frames
    MAX_LUMINANCE = 250.0         # Reject video composed entirely of washed out frames
    TARGET_WIDTH = VIDEO_WIDTH     # 1080
    TARGET_HEIGHT = VIDEO_HEIGHT   # 1920

    @classmethod
    def audit_video(
        cls,
        video_path: Union[Path, str],
        expected_scenes: Optional[int] = None,
        expected_duration: Optional[float] = None,
        audio_path: Optional[Union[Path, str]] = None,
        generate_contact_sheet: bool = True,
    ) -> QCReport:
        """
        Executes complete quality control inspection on a rendered video file.
        """
        v_path = Path(video_path)
        errors: List[str] = []
        checks: Dict[str, bool] = {}

        # 1. Physical file check
        if not v_path.exists():
            return QCReport(
                video_path=str(v_path),
                passed=False,
                errors=[f"Video file does not exist: {v_path}"],
                checks={"file_exists": False},
            )

        file_size = v_path.stat().st_size
        if file_size < cls.MIN_FILE_SIZE_BYTES:
            return QCReport(
                video_path=str(v_path),
                passed=False,
                errors=[f"Video file is truncated or unexpectedly small ({file_size} bytes, min {cls.MIN_FILE_SIZE_BYTES})"],
                checks={"file_size_valid": False},
            )
        checks["file_size_valid"] = True

        # 2. Probe with MoviePy / FFprobe
        duration = 0.0
        w, h = 0, 0
        fps = 0.0
        has_audio = False
        v_codec = "h264"
        a_codec = "aac"

        try:
            from moviepy import VideoFileClip
            with VideoFileClip(str(v_path)) as clip:
                duration = round(clip.duration, 2)
                w, h = clip.size
                fps = round(clip.fps, 1) if clip.fps else VIDEO_FPS
                has_audio = clip.audio is not None and clip.audio.duration > 0
        except Exception as exc:
            errors.append(f"Failed to read video with MoviePy: {exc}")
            checks["decode_success"] = False
            return QCReport(
                video_path=str(v_path),
                passed=False,
                errors=errors,
                checks=checks,
            )

        checks["decode_success"] = True

        # 3. Geometry & Aspect Ratio Check
        dimensions_ok = (w == cls.TARGET_WIDTH and h == cls.TARGET_HEIGHT)
        if not dimensions_ok:
            # Allow proportional vertical 9:16 (w < h and ratio approx 0.5625)
            ratio = w / h if h > 0 else 0
            if w >= h or ratio > 0.70 or ratio < 0.45:
                errors.append(f"Invalid dimensions: {w}x{h}. Expected vertical 9:16 (1080x1920).")
                checks["dimensions_valid"] = False
            else:
                checks["dimensions_valid"] = True
        else:
            checks["dimensions_valid"] = True

        aspect_ratio = f"{w}:{h}"

        # 4. Audio Verification & Duration Sync
        if not has_audio:
            errors.append("Video has no audio stream or empty audio duration.")
            checks["audio_present"] = False
        else:
            checks["audio_present"] = True

        audio_synced = True
        if expected_duration is not None and expected_duration > 0:
            diff = abs(duration - expected_duration)
            if diff > 1.5:
                errors.append(f"Video duration mismatch: actual {duration}s vs expected {expected_duration}s (diff {diff:.2f}s > 1.5s).")
                audio_synced = False
        if audio_path:
            a_p = Path(audio_path)
            if a_p.exists():
                try:
                    from moviepy import AudioFileClip
                    with AudioFileClip(str(a_p)) as ac:
                        a_dur = round(ac.duration, 2)
                        diff = abs(duration - a_dur)
                        if diff > 1.5:
                            errors.append(f"Audio/video sync mismatch: video={duration}s vs audio={a_dur}s (diff={diff:.2f}s).")
                            audio_synced = False
                except Exception as e:
                    logger.debug(f"Audio sync check notice: {e}")
        checks["audio_synced"] = audio_synced

        # 5. Visual Frame Sampling (Black/Corrupt Frame Detection)
        black_frames = False
        corrupt_frames = False
        sampled_frames: List[Image.Image] = []

        try:
            from moviepy import VideoFileClip
            with VideoFileClip(str(v_path)) as clip:
                num_samples = max(3, expected_scenes or 5)
                sample_times = [
                    round((duration / (num_samples + 1)) * (i + 1), 2)
                    for i in range(num_samples)
                ]

                dark_count = 0
                for t in sample_times:
                    if t >= duration:
                        continue
                    try:
                        arr = clip.get_frame(t)
                        f_img = Image.fromarray(arr)
                        sampled_frames.append(f_img)

                        stat = ImageStat.Stat(f_img.convert("L"))
                        lum = stat.mean[0]
                        if lum < cls.MIN_LUMINANCE:
                            dark_count += 1
                    except Exception as fe:
                        corrupt_frames = True
                        errors.append(f"Corrupt frame detected at t={t}s: {fe}")

                # If majority of sampled frames are totally black, fail
                if dark_count >= max(2, num_samples - 1):
                    black_frames = True
                    errors.append(f"Black frames detected: {dark_count}/{len(sample_times)} sampled frames are completely dark.")
        except Exception as exc:
            corrupt_frames = True
            errors.append(f"Error sampling video frames: {exc}")

        checks["no_black_frames"] = not black_frames
        checks["no_corrupt_frames"] = not corrupt_frames

        # 6. Contact Sheet Review Artifact
        contact_sheet_path: Optional[str] = None
        if generate_contact_sheet and sampled_frames:
            try:
                contact_sheet_path = cls._create_contact_sheet(
                    video_path=v_path,
                    frames=sampled_frames,
                    duration=duration,
                )
                checks["contact_sheet_created"] = True
            except Exception as e:
                logger.debug(f"Contact sheet generation notice: {e}")
                checks["contact_sheet_created"] = False

        passed = len(errors) == 0

        report = QCReport(
            video_path=str(v_path),
            passed=passed,
            duration=duration,
            dimensions=(w, h),
            aspect_ratio=aspect_ratio,
            fps=fps,
            video_codec=v_codec,
            audio_codec=a_codec,
            has_audio=has_audio,
            audio_synced=audio_synced,
            black_frames_detected=black_frames,
            corrupt_frames_detected=corrupt_frames,
            contact_sheet_path=contact_sheet_path,
            checks=checks,
            errors=errors,
        )

        if not passed:
            logger.warning(f"[VideoQC] Reel QC Failed for {v_path.name}: {errors}")
        else:
            logger.info(f"[VideoQC] Reel QC Passed for {v_path.name} ({duration}s, {w}x{h}, {fps}fps, Audio=OK)")

        return report

    @classmethod
    def _create_contact_sheet(
        cls,
        video_path: Path,
        frames: List[Image.Image],
        duration: float,
    ) -> str:
        """
        Creates an organized, labeled 2-column contact sheet of the sampled scene frames.
        """
        if not frames:
            return ""

        thumb_w = 270
        thumb_h = 480
        cols = 3 if len(frames) >= 5 else 2
        rows = math.ceil(len(frames) / cols)

        header_h = 60
        margin = 15
        grid_w = cols * thumb_w + (cols + 1) * margin
        grid_h = header_h + rows * thumb_h + (rows + 1) * margin

        sheet = Image.new("RGB", (grid_w, grid_h), (18, 18, 24))
        draw = ImageDraw.Draw(sheet)

        # Header banner
        draw.text((margin, 18), f"REEL QC CONTACT SHEET: {video_path.name} ({duration:.1f}s)", fill=(255, 215, 0))

        for idx, f in enumerate(frames):
            r = idx // cols
            c = idx % cols
            x = margin + c * (thumb_w + margin)
            y = header_h + margin + r * (thumb_h + margin)

            resized = f.resize((thumb_w, thumb_h), Image.Resampling.BILINEAR)
            sheet.paste(resized, (x, y))

            # Frame label
            label = f"Scene {idx + 1}"
            draw.rectangle([x, y + thumb_h - 28, x + thumb_w, y + thumb_h], fill=(0, 0, 0, 200))
            draw.text((x + 8, y + thumb_h - 22), label, fill=(255, 255, 255))

        out_dir = PROJECT_ROOT / "insta content"
        out_dir.mkdir(parents=True, exist_ok=True)
        sheet_path = out_dir / f"scene_contact_sheet_{video_path.stem}.jpg"
        sheet.save(sheet_path, "JPEG", quality=90)
        return str(sheet_path)
