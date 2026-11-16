import os
import sys
from pathlib import Path
import pytest

# Ensure project root is in sys.path for all test collection
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def isolate_test_visual_registries(tmp_path, monkeypatch):
    """
    Automatic test isolation fixture:
    1. Diverts PermanentVisualMemory and DynamicVisualEngine to an isolated temporary registry.
    2. Resets all in-memory caches and sets.
    3. Enables TESTING mode to prevent live external network timeouts.
    4. Guarantees no test pollutes the production registry on disk.
    """
    test_storage = tmp_path / "storage"
    test_storage.mkdir(parents=True, exist_ok=True)
    test_broll = tmp_path / "assets" / "generated_broll"
    test_broll.mkdir(parents=True, exist_ok=True)

    perm_file = test_storage / "permanent_visual_registry.json"
    legacy_file = test_storage / "used_visuals_registry.json"
    lock_file = test_storage / "visual_memory.lock"

    monkeypatch.setattr("app.storage.permanent_visual_memory.STORAGE_DIR", test_storage)
    monkeypatch.setattr("app.storage.permanent_visual_memory.PERMANENT_REGISTRY_FILE", perm_file)
    monkeypatch.setattr("app.storage.permanent_visual_memory.LEGACY_REGISTRY_FILE", legacy_file)
    monkeypatch.setattr("app.storage.permanent_visual_memory.LOCK_FILE", lock_file)

    monkeypatch.setattr("app.video.dynamic_visual_engine.USED_REGISTRY_FILE", legacy_file)

    monkeypatch.setenv("TESTING", "true")

    from app.storage.permanent_visual_memory import PermanentVisualMemory
    from app.video.dynamic_visual_engine import DynamicVisualEngine

    PermanentVisualMemory._cache_loaded = False
    PermanentVisualMemory._records = {}
    PermanentVisualMemory._sha256_set = set()
    PermanentVisualMemory._source_identities = set()
    PermanentVisualMemory._last_disk_mtime_ns = 0
    PermanentVisualMemory._last_disk_size = 0

    DynamicVisualEngine._session_used_urls = set()
    DynamicVisualEngine._session_used_hashes = set()

    yield

    # Clean up state after test
    PermanentVisualMemory._cache_loaded = False
    PermanentVisualMemory._records = {}
    PermanentVisualMemory._sha256_set = set()
    PermanentVisualMemory._source_identities = set()
    PermanentVisualMemory._last_disk_mtime_ns = 0
    PermanentVisualMemory._last_disk_size = 0

    DynamicVisualEngine._session_used_urls = set()
    DynamicVisualEngine._session_used_hashes = set()
