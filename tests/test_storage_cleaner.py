import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.storage_cleaner import StorageCleaner


def test_clean_intermediate_generation_data():
    # Create dummy intermediate files
    audio_dir = PROJECT_ROOT / "output" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    dummy_sc = audio_dir / "scene_test_dummy_123.mp3"
    dummy_sc.write_text("dummy audio content")

    res = StorageCleaner.clean_intermediate_generation_data()
    assert res["files_removed"] >= 1
    assert not dummy_sc.exists()
