"""
Comprehensive Production Test Suite for:
1. Permanent Visual Memory (Multi-Algorithm Cryptographic & Perceptual Fingerprints)
2. Exact and Near-Duplicate Visual Rejection (Resized, Renamed, Recompressed)
3. Asset Lifecycle State Machine (GENERATED -> VALIDATED -> UPLOADING -> PUBLISHED -> VERIFIED -> CLEANED)
4. Post-Publication Verified Cleanup Guard
5. Preservation of Permanent Registry during and after cleanup
6. Failure and Pending State Protection (Failed uploads NEVER trigger premature cleanup)
7. Concurrency Protection (Concurrent workflows cannot lose registry updates)
8. Safety Path Boundaries (Strict protection against deleting files outside designated temp directories)
"""

import json
import os
import shutil
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from PIL import Image
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.storage.permanent_visual_memory import PermanentVisualMemory
from app.storage.asset_lifecycle_manager import AssetLifecycleManager, JobState


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    """Sets up an isolated storage & output environment for lifecycle testing."""
    test_storage = tmp_path / "storage"
    test_storage.mkdir(parents=True, exist_ok=True)
    test_output = tmp_path / "output"
    test_output.mkdir(parents=True, exist_ok=True)
    test_broll = tmp_path / "assets" / "generated_broll"
    test_broll.mkdir(parents=True, exist_ok=True)
    test_insta = tmp_path / "insta content"
    test_insta.mkdir(parents=True, exist_ok=True)

    perm_file = test_storage / "permanent_visual_registry.json"
    legacy_file = test_storage / "used_visuals_registry.json"
    lock_file = test_storage / "visual_memory.lock"
    jobs_file = test_storage / "asset_lifecycle_jobs.json"
    jobs_lock = test_storage / "asset_lifecycle.lock"

    monkeypatch.setattr("app.storage.permanent_visual_memory.PERMANENT_REGISTRY_FILE", perm_file)
    monkeypatch.setattr("app.storage.permanent_visual_memory.LEGACY_REGISTRY_FILE", legacy_file)
    monkeypatch.setattr("app.storage.permanent_visual_memory.LOCK_FILE", lock_file)

    monkeypatch.setattr("app.storage.asset_lifecycle_manager.STORAGE_DIR", test_storage)
    monkeypatch.setattr("app.storage.asset_lifecycle_manager.JOBS_REGISTRY_FILE", jobs_file)
    monkeypatch.setattr("app.storage.asset_lifecycle_manager.JOBS_LOCK_FILE", jobs_lock)
    monkeypatch.setattr("app.storage.asset_lifecycle_manager.PROJECT_ROOT", tmp_path)
    monkeypatch.setattr("app.storage.asset_lifecycle_manager.FAILED_REELS_DIR", test_output / "failed_reels")
    monkeypatch.setattr(
        "app.storage.asset_lifecycle_manager.DESIGNATED_TEMP_DIRS",
        [
            test_output / "audio",
            test_output / "frames",
            test_output / "reels",
            test_broll,
            test_insta,
        ],
    )
    monkeypatch.setattr(
        "app.storage.asset_lifecycle_manager.PROTECTED_DIRS",
        [
            test_storage,
            tmp_path / "config",
            tmp_path / "app",
            tmp_path / "tests",
        ],
    )

    PermanentVisualMemory._cache_loaded = False
    PermanentVisualMemory._records = {}
    PermanentVisualMemory._sha256_set = set()
    PermanentVisualMemory._source_identities = set()

    return {
        "root": tmp_path,
        "storage": test_storage,
        "output": test_output,
        "broll": test_broll,
        "insta": test_insta,
        "perm_file": perm_file,
    }


def create_synthetic_image(path: Path, color=(140, 60, 20), size=(1080, 1920)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", size, color)
    img.save(str(path), format="JPEG", quality=95)
    return path


# =============================================================================
# TEST 1: IMAGES ARE REMOVED AFTER VERIFIED PUBLISHING
# =============================================================================
def test_images_removed_after_verified_publishing(isolated_env):
    """Proves disposable images and video files are removed after verified publishing."""
    broll_dir = isolated_env["broll"]
    insta_dir = isolated_env["insta"]

    img1 = create_synthetic_image(broll_dir / "scene1_test.jpg", color=(200, 50, 50))
    img2 = create_synthetic_image(broll_dir / "scene2_test.jpg", color=(50, 200, 50))
    video_file = create_synthetic_image(insta_dir / "viral_reel_video.mp4", color=(10, 10, 10))

    assert img1.exists()
    assert img2.exists()
    assert video_file.exists()

    job_id = AssetLifecycleManager.create_job(
        topic="5 Mukhi Rudraksha Benefits",
        script_id="script_test_101",
        scene_images=[img1, img2],
        video_path=video_file,
    )

    # Move to PUBLISHED then VERIFIED
    AssetLifecycleManager.record_published(job_id, media_id="ig_media_12345", media_code="Cxyz123")
    AssetLifecycleManager.mark_verified(job_id, verified_source="live_api_check")

    report = AssetLifecycleManager.run_cleanup_job(job_id)

    assert report["status"] == "SUCCESS"
    assert report["assets_deleted_count"] >= 3
    assert report["storage_reclaimed_bytes"] > 0
    assert not img1.exists(), "Scene image 1 should be deleted after verified cleanup"
    assert not img2.exists(), "Scene image 2 should be deleted after verified cleanup"
    assert not video_file.exists(), "Rendered video should be deleted after verified cleanup"


# =============================================================================
# TEST 2: FINGERPRINTS REMAIN AFTER DELETION
# =============================================================================
def test_fingerprints_remain_after_deletion(isolated_env):
    """Proves fingerprints remain in durable storage even after source images are deleted."""
    broll_dir = isolated_env["broll"]
    img = create_synthetic_image(broll_dir / "gemstone_sapphire.jpg", color=(10, 30, 180))
    fp_before = PermanentVisualMemory.compute_fingerprints(img)

    job_id = AssetLifecycleManager.create_job(
        topic="Blue Sapphire Placement",
        script_id="script_sapphire_01",
        scene_images=[img],
    )
    AssetLifecycleManager.record_published(job_id, media_id="ig_media_sapphire")
    AssetLifecycleManager.mark_verified(job_id)

    # Execute cleanup
    AssetLifecycleManager.run_cleanup_job(job_id)

    # File is deleted
    assert not img.exists()

    # Fingerprint record is fully preserved in permanent visual memory
    stats = PermanentVisualMemory.get_stats()
    assert stats["total_fingerprints"] >= 1

    registry_data = PermanentVisualMemory.load_registry()
    record = registry_data["records"].get(fp_before["sha256"])

    assert record is not None, "Fingerprint record must remain after file deletion"
    assert record["sha256"] == fp_before["sha256"]
    assert record["phash"] == fp_before["phash"]
    assert record["dhash"] == fp_before["dhash"]
    assert record["reel_id"] == "ig_media_sapphire"
    assert record["script_id"] == "script_sapphire_01"


# =============================================================================
# TEST 3: NEXT WORKFLOW DETECTS PREVIOUSLY USED IMAGES (EXACT & NEAR-DUPLICATE)
# =============================================================================
def test_next_workflow_run_detects_previously_used_images(isolated_env):
    """
    Proves that even after physical deletion of an image, any subsequent workflow run
    immediately detects and rejects:
    1. The exact same image bytes.
    2. A renamed variant.
    3. A resized variant.
    4. A recompressed JPEG variant.
    """
    broll_dir = isolated_env["broll"]
    orig_path = create_synthetic_image(broll_dir / "original_pyrite.jpg", color=(218, 165, 32))

    # Commit original to permanent memory and then delete the file
    PermanentVisualMemory.record_used_visual(
        orig_path,
        source_identity="original_pyrite.jpg",
        script_id="script_pyrite_prev",
        reel_id="reel_pyrite_prev",
    )
    orig_path.unlink()
    assert not orig_path.exists()

    # 1. Exact bytes detection
    fresh_identical = create_synthetic_image(broll_dir / "fresh_identical.jpg", color=(218, 165, 32))
    is_dup, reason, _ = PermanentVisualMemory.check_duplicate(fresh_identical)
    assert is_dup is True, f"Identical image should be rejected! Reason: {reason}"
    assert "Exact" in reason or "match" in reason

    # 2. Renamed copy
    renamed = create_synthetic_image(broll_dir / "completely_different_name.jpg", color=(218, 165, 32))
    is_dup, reason, _ = PermanentVisualMemory.check_duplicate(renamed)
    assert is_dup is True, f"Renamed variant should be rejected! Reason: {reason}"

    # 3. Resized copy (720x1280 down to 360x640)
    resized_path = broll_dir / "resized_copy.jpg"
    with Image.open(renamed) as im:
        im.resize((360, 640)).save(str(resized_path), format="JPEG", quality=95)
    is_dup, reason, _ = PermanentVisualMemory.check_duplicate(resized_path)
    assert is_dup is True, f"Resized near-duplicate should be rejected! Reason: {reason}"
    assert "pHash" in reason or "near-duplicate" in reason or "dHash" in reason

    # 4. Recompressed copy (quality=60)
    recompressed_path = broll_dir / "recompressed_copy.jpg"
    with Image.open(renamed) as im:
        im.save(str(recompressed_path), format="JPEG", quality=60)
    is_dup, reason, _ = PermanentVisualMemory.check_duplicate(recompressed_path)
    assert is_dup is True, f"Recompressed near-duplicate should be rejected! Reason: {reason}"


# =============================================================================
# TEST 4: CLEANUP NEVER REMOVES THE PERMANENT REGISTRY
# =============================================================================
def test_cleanup_never_removes_the_permanent_registry(isolated_env):
    """Proves the permanent registry file is preserved and uncorrupted during cleanup."""
    broll_dir = isolated_env["broll"]
    perm_file = isolated_env["perm_file"]

    img = create_synthetic_image(broll_dir / "test_item.jpg")
    job_id = AssetLifecycleManager.create_job(
        topic="Test Topic",
        script_id="script_test_00",
        scene_images=[img],
    )
    AssetLifecycleManager.record_published(job_id, media_id="media_test_00")
    AssetLifecycleManager.mark_verified(job_id)

    # Run cleanup
    AssetLifecycleManager.run_cleanup_job(job_id)

    assert perm_file.exists(), "Permanent registry must NEVER be deleted during cleanup!"
    assert perm_file.stat().st_size > 50, "Permanent registry must contain valid data"

    with open(perm_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "records" in data
    assert len(data["records"]) >= 1


# =============================================================================
# TEST 5: FAILED AND PENDING UPLOADS DO NOT TRIGGER PREMATURE CLEANUP
# =============================================================================
def test_failed_and_pending_uploads_do_not_trigger_cleanup(isolated_env):
    """
    Proves that cleanup strictly refuses to run on:
    1. GENERATED jobs (not uploaded)
    2. UPLOADING jobs (pending)
    3. FAILED jobs (upload failed)
    Assets are retained safely.
    """
    broll_dir = isolated_env["broll"]
    img1 = create_synthetic_image(broll_dir / "pending_img.jpg", color=(90, 80, 70))
    img2 = create_synthetic_image(broll_dir / "failed_img.jpg", color=(10, 20, 30))

    # Case 1: Job in GENERATED state
    job_gen = AssetLifecycleManager.create_job(
        topic="Generated Pending",
        script_id="script_pending",
        scene_images=[img1],
    )
    with pytest.raises(RuntimeError, match="Refusing cleanup"):
        AssetLifecycleManager.run_cleanup_job(job_gen)
    assert img1.exists(), "Image must NOT be cleaned when job is only GENERATED"

    # Case 2: Job in UPLOADING state
    AssetLifecycleManager.update_job_state(job_gen, JobState.UPLOADING, message="Uploading...")
    with pytest.raises(RuntimeError, match="Refusing cleanup"):
        AssetLifecycleManager.run_cleanup_job(job_gen)
    assert img1.exists(), "Image must NOT be cleaned when upload is in progress"

    # Case 3: Job in FAILED state
    job_fail = AssetLifecycleManager.create_job(
        topic="Failed Upload",
        script_id="script_fail",
        scene_images=[img2],
    )
    AssetLifecycleManager.mark_failed(job_fail, error_message="Instagram Graph API 500 error")
    with pytest.raises(RuntimeError, match="Refusing cleanup"):
        AssetLifecycleManager.run_cleanup_job(job_fail)
    assert img2.exists(), "Image must NOT be cleaned when upload failed"


# =============================================================================
# TEST 6: CONCURRENT WORKFLOWS CANNOT LOSE REGISTRY UPDATES
# =============================================================================
def test_concurrent_workflows_cannot_lose_registry_updates(isolated_env):
    """Proves that multiple concurrent threads updating permanent visual memory do not lose records."""
    num_threads = 6
    records_per_thread = 5
    errors = []

    def worker(worker_id: int):
        try:
            for i in range(records_per_thread):
                unique_color = (
                    (worker_id * 35 + i * 5) % 255,
                    (worker_id * 50 + i * 10) % 255,
                    (worker_id * 70 + i * 15) % 255,
                )
                img = Image.new("RGB", (64, 64), color=unique_color)
                PermanentVisualMemory.record_used_visual(
                    image_input=img,
                    source_identity=f"thread_{worker_id}_img_{i}_{uuid.uuid4().hex[:6]}",
                    script_id=f"script_th_{worker_id}",
                    reel_id=f"reel_th_{worker_id}",
                )
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(t_id,)) for t_id in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Concurrent updates produced errors: {errors}"

    stats = PermanentVisualMemory.get_stats()
    expected_new = num_threads * records_per_thread
    assert stats["total_fingerprints"] >= expected_new, (
        f"Expected at least {expected_new} fingerprints, but found {stats['total_fingerprints']}"
    )


# =============================================================================
# TEST 7: SAFETY PATH BOUNDARIES BLOCK DELETION OUTSIDE DESIGNATED DIRECTORIES
# =============================================================================
def test_safety_path_boundaries(isolated_env):
    """Proves safety guard blocks deletion of files outside designated temporary directories."""
    root = isolated_env["root"]
    storage_dir = isolated_env["storage"]

    # File inside storage (protected)
    protected_file = storage_dir / "important_data.json"
    protected_file.write_text("{}", encoding="utf-8")

    assert AssetLifecycleManager.is_safe_temp_path(protected_file) is False

    # File in project root (protected)
    root_file = root / "system_file.py"
    root_file.write_text("# code", encoding="utf-8")
    assert AssetLifecycleManager.is_safe_temp_path(root_file) is False

    # File in designated broll directory (safe)
    broll_file = isolated_env["broll"] / "temp_scene.jpg"
    assert AssetLifecycleManager.is_safe_temp_path(broll_file) is True
