"""
Storage Cleaner & Auto-Purge Engine
Automatically clears disk space by deleting intermediate audio chunks, temporary video frames,
MoviePy temp files, and uploaded video files once published to Instagram.
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("StorageCleaner")

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class StorageCleaner:
    """
    Manages autonomous disk hygiene:
    1. Intermediate Cleanup: Purges scene audio chunks, frame caches, and MoviePy temp buffers.
    2. Post-Publishing Cleanup: Purges rendered video files and intermediate b-roll once confirmed posted on Instagram.
    """

    @classmethod
    def clean_intermediate_generation_data(cls) -> Dict[str, Any]:
        """
        Deletes temporary scene audio chunks, frame renders, and MoviePy buffers
        generated during reel composition.
        """
        freed_bytes = 0
        removed_count = 0

        # 1. Clean output/audio/ (scene_*.mp3, temp wavs)
        audio_dir = PROJECT_ROOT / "output" / "audio"
        if audio_dir.exists():
            for f in audio_dir.glob("scene_*.mp3"):
                try:
                    freed_bytes += f.stat().st_size
                    f.unlink()
                    removed_count += 1
                except Exception as e:
                    logger.debug(f"Could not remove {f.name}: {e}")

            for f in audio_dir.glob("*.wav"):
                try:
                    freed_bytes += f.stat().st_size
                    f.unlink()
                    removed_count += 1
                except Exception as e:
                    logger.debug(f"Could not remove {f.name}: {e}")

        # 2. Clean output/frames/ and frame_sample_*.jpg
        frames_dir = PROJECT_ROOT / "output" / "frames"
        if frames_dir.exists():
            for f in frames_dir.glob("*.jpg"):
                try:
                    freed_bytes += f.stat().st_size
                    f.unlink()
                    removed_count += 1
                except Exception as e:
                    logger.debug(f"Could not remove {f.name}: {e}")

        for f in (PROJECT_ROOT / "output").glob("frame_sample_*.jpg"):
            try:
                freed_bytes += f.stat().st_size
                f.unlink()
                removed_count += 1
            except Exception as e:
                logger.debug(f"Could not remove {f.name}: {e}")

        # 3. Clean any lingering MoviePy temp files (*TEMP_MPY*)
        for p in [PROJECT_ROOT / "output" / "reels", PROJECT_ROOT / "insta content", PROJECT_ROOT]:
            if p.exists():
                for f in p.glob("*TEMP_MPY*"):
                    try:
                        freed_bytes += f.stat().st_size
                        f.unlink()
                        removed_count += 1
                    except Exception as e:
                        logger.debug(f"Could not remove {f.name}: {e}")

        freed_mb = round(freed_bytes / (1024 * 1024), 2)
        logger.info(f"[StorageCleaner] Cleaned {removed_count} intermediate generation files, freed {freed_mb} MB.")
        return {
            "files_removed": removed_count,
            "freed_mb": freed_mb,
        }

    @classmethod
    def clean_post_publishing_data(
        cls,
        keep_latest_reel: bool = False,
        clean_generated_broll: bool = True,
    ) -> Dict[str, Any]:
        """
        Executed after video has been successfully posted to Instagram.
        Deletes heavy video files and intermediate b-roll to reclaim maximum disk space.
        Note: Image hashes/names remain logged in storage/used_visuals_registry.json
        so visual diversity is permanently preserved even after deleting the image files.
        """
        # First clean intermediate generation files
        inter_stats = cls.clean_intermediate_generation_data()
        freed_bytes = int(inter_stats["freed_mb"] * 1024 * 1024)
        removed_count = inter_stats["files_removed"]

        # 1. Clean historical reels in output/reels/
        reels_dir = PROJECT_ROOT / "output" / "reels"
        if reels_dir.exists():
            reels = sorted(reels_dir.glob("*.mp4"), key=lambda f: f.stat().st_mtime)
            # If keep_latest_reel is True, keep the newest one; otherwise delete all
            to_delete = reels[:-1] if keep_latest_reel and reels else reels
            for r in to_delete:
                try:
                    freed_bytes += r.stat().st_size
                    r.unlink()
                    removed_count += 1
                    logger.info(f"[StorageCleaner] Purged posted reel: {r.name}")
                except Exception as e:
                    logger.debug(f"Could not remove reel {r.name}: {e}")

        # 2. Clean published video from insta content/
        if not keep_latest_reel:
            insta_video = PROJECT_ROOT / "insta content" / "viral_reel_video.mp4"
            if insta_video.exists():
                try:
                    freed_bytes += insta_video.stat().st_size
                    insta_video.unlink()
                    removed_count += 1
                    logger.info("[StorageCleaner] Purged published video from insta content/.")
                except Exception as e:
                    logger.debug(f"Could not remove insta content video: {e}")

            insta_audio = PROJECT_ROOT / "insta content" / "voiceover_audio.mp3"
            if insta_audio.exists():
                try:
                    freed_bytes += insta_audio.stat().st_size
                    insta_audio.unlink()
                    removed_count += 1
                except Exception as e:
                    logger.debug(f"Could not remove insta content audio: {e}")

        # 3. Clean generated b-roll in assets/generated_broll/
        if clean_generated_broll:
            broll_dir = PROJECT_ROOT / "assets" / "generated_broll"
            if broll_dir.exists():
                for f in broll_dir.glob("*.jpg"):
                    try:
                        freed_bytes += f.stat().st_size
                        f.unlink()
                        removed_count += 1
                    except Exception as e:
                        logger.debug(f"Could not remove broll {f.name}: {e}")

        freed_mb = round(freed_bytes / (1024 * 1024), 2)
        logger.info(f"[StorageCleaner] Total cleanup complete: {removed_count} files removed, freed {freed_mb} MB.")
        return {
            "files_removed": removed_count,
            "freed_mb": freed_mb,
        }


if __name__ == "__main__":
    import sys
    print("Running StorageCleaner manual cleanup...")
    res = StorageCleaner.clean_intermediate_generation_data()
    print(f"Cleaned {res['files_removed']} files, freed {res['freed_mb']} MB.")
