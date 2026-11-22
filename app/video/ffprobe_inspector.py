"""
Authoritative Video Stream & Container Inspector.
Executes real binary-level FFprobe / FFmpeg inspection on rendered Reels:
1. Stream probe: Resolution, Aspect Ratio, Codec, Pixel Format, FPS, Bitrate, Duration.
2. Audio stream probe: Codec, Sample Rate, Channels, Bitrate, Loudness & Silence Detection.
3. Full Decodability Audit: Complete container decoding pass (`ffmpeg -v error -i ... -f null -`)
   catching broken timestamps, truncated moov atoms, and corrupted frame packets.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from app.utils.ffmpeg_resolver import get_ffmpeg_binary, get_ffprobe_binary

logger = logging.getLogger("FFprobeInspector")


class ProbeExecutionError(Exception):
    """Raised when probing fails to execute or locate tools."""
    pass


@dataclass
class FFprobeMetadata:
    """Complete technical stream and container profile for a video file."""
    file_path: str
    file_exists: bool
    file_size_bytes: int = 0
    duration_seconds: float = 0.0
    container_format: str = "unknown"
    overall_bitrate_kbps: float = 0.0

    # Video stream
    has_video: bool = False
    video_streams_count: int = 0
    video_codec: str = "unknown"
    video_profile: str = "unknown"
    pixel_format: str = "unknown"
    width: int = 0
    height: int = 0
    aspect_ratio: str = "unknown"
    aspect_ratio_float: float = 0.0
    fps: float = 0.0
    video_bitrate_kbps: float = 0.0

    # Audio stream
    has_audio: bool = False
    audio_streams_count: int = 0
    audio_codec: str = "unknown"
    audio_sample_rate: int = 0
    audio_channels: int = 0
    audio_bitrate_kbps: float = 0.0
    audio_mean_volume_db: float = -99.0
    audio_max_volume_db: float = -99.0
    is_audio_silent: bool = False

    # Decode integrity
    decode_passed: bool = False
    decode_errors: List[str] = field(default_factory=list)

    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FFprobeInspector:
    """
    Direct technical probe for MP4/video files using ffprobe and ffmpeg binaries.
    """

    @classmethod
    def probe(
        cls,
        video_path: Union[Path, str],
        timeout_seconds: float = 20.0,
        verify_decode: bool = True,
        check_silence: bool = True,
    ) -> FFprobeMetadata:
        """
        Executes binary probe and returns complete FFprobeMetadata.
        """
        vp = Path(video_path)
        if not vp.exists() or not vp.is_file():
            return FFprobeMetadata(
                file_path=str(vp),
                file_exists=False,
                decode_passed=False,
                decode_errors=[f"File does not exist: {vp}"],
            )

        file_size = vp.stat().st_size
        meta = FFprobeMetadata(
            file_path=str(vp.resolve()),
            file_exists=True,
            file_size_bytes=file_size,
        )

        ffprobe_bin = get_ffprobe_binary()
        ffmpeg_bin = get_ffmpeg_binary()

        # If neither binary is available, report failure
        if not ffprobe_bin and not ffmpeg_bin:
            meta.decode_passed = False
            meta.decode_errors.append("Neither FFprobe nor FFmpeg binary is available on the system.")
            return meta

        # 1. Probe technical stream properties
        probed_via_ffprobe = False
        if ffprobe_bin:
            probed_via_ffprobe = cls._probe_with_ffprobe(ffprobe_bin, vp, meta, timeout_seconds)

        if not probed_via_ffprobe and ffmpeg_bin:
            cls._probe_with_ffmpeg(ffmpeg_bin, vp, meta, timeout_seconds)

        # 2. Audio Loudness & Silence Verification
        if check_silence and ffmpeg_bin and meta.has_audio:
            cls._measure_audio_volume(ffmpeg_bin, vp, meta, timeout_seconds)

        # 3. Full Decodability Check
        if verify_decode and ffmpeg_bin:
            cls._verify_full_decode(ffmpeg_bin, vp, meta, timeout_seconds)
        else:
            meta.decode_passed = meta.has_video

        return meta

    @classmethod
    def _probe_with_ffprobe(
        cls,
        ffprobe_bin: str,
        video_path: Path,
        meta: FFprobeMetadata,
        timeout: float,
    ) -> bool:
        """Probes video using ffprobe JSON output."""
        try:
            cmd = [
                ffprobe_bin,
                "-v", "error",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                "-show_error",
                str(video_path),
            ]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, text=True)
            if proc.returncode != 0:
                logger.debug(f"ffprobe failed (code {proc.returncode}): {proc.stderr[:100]}")
                return False

            data = json.loads(proc.stdout)
            meta.raw_metadata["ffprobe_json"] = data

            fmt = data.get("format", {})
            meta.container_format = fmt.get("format_name", "unknown")
            meta.duration_seconds = float(fmt.get("duration", 0.0) or 0.0)
            if "bit_rate" in fmt:
                meta.overall_bitrate_kbps = round(float(fmt["bit_rate"]) / 1000.0, 1)

            streams = data.get("streams", [])
            for s in streams:
                codec_type = s.get("codec_type")
                if codec_type == "video" and not meta.has_video:
                    meta.has_video = True
                    meta.video_streams_count += 1
                    meta.video_codec = str(s.get("codec_name", "")).lower()
                    meta.video_profile = str(s.get("profile", "")).lower()
                    meta.pixel_format = str(s.get("pix_fmt", "")).lower()
                    meta.width = int(s.get("width", 0))
                    meta.height = int(s.get("height", 0))
                    if meta.height > 0:
                        meta.aspect_ratio_float = round(meta.width / meta.height, 4)
                        meta.aspect_ratio = f"{meta.width}:{meta.height}"

                    # FPS parsing (e.g. "24/1" or "30000/1001")
                    r_frame_rate = s.get("r_frame_rate", "")
                    if "/" in r_frame_rate:
                        num, den = r_frame_rate.split("/", 1)
                        if float(den) > 0:
                            meta.fps = round(float(num) / float(den), 2)
                    elif r_frame_rate:
                        meta.fps = round(float(r_frame_rate), 2)

                    if "bit_rate" in s:
                        meta.video_bitrate_kbps = round(float(s["bit_rate"]) / 1000.0, 1)
                    if not meta.duration_seconds and "duration" in s:
                        meta.duration_seconds = float(s["duration"])

                elif codec_type == "audio" and not meta.has_audio:
                    meta.has_audio = True
                    meta.audio_streams_count += 1
                    meta.audio_codec = str(s.get("codec_name", "")).lower()
                    meta.audio_sample_rate = int(s.get("sample_rate", 0))
                    meta.audio_channels = int(s.get("channels", 0))
                    if "bit_rate" in s:
                        meta.audio_bitrate_kbps = round(float(s["bit_rate"]) / 1000.0, 1)

            return meta.has_video
        except Exception as exc:
            logger.debug(f"ffprobe exception: {exc}")
            return False

    @classmethod
    def _probe_with_ffmpeg(
        cls,
        ffmpeg_bin: str,
        video_path: Path,
        meta: FFprobeMetadata,
        timeout: float,
    ) -> None:
        """Parses stream details from ffmpeg banner and input stderr info."""
        try:
            cmd = [ffmpeg_bin, "-hide_banner", "-i", str(video_path)]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, text=True)
            output = proc.stderr or proc.stdout or ""
            meta.raw_metadata["ffmpeg_i_output"] = output

            # 1. Parse Duration and container bitrate
            # e.g.: Duration: 00:00:29.21, start: 0.000000, bitrate: 9723 kb/s
            dur_match = re.search(r"Duration:\s*(\d+):(\d+):([\d\.]+),\s*start:\s*([\d\.-]+),\s*bitrate:\s*(\d+)\s*kb/s", output)
            if dur_match:
                h = int(dur_match.group(1))
                m = int(dur_match.group(2))
                s = float(dur_match.group(3))
                meta.duration_seconds = round(h * 3600 + m * 60 + s, 2)
                meta.overall_bitrate_kbps = float(dur_match.group(5))

            # 2. Parse Video stream
            # e.g.: Stream #0:0[0x1](und): Video: h264 (Constrained Baseline) (avc1 / 0x31637661), yuv420p(progressive), 1080x1920, 9591 kb/s, 24 fps, ...
            for line in output.splitlines():
                if "Stream #" in line and "Video:" in line:
                    meta.has_video = True
                    meta.video_streams_count += 1

                    # Codec
                    v_codec_match = re.search(r"Video:\s*(\w+)", line)
                    if v_codec_match:
                        meta.video_codec = v_codec_match.group(1).lower()

                    # Profile
                    profile_match = re.search(r"\(([^)]+)\)\s*\(avc1|\(([^)]+)\),", line)
                    if profile_match:
                        meta.video_profile = (profile_match.group(1) or profile_match.group(2) or "").strip().lower()

                    # Pixel format
                    pix_match = re.search(r",\s*([a-zA-Z0-9_]+(?:\([a-zA-Z0-9_]+\))?),\s*(\d+)x(\d+)", line)
                    if pix_match:
                        raw_pix = pix_match.group(1).lower()
                        meta.pixel_format = raw_pix.split("(")[0].strip()
                        meta.width = int(pix_match.group(2))
                        meta.height = int(pix_match.group(3))
                    else:
                        dim_match = re.search(r"(\d{3,4})x(\d{3,4})", line)
                        if dim_match:
                            meta.width = int(dim_match.group(1))
                            meta.height = int(dim_match.group(2))
                        pix_only = re.search(r",\s*(yuv420p|yuv444p|yuvj420p|rgb24|bgr24)", line)
                        if pix_only:
                            meta.pixel_format = pix_only.group(1)

                    if meta.height > 0:
                        meta.aspect_ratio_float = round(meta.width / meta.height, 4)
                        meta.aspect_ratio = f"{meta.width}:{meta.height}"

                    # FPS
                    fps_match = re.search(r",\s*([\d\.]+)\s*fps", line)
                    if fps_match:
                        meta.fps = float(fps_match.group(1))

                    # Video bitrate
                    v_br_match = re.search(r",\s*(\d+)\s*kb/s", line)
                    if v_br_match:
                        meta.video_bitrate_kbps = float(v_br_match.group(1))

                elif "Stream #" in line and "Audio:" in line:
                    meta.has_audio = True
                    meta.audio_streams_count += 1

                    # Codec
                    a_codec_match = re.search(r"Audio:\s*(\w+)", line)
                    if a_codec_match:
                        meta.audio_codec = a_codec_match.group(1).lower()

                    # Sample rate
                    sr_match = re.search(r",\s*(\d+)\s*Hz", line)
                    if sr_match:
                        meta.audio_sample_rate = int(sr_match.group(1))

                    # Channels
                    if "stereo" in line:
                        meta.audio_channels = 2
                    elif "mono" in line:
                        meta.audio_channels = 1
                    else:
                        ch_match = re.search(r",\s*(\d+)\s*channels", line)
                        if ch_match:
                            meta.audio_channels = int(ch_match.group(1))

                    # Audio bitrate
                    a_br_match = re.search(r",\s*(\d+)\s*kb/s", line)
                    if a_br_match:
                        meta.audio_bitrate_kbps = float(a_br_match.group(1))

        except Exception as exc:
            logger.debug(f"ffmpeg -i probe failed: {exc}")

    @classmethod
    def _measure_audio_volume(
        cls,
        ffmpeg_bin: str,
        video_path: Path,
        meta: FFprobeMetadata,
        timeout: float,
    ) -> None:
        """Runs ffmpeg volumedetect filter to determine loudness and silence."""
        try:
            cmd = [
                ffmpeg_bin,
                "-i", str(video_path),
                "-af", "volumedetect",
                "-f", "null",
                "-",
            ]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, text=True)
            err = proc.stderr or ""
            mean_match = re.search(r"mean_volume:\s*([\-\d\.]+)\s*dB", err)
            max_match = re.search(r"max_volume:\s*([\-\d\.]+)\s*dB", err)

            if mean_match:
                meta.audio_mean_volume_db = float(mean_match.group(1))
            if max_match:
                meta.audio_max_volume_db = float(max_match.group(1))

            # Silent if max volume is below -60dB or mean volume is below -80dB
            if meta.audio_max_volume_db <= -60.0 or meta.audio_mean_volume_db <= -80.0:
                meta.is_audio_silent = True
            else:
                meta.is_audio_silent = False
        except Exception as exc:
            logger.debug(f"Volume detect failed: {exc}")

    @classmethod
    def _verify_full_decode(
        cls,
        ffmpeg_bin: str,
        video_path: Path,
        meta: FFprobeMetadata,
        timeout: float,
    ) -> None:
        """
        Runs `ffmpeg -v error -i <file> -f null -` to fully decode all video and audio packets.
        Captures timestamp desyncs, missing moov atoms, corrupted slices, and truncation.
        """
        try:
            cmd = [
                ffmpeg_bin,
                "-v", "error",
                "-i", str(video_path),
                "-f", "null",
                "-",
            ]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, text=True)
            stderr = (proc.stderr or "").strip()

            fatal_indicators = [
                "error",
                "corrupt",
                "invalid data",
                "moov atom not found",
                "truncated",
                "header missing",
                "decoding error",
            ]

            fatal_errors: List[str] = []
            if proc.returncode != 0:
                fatal_errors.append(f"FFmpeg decoding process exited with error code {proc.returncode}")

            if stderr:
                for line in stderr.splitlines():
                    low = line.lower()
                    if any(fi in low for fi in fatal_indicators):
                        fatal_errors.append(line.strip())

            if fatal_errors:
                meta.decode_passed = False
                meta.decode_errors = fatal_errors
            else:
                meta.decode_passed = True
                meta.decode_errors = []

        except subprocess.TimeoutExpired:
            meta.decode_passed = False
            meta.decode_errors = [f"Full decode check timed out after {timeout}s"]
        except Exception as exc:
            meta.decode_passed = False
            meta.decode_errors = [f"Decode check execution failed: {exc}"]
