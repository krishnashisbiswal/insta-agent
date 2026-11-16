import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.storage_cleaner import StorageCleaner


def test_clean_intermediate_generation_data():
    audio_dir = PROJECT_ROOT / "output" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    dummy_sc = audio_dir / "scene_test_dummy_123.mp3"
    dummy_sc.write_text("dummy audio content")

    res = StorageCleaner.clean_intermediate_generation_data()
    assert res["files_removed"] >= 1
    assert not dummy_sc.exists()


def test_clean_dry_run_mode():
    audio_dir = PROJECT_ROOT / "output" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    dummy_dry = audio_dir / "scene_test_dry_run.mp3"
    dummy_dry.write_text("dry run audio content")

    try:
        res = StorageCleaner.clean_intermediate_generation_data(dry_run=True)
        assert res["dry_run"] is True
        assert res["files_removed"] >= 1
        # In dry run, file must NOT be deleted
        assert dummy_dry.exists()
    finally:
        if dummy_dry.exists():
            dummy_dry.unlink()


def test_protected_dirs_never_deleted():
    storage_file = PROJECT_ROOT / "storage" / "permanent_visual_registry.json"
    assert StorageCleaner._is_safe_to_delete(storage_file) is False

    app_file = PROJECT_ROOT / "app" / "main.py"
    assert StorageCleaner._is_safe_to_delete(app_file) is False


def test_post_publishing_cleanup_retention():
    reels_dir = PROJECT_ROOT / "output" / "reels"
    reels_dir.mkdir(parents=True, exist_ok=True)
    dummy_reel = reels_dir / "test_retention_reel.mp4"
    dummy_reel.write_text("fake mp4 content")

    try:
        res = StorageCleaner.clean_post_publishing_data(
            keep_latest_reel=True,
            clean_generated_broll=False,
            retention_days=30,  # Far in the future, should retain
            keep_reels_count=5,
            dry_run=False,
        )
        assert dummy_reel.name in res["retained_reels"]
        assert dummy_reel.exists()
    finally:
        if dummy_reel.exists():
            dummy_reel.unlink()
