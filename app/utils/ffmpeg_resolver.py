"""
Centralized FFmpeg Binary Resolver.
Resolves, validates, and caches the authoritative FFmpeg executable across platforms.

Resolution Order:
1. Explicitly configured path: os.getenv("FFMPEG_BINARY") or os.getenv("FFMPEG_PATH").
2. System PATH executable via shutil.which("ffmpeg").
3. imageio_ffmpeg bundled binary via imageio_ffmpeg.get_ffmpeg_exe().
4. Standard platform installation locations (e.g. Program Files, /usr/bin).

Validation:
- Binary must physically exist.
- Binary must be executable.
- Executing `[binary, "-version"]` must return exit code 0 and contain "ffmpeg version".

Thread-safe caching ensures resolution occurs only once during process lifetime.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("FFmpegResolver")

_lock = threading.Lock()
_cached_ffmpeg_binary: Optional[str] = None
_cached_ffmpeg_version: Optional[str] = None
_cached_diagnostics: Optional[Dict[str, Any]] = None


def _validate_binary(binary_path: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Executes [binary_path, "-version"] to verify that the binary can run.
    Returns (is_valid: bool, version_string: Optional[str], error_message: Optional[str]).
    """
    try:
        p = Path(binary_path)
        if not p.is_file():
            return False, None, f"Path does not exist or is not a regular file: {binary_path}"

        # Test execution
        proc = subprocess.run(
            [str(p), "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
            text=True,
        )

        output = proc.stdout or proc.stderr or ""
        if proc.returncode == 0 and "ffmpeg version" in output.lower():
            # Extract first line (e.g. 'ffmpeg version 9.0.2 ...')
            version_line = output.splitlines()[0].strip() if output.splitlines() else "ffmpeg unknown version"
            return True, version_line, None
        else:
            err = (proc.stderr or proc.stdout or f"exit code {proc.returncode}").strip()
            return False, None, f"Execution failed ({err[:120]})"

    except subprocess.TimeoutExpired:
        return False, None, f"Execution timed out (>5s) for {binary_path}"
    except (PermissionError, OSError) as e:
        return False, None, f"Execution permission or OS error: {e}"
    except Exception as e:
        return False, None, f"Unexpected validation error: {e}"


def get_ffmpeg_binary(force_refresh: bool = False) -> Optional[str]:
    """
    Returns the absolute path to the validated FFmpeg binary, or None if unavailable.
    Caches the result unless force_refresh is True.
    """
    global _cached_ffmpeg_binary, _cached_ffmpeg_version, _cached_diagnostics

    with _lock:
        if _cached_ffmpeg_binary is not None and not force_refresh:
            return _cached_ffmpeg_binary

        candidates: List[Tuple[str, str]] = []  # (source_description, path_string)
        attempt_logs: List[Dict[str, Any]] = []

        # 1. Explicit configured environment variables
        env_configured = os.getenv("FFMPEG_BINARY") or os.getenv("FFMPEG_PATH")
        if env_configured and env_configured.strip():
            candidates.append(("Explicit Configuration (FFMPEG_BINARY/FFMPEG_PATH)", env_configured.strip()))

        # 2. System PATH via shutil.which
        system_which = shutil.which("ffmpeg")
        if system_which:
            candidates.append(("System PATH (shutil.which)", system_which))

        # 3. imageio_ffmpeg bundled binary
        try:
            import imageio_ffmpeg
            img_exe = imageio_ffmpeg.get_ffmpeg_exe()
            if img_exe:
                candidates.append(("imageio_ffmpeg bundled binary", img_exe))
        except Exception as e:
            attempt_logs.append({
                "source": "imageio_ffmpeg",
                "candidate": None,
                "valid": False,
                "error": f"Import or lookup failed: {e}",
            })

        # 4. Standard platform directories
        common_locations = [
            "C:\\ffmpeg\\bin\\ffmpeg.exe",
            "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe",
            "C:\\ProgramData\\chocolatey\\bin\\ffmpeg.exe",
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            "/opt/homebrew/bin/ffmpeg",
        ]
        for loc in common_locations:
            if os.path.isfile(loc):
                candidates.append((f"Common Platform Location ({loc})", loc))

        # Test candidates in order of priority
        resolved_bin: Optional[str] = None
        resolved_ver: Optional[str] = None

        for source_name, cand_path in candidates:
            is_valid, ver_str, err_msg = _validate_binary(cand_path)
            attempt_logs.append({
                "source": source_name,
                "candidate": cand_path,
                "valid": is_valid,
                "version": ver_str,
                "error": err_msg,
            })
            if is_valid:
                resolved_bin = str(Path(cand_path).resolve())
                resolved_ver = ver_str
                logger.info(f"[FFmpegResolver] Resolved FFmpeg via {source_name}: {resolved_bin} ({ver_str})")
                break

        _cached_ffmpeg_binary = resolved_bin
        _cached_ffmpeg_version = resolved_ver
        _cached_diagnostics = {
            "resolved": resolved_bin is not None,
            "binary_path": resolved_bin,
            "version": resolved_ver,
            "candidates_evaluated": attempt_logs,
        }

        # If a valid binary was found, ensure its directory is prepended to os.environ["PATH"]
        # so any underlying subprocess or MoviePy call finds it as well
        if resolved_bin:
            bin_dir = str(Path(resolved_bin).parent)
            current_path = os.environ.get("PATH", "")
            if bin_dir.lower() not in current_path.lower():
                os.environ["PATH"] = bin_dir + os.pathsep + current_path

        return _cached_ffmpeg_binary


def is_ffmpeg_available(force_refresh: bool = False) -> bool:
    """Returns True if a valid, executable FFmpeg binary is available."""
    return get_ffmpeg_binary(force_refresh=force_refresh) is not None


def get_ffmpeg_version(binary_path: Optional[str] = None) -> Optional[str]:
    """Returns the version line of the resolved or specified FFmpeg binary."""
    if binary_path:
        is_valid, ver, _ = _validate_binary(binary_path)
        return ver if is_valid else None
    get_ffmpeg_binary()
    return _cached_ffmpeg_version


def get_ffmpeg_diagnostics() -> Dict[str, Any]:
    """Returns structured diagnostic information detailing FFmpeg resolution."""
    if _cached_diagnostics is None:
        get_ffmpeg_binary()
    return _cached_diagnostics or {"resolved": False, "candidates_evaluated": []}
