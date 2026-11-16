"""
Storage Cleaner & Auto-Purge Engine (Production Hardened).

Automatically manages disk hygiene:
1. Intermediate Cleanup: Purges scene audio chunks, frame caches, and MoviePy temp buffers.
2. Post-Publishing Cleanup: Safely purges rendered video files and intermediate b-roll
   according to a retention policy once confirmed posted on Instagram.
3. Dry-Run Support: Allows previewing cleanup actions without deleting files.
4. Permanent Memory Preservation: Guarantees visual fingerprints and publishing metadata
   are NEVER deleted.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("StorageCleaner")

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Designated Temporary Directories (Strict Safety Boundaries)
DESIGNATED_TEMP_DIRS: List[Path] = [
    PROJECT_ROOT / "output" / "audio",
    PROJECT_ROOT / "output" / "frames",
    PROJECT_ROOT / "output" / "reels",
    PROJECT_ROOT / "output" / "rudraksha_nov15_frames",
    PROJECT_ROOT / "output" / "test_verified_frames",
    PROJECT_ROOT / "assets" / "generated_broll",
    PROJECT_ROOT / "insta content",
]

# Protected Directories (NEVER TOUCHED)
PROTECTED_DIRS: List[Path] = [
    PROJECT_ROOT / "storage",
    PROJECT_ROOT / "config",
    PROJECT_ROOT / "app",
    PROJECT_ROOT / "tests",
    PROJECT_ROOT / ".git",
    PROJECT_ROOT / ".venv",
]


class StorageCleaner:
    """
    Manages autonomous disk hygiene:
    1. Intermediate Cleanup: Purges scene audio chunks, frame caches, and MoviePy temp buffers.
    2. Post-Publishing Cleanup: Purges rendered video files and intermediate b-roll once confirmed posted on Instagram.
    3. Dry-run mode: Previews deletions without unlinking files.
    """

    @classmethod
    def _is_safe_to_delete(cls, file_path: Path) -> bool:
        """Ensures file is strictly within designated temp dirs and not protected."""
        try:
            resolved = file_path.resolve()
            # Ensure not within any protected directory
            for prot in PROTECTED_DIRS:
                try:
                    resolved.relative_to(prot.resolve())
                    return False  # Inside a protected directory!
                except ValueError:
                    pass

            # Ensure within at least one designated temp dir
            for allowed in DESIGNATED_TEMP_DIRS:
                try:
                    resolved.relative_to(allowed.resolve())
                    return True
                except ValueError:
                    pass

            # Direct temp files in PROJECT_ROOT (e.g. *TEMP_MPY*)
            if resolved.parent == PROJECT_ROOT.resolve() and "TEMP_MPY" in resolved.name:
                return True

            return False
        except Exception:
            return False

    @classmethod
    def clean_intermediate_generation_data(
        cls,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Deletes temporary scene audio chunks, frame renders, and MoviePy buffers
        generated during reel composition.
        """
        freed_bytes = 0
        removed_count = 0
        removed_files: List[str] = []

        # 1. Clean output/audio/ (scene_*.mp3, temp wavs)
        audio_dir = PROJECT_ROOT / "output" / "audio"
        if audio_dir.exists():
            for pattern in ["scene_*.mp3", "*.wav", "temp_*.mp3"]:
                for f in audio_dir.glob(pattern):
                    if not cls._is_safe_to_delete(f):
                        continue
                    try:
                        size = f.stat().st_size
                        freed_bytes += size
                        removed_count += 1
                        removed_files.append(str(f))
                        if not dry_run:
                            f.unlink()
                    except Exception as e:
                        logger.debug(f"Could not remove {f.name}: {e}")

        # 2. Clean output/frames/ and frame_sample_*.jpg
        frames_dir = PROJECT_ROOT / "output" / "frames"
        if frames_dir.exists():
            for f in frames_dir.glob("*.jpg"):
                if not cls._is_safe_to_delete(f):
                    continue
                try:
                    size = f.stat().st_size
                    freed_bytes += size
                    removed_count += 1
                    removed_files.append(str(f))
                    if not dry_run:
                        f.unlink()
                except Exception as e:
                    logger.debug(f"Could not remove {f.name}: {e}")

        output_dir = PROJECT_ROOT / "output"
        if output_dir.exists():
            for f in output_dir.glob("frame_sample_*.jpg"):
                if not cls._is_safe_to_delete(f):
                    continue
                try:
                    size = f.stat().st_size
                    freed_bytes += size
                    removed_count += 1
                    removed_files.append(str(f))
                    if not dry_run:
                        f.unlink()
                except Exception as e:
                    logger.debug(f"Could not remove {f.name}: {e}")

        # 3. Clean any lingering MoviePy temp files (*TEMP_MPY*)
        for p in [PROJECT_ROOT / "output" / "reels", PROJECT_ROOT / "insta content", PROJECT_ROOT]:
            if p.exists():
                for f in p.glob("*TEMP_MPY*"):
                    if not cls._is_safe_to_delete(f):
                        continue
                    try:
                        size = f.stat().st_size
                        freed_bytes += size
                        removed_count += 1
                        removed_files.append(str(f))
                        if not dry_run:
                            f.unlink()
                    except Exception as e:
                        logger.debug(f"Could not remove {f.name}: {e}")

        freed_mb = round(freed_bytes / (1024 * 1024), 2)
        mode_label = "[DRY-RUN] " if dry_run else ""
        logger.info(f"[StorageCleaner] {mode_label}Cleaned {removed_count} intermediate generation files, freed {freed_mb} MB.")
        return {
            "files_removed": removed_count,
            "freed_mb": freed_mb,
            "freed_bytes": freed_bytes,
            "removed_files": removed_files,
            "dry_run": dry_run,
        }

    @classmethod
    def clean_post_publishing_data(
        cls,
        keep_latest_reel: bool = False,
        clean_generated_broll: bool = True,
        retention_days: int = 7,
        keep_reels_count: int = 3,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Executed after video has been successfully posted to Instagram.
        Deletes heavy video files and intermediate b-roll to reclaim maximum disk space,
        subject to configurable retention limits.
        
        Guarantees:
        - Image hashes and fingerprints in storage/used_visuals_registry.json and
          storage/permanent_visual_registry.json are NEVER deleted.
        """
        # First clean intermediate generation files
        inter_stats = cls.clean_intermediate_generation_data(dry_run=dry_run)
        freed_bytes = inter_stats["freed_bytes"]
        removed_count = inter_stats["files_removed"]
        removed_files = list(inter_stats.get("removed_files", []))
        retained_reels: List[str] = []

        now = time.time()
        retention_seconds = retention_days * 86400

        # 1. Clean historical reels in output/reels/
        reels_dir = PROJECT_ROOT / "output" / "reels"
        if reels_dir.exists():
            reels = sorted(reels_dir.glob("*.mp4"), key=lambda f: f.stat().st_mtime)
            
            if keep_latest_reel:
                # Keep up to keep_reels_count newest reels
                keep_count = max(1, keep_reels_count)
                to_delete = reels[:-keep_count] if len(reels) > keep_count else []
                retained_reels.extend([r.name for r in reels[-keep_count:]])
            else:
                to_delete = reels

            for r in to_delete:
                if not cls._is_safe_to_delete(r):
                    continue
                try:
                    # Enforce retention age: only delete if older than retention_days or keep_latest_reel is False
                    mtime = r.stat().st_mtime
                    if (now - mtime) >= retention_seconds or not keep_latest_reel:
                        size = r.stat().st_size
                        freed_bytes += size
                        removed_count += 1
                        removed_files.append(str(r))
                        if not dry_run:
                            r.unlink()
                            logger.info(f"[StorageCleaner] Purged posted reel: {r.name}")
                    else:
                        retained_reels.append(r.name)
                except Exception as e:
                    logger.debug(f"Could not remove reel {r.name}: {e}")

        # 2. Clean published video from insta content/
        if not keep_latest_reel:
            insta_video = PROJECT_ROOT / "insta content" / "viral_reel_video.mp4"
            if insta_video.exists() and cls._is_safe_to_delete(insta_video):
                try:
                    size = insta_video.stat().st_size
                    freed_bytes += size
                    removed_count += 1
                    removed_files.append(str(insta_video))
                    if not dry_run:
                        insta_video.unlink()
                        logger.info("[StorageCleaner] Purged published video from insta content/.")
                except Exception as e:
                    logger.debug(f"Could not remove insta content video: {e}")

            insta_audio = PROJECT_ROOT / "insta content" / "voiceover_audio.mp3"
            if insta_audio.exists() and cls._is_safe_to_delete(insta_audio):
                try:
                    size = insta_audio.stat().st_size
                    freed_bytes += size
                    removed_count += 1
                    removed_files.append(str(insta_audio))
                    if not dry_run:
                        insta_audio.unlink()
                except Exception as e:
                    logger.debug(f"Could not remove insta content audio: {e}")

        # 3. Clean generated b-roll in assets/generated_broll/
        if clean_generated_broll:
            broll_dir = PROJECT_ROOT / "assets" / "generated_broll"
            if broll_dir.exists():
                for f in broll_dir.glob("*.jpg"):
                    if not cls._is_safe_to_delete(f):
                        continue
                    try:
                        size = f.stat().st_size
                        freed_bytes += size
                        removed_count += 1
                        removed_files.append(str(f))
                        if not dry_run:
                            f.unlink()
                    except Exception as e:
                        logger.debug(f"Could not remove broll {f.name}: {e}")

        freed_mb = round(freed_bytes / (1024 * 1024), 2)
        mode_label = "[DRY-RUN] " if dry_run else ""
        logger.info(f"[StorageCleaner] {mode_label}Total cleanup complete: {removed_count} files removed, freed {freed_mb} MB.")
        return {
            "files_removed": removed_count,
            "freed_mb": freed_mb,
            "freed_bytes": freed_bytes,
            "removed_files": removed_files,
            "retained_reels": retained_reels,
            "dry_run": dry_run,
        }


if __name__ == "__main__":
    import sys
    print("Running StorageCleaner dry-run...")
    res = StorageCleaner.clean_intermediate_generation_data(dry_run=True)
    print(f"Dry-run: Would clean {res['files_removed']} files, freeing {res['freed_mb']} MB.")
