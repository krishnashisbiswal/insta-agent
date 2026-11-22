"""
Isolated Production Workspace & Artifact Lifecycle Management.

Ensures every Reel production runs in a unique, isolated directory:
  output/productions/production_YYYYMMDD_HHMMSS_<job_id>/
    ├── final_video.mp4
    ├── validation.json
    ├── metadata.json
    └── qc_contact_sheet.jpg

Prevents stale artifacts, eliminates reliance on shared fixed filenames,
and isolates artifacts for verification, quarantine, and audit trails.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRODUCTIONS_BASE_DIR = PROJECT_ROOT / "output" / "productions"
QUARANTINE_BASE_DIR = PROJECT_ROOT / "output" / "quarantine"

logger = logging.getLogger("ProductionWorkspace")


def compute_file_sha256(file_path: Union[Path, str], block_size: int = 65536) -> str:
    """Computes SHA-256 hash of a file on disk."""
    p = Path(file_path)
    if not p.is_file():
        raise FileNotFoundError(f"File not found for hashing: {p}")
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(block_size):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class ProductionJobWorkspace:
    """Represents an isolated filesystem workspace for a single Reel generation job."""
    job_id: str
    workspace_dir: Path
    created_at_epoch: float
    video_path: Path
    validation_path: Path
    metadata_path: Path
    contact_sheet_path: Path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "workspace_dir": str(self.workspace_dir.resolve()),
            "created_at_epoch": self.created_at_epoch,
            "video_path": str(self.video_path.resolve()),
            "validation_path": str(self.validation_path.resolve()),
            "metadata_path": str(self.metadata_path.resolve()),
            "contact_sheet_path": str(self.contact_sheet_path.resolve()),
        }

    def save_metadata(self, metadata: Dict[str, Any]) -> None:
        """Saves job metadata safely."""
        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def quarantine_artifacts(self, reason: str) -> Path:
        """
        Moves the workspace to quarantine on validation rejection.
        Preserves complete artifacts for inspection and debugging without risk of reuse.
        """
        QUARANTINE_BASE_DIR.mkdir(parents=True, exist_ok=True)
        dest = QUARANTINE_BASE_DIR / f"rejected_{self.workspace_dir.name}"
        if dest.exists():
            dest = QUARANTINE_BASE_DIR / f"rejected_{self.workspace_dir.name}_{int(time.time())}"
        
        # Write failure note
        try:
            note_path = self.workspace_dir / "REJECTION_REASON.txt"
            note_path.write_text(f"Rejected at {time.ctime()}\nReason: {reason}\n", encoding="utf-8")
        except Exception:
            pass

        shutil.move(str(self.workspace_dir), str(dest))
        logger.warning(f"[ProductionWorkspace] Quarantined rejected job {self.job_id} to {dest}")
        return dest


class ProductionWorkspaceManager:
    """
    Factory for creating and managing isolated Reel production directories.
    """

    @classmethod
    def create_workspace(
        cls,
        job_id: Optional[str] = None,
        prefix: str = "production",
    ) -> ProductionJobWorkspace:
        """
        Creates a dedicated production workspace directory with timestamp and UUID.
        Example: output/productions/production_20261122_231500_a1b2c3d4/
        """
        now = time.time()
        dt_str = datetime.fromtimestamp(now).strftime("%Y%m%d_%H%M%S")
        jid = job_id or uuid.uuid4().hex[:8]
        dir_name = f"{prefix}_{dt_str}_{jid}"

        ws_dir = PRODUCTIONS_BASE_DIR / dir_name
        ws_dir.mkdir(parents=True, exist_ok=True)

        return ProductionJobWorkspace(
            job_id=jid,
            workspace_dir=ws_dir,
            created_at_epoch=now,
            video_path=ws_dir / "final_video.mp4",
            validation_path=ws_dir / "validation.json",
            metadata_path=ws_dir / "metadata.json",
            contact_sheet_path=ws_dir / "qc_contact_sheet.jpg",
        )
