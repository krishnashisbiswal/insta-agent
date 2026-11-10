"""
Headless Blender 3D Renderer Integration.

Detects system Blender installation, coordinates headless renders,
and falls back safely with honest status reporting when Blender is unavailable.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BlenderRenderer:
    """
    Headless Blender CLI Renderer.
    """

    def __init__(self, blender_path: Optional[str] = None):
        self.blender_bin = blender_path or os.getenv("BLENDER_PATH") or shutil.which("blender")

    @property
    def is_available(self) -> bool:
        return bool(self.blender_bin and Path(self.blender_bin).exists() if os.path.isabs(self.blender_bin or "") else self.blender_bin)

    def check_status(self) -> Dict[str, Any]:
        if not self.is_available:
            return {
                "available": False,
                "status": "BLOCKED",
                "message": "Blender is not installed or not found in system PATH. Install Blender and set BLENDER_PATH.",
            }

        try:
            res = subprocess.run(
                [self.blender_bin, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            version_line = res.stdout.splitlines()[0] if res.stdout else "Blender"
            return {
                "available": True,
                "status": "READY",
                "binary": self.blender_bin,
                "version": version_line,
            }
        except Exception as exc:
            return {
                "available": False,
                "status": "ERROR",
                "message": f"Failed to execute Blender CLI: {exc}",
            }

    def render_script(
        self,
        script_path: Path,
        output_path: Path,
        blend_file: Optional[Path] = None,
        timeout: int = 180,
    ) -> Dict[str, Any]:
        """
        Executes a headless python rendering script inside Blender.
        """
        if not self.is_available:
            return {
                "success": False,
                "status": "BLOCKED",
                "fallback_required": True,
                "message": "Blender binary unavailable; fallback to procedural 3D or visual engine.",
            }

        cmd = [self.blender_bin, "-b"]
        if blend_file and blend_file.exists():
            cmd.extend([str(blend_file)])
        cmd.extend(["-P", str(script_path)])

        try:
            logger.info(f"Executing Blender headless command: {' '.join(cmd)}")
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if res.returncode == 0 and output_path.exists():
                return {
                    "success": True,
                    "status": "RENDERED",
                    "output_path": str(output_path),
                }
            else:
                return {
                    "success": False,
                    "status": "FAILED",
                    "error": res.stderr[:500] if res.stderr else "Blender exited with non-zero status",
                    "fallback_required": True,
                }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "status": "TIMEOUT",
                "error": f"Blender render timed out after {timeout} seconds",
                "fallback_required": True,
            }
        except Exception as exc:
            return {
                "success": False,
                "status": "ERROR",
                "error": str(exc),
                "fallback_required": True,
            }
