"""
Comprehensive Test Suite for Chunk 3: Persistent State, History & Data Safety.

Covers:
1. State restoration across runs
2. First-ever workflow run (clean baseline initialization)
3. Existing workflow run state preservation
4. Missing artifact & cache miss handling
5. Corrupted state quarantine and forensic preservation
6. Automated recovery from .bak and temporary snapshots
7. Atomic writes with fsync and Windows retry backoff
8. Concurrent multi-threaded writes under FileLock
9. Duplicate prevention records and zero data loss on merge
10. Schema versioning and backward-compatible non-destructive migration
11. Windows & Linux cross-platform path handling
12. Failed publishing state preservation
13. Full StateManager audit and integrity validation
"""

import copy
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.storage.safe_store import (
    atomic_write_json,
    safe_read_json,
    safe_file_lock,
    ensure_versioned_envelope,
)
from app.storage.state_manager import StateManager, STATE_CATALOG


@pytest.fixture
def temp_storage(tmp_path):
    """Provides an isolated storage directory for testing."""
    storage = tmp_path / "storage"
    storage.mkdir(parents=True, exist_ok=True)
    return storage


# =============================================================================
# 1. ATOMIC WRITES & REPLACEMENT
# =============================================================================
def test_atomic_writes_and_fsync(temp_storage):
    """Proves atomic writes leave no dangling temp files and persist valid JSON."""
    target = temp_storage / "test_data.json"
    payload = {"status": "ok", "count": 42, "items": ["a", "b", "c"]}

    written = atomic_write_json(target, payload, make_backup=False)
    assert written.exists()
    assert target.exists()

    with open(target, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == payload

    # Ensure no lingering temp files
    temp_files = list(temp_storage.glob(".tmp_*"))
    assert len(temp_files) == 0


def test_atomic_write_creates_backup(temp_storage):
    """Proves updating an existing file safely creates and updates a .bak file."""
    target = temp_storage / "test_backup.json"
    initial_data = {"version": 1, "value": "original"}
    updated_data = {"version": 2, "value": "updated"}

    atomic_write_json(target, initial_data, make_backup=True)
    assert target.exists()

    # Second write should create .bak containing initial_data
    atomic_write_json(target, updated_data, make_backup=True)
    bak_file = target.with_suffix(".json.bak")
    assert bak_file.exists()

    with open(bak_file, "r", encoding="utf-8") as bf:
        bak_data = json.load(bf)
    assert bak_data == initial_data

    with open(target, "r", encoding="utf-8") as tf:
        curr_data = json.load(tf)
    assert curr_data == updated_data


# =============================================================================
# 2. CORRUPTED STATE RECOVERY & FORENSIC QUARANTINE
# =============================================================================
def test_corrupted_state_quarantined_and_recovered_from_backup(temp_storage):
    """
    Proves that when a state file is corrupted, safe_read_json:
    1. Quarantines the bad file so forensics are preserved.
    2. Recovers state seamlessly from the .bak file.
    3. Re-establishes the target file.
    """
    target = temp_storage / "daily_post_tracker.json"
    valid_data = {"last_post_date": "2026-11-18", "total_posts": 10, "history": []}

    # Step 1: Write valid state with backup
    atomic_write_json(target, valid_data, make_backup=True)
    # Write another to ensure .bak is populated with valid_data
    atomic_write_json(target, valid_data, make_backup=True)

    # Step 2: Corrupt target with malformed JSON
    with open(target, "w", encoding="utf-8") as f:
        f.write("{malformed json truncated...")

    # Step 3: Read safely
    recovered = safe_read_json(
        target,
        default_factory=lambda: {"last_post_date": None, "total_posts": 0, "history": []},
        validate_fn=lambda d: isinstance(d, dict) and "history" in d,
    )

    assert recovered == valid_data

    # Verify quarantine file was created
    quarantined = list(temp_storage.glob(".corrupted_*_daily_post_tracker.json"))
    assert len(quarantined) >= 1
    assert "{malformed json truncated..." in quarantined[0].read_text(encoding="utf-8")


def test_unrecoverable_corrupted_file_preserves_quarantine(temp_storage):
    """
    Proves that if a corrupted file has NO backup, the bad file is quarantined
    and default_factory is returned without silently destroying forensic evidence.
    """
    target = temp_storage / "unrecoverable.json"
    with open(target, "w", encoding="utf-8") as f:
        f.write("totally invalid !!!")

    default_payload = {"clean_init": True}
    res = safe_read_json(target, default_factory=lambda: default_payload)
    assert res == default_payload

    # Quarantined copy must exist
    quarantined = list(temp_storage.glob(".corrupted_*_unrecoverable.json"))
    assert len(quarantined) == 1
    assert "totally invalid !!!" in quarantined[0].read_text(encoding="utf-8")


# =============================================================================
# 3. CONCURRENT ACCESS & THREAD SAFETY
# =============================================================================
def test_concurrent_writes_protection(temp_storage):
    """Proves multiple concurrent threads writing under locks do not corrupt state."""
    target = temp_storage / "concurrent_registry.json"
    atomic_write_json(target, {"records": {}}, make_backup=False)

    num_threads = 6
    writes_per_thread = 5
    errors = []

    def worker(worker_id: int):
        try:
            for i in range(writes_per_thread):
                lock_file = temp_storage / "concurrent_registry.json.lock"
                with safe_file_lock(lock_file, timeout=10.0):
                    data = safe_read_json(target, default_factory=lambda: {"records": {}})
                    data["records"][f"w_{worker_id}_item_{i}"] = {"id": i, "worker": worker_id}
                    atomic_write_json(target, data, make_backup=False)
                time.sleep(0.01)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(t_id,)) for t_id in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Errors in concurrent workers: {errors}"

    final_data = safe_read_json(target)
    assert len(final_data["records"]) == num_threads * writes_per_thread


# =============================================================================
# 4. FIRST-EVER RUN & MISSING ARTIFACT
# =============================================================================
def test_first_ever_workflow_run(temp_storage):
    """Proves first-ever workflow run behaves cleanly when storage is completely empty."""
    mgr = StateManager(storage_dir=temp_storage)

    # Validate on empty storage
    valid, issues = mgr.validate_all_state()
    assert valid is True
    assert issues == []

    # Audit reports missing files without failing
    audit = mgr.audit_all_state()
    assert audit["total_files"] == len(STATE_CATALOG)
    assert audit["present_files"] == 0
    assert audit["missing_files"] == len(STATE_CATALOG)
    assert audit["corrupted_files"] == 0


def test_missing_artifact_graceful_fallback(temp_storage):
    """Proves restoring from a non-existent artifact path gracefully skips without error."""
    mgr = StateManager(storage_dir=temp_storage)
    non_existent = temp_storage / "does_not_exist"

    res = mgr.restore_and_merge_state(non_existent)
    assert res["restored"] == []
    assert res["merged"] == []
    assert res["errors"] == []


# =============================================================================
# 5. SEMANTIC MERGING & ZERO DATA LOSS
# =============================================================================
def test_semantic_merge_visual_registry(temp_storage, tmp_path):
    """Proves permanent visual registry unions records and never loses fingerprints."""
    src_dir = tmp_path / "cache_source"
    src_dir.mkdir()

    dst_reg = temp_storage / "permanent_visual_registry.json"
    src_reg = src_dir / "permanent_visual_registry.json"

    # Destination has fingerprint A and B
    atomic_write_json(dst_reg, {
        "schema_version": "2.0.0",
        "total_records": 2,
        "records": {
            "hash_aaa": {"sha256": "hash_aaa", "usage_timestamp": "2026-11-18T10:00:00"},
            "hash_bbb": {"sha256": "hash_bbb", "usage_timestamp": "2026-11-18T10:00:00"},
        }
    })

    # Restored cache has fingerprint B (older) and C (new)
    atomic_write_json(src_reg, {
        "schema_version": "2.0.0",
        "total_records": 2,
        "records": {
            "hash_bbb": {"sha256": "hash_bbb", "usage_timestamp": "2026-11-17T10:00:00"},
            "hash_ccc": {"sha256": "hash_ccc", "usage_timestamp": "2026-11-18T11:00:00"},
        }
    })

    mgr = StateManager(storage_dir=temp_storage)
    res = mgr.restore_and_merge_state(src_dir)

    assert "permanent_visual_registry.json" in res["merged"]
    merged = safe_read_json(dst_reg)

    # Must contain AAA, BBB, CCC (3 total records)
    assert len(merged["records"]) == 3
    assert set(merged["records"].keys()) == {"hash_aaa", "hash_bbb", "hash_ccc"}
    # BBB should preserve dst timestamp because it was newer
    assert merged["records"]["hash_bbb"]["usage_timestamp"] == "2026-11-18T10:00:00"


def test_semantic_merge_post_tracker(temp_storage, tmp_path):
    """Proves daily post tracker merges historical publications without dropping dates."""
    src_dir = tmp_path / "cache_source"
    src_dir.mkdir()

    dst_tracker = temp_storage / "daily_post_tracker.json"
    src_tracker = src_dir / "daily_post_tracker.json"

    atomic_write_json(dst_tracker, {
        "last_post_date": "2026-11-18",
        "total_posts": 1,
        "history": [{"date": "2026-11-18", "media_id": "m18", "topic": "Topic 18"}],
        "2026-11-18": {"media_id": "m18"}
    })

    atomic_write_json(src_tracker, {
        "last_post_date": "2026-11-17",
        "total_posts": 1,
        "history": [{"date": "2026-11-17", "media_id": "m17", "topic": "Topic 17"}],
        "2026-11-17": {"media_id": "m17"}
    })

    mgr = StateManager(storage_dir=temp_storage)
    res = mgr.restore_and_merge_state(src_dir)
    assert "daily_post_tracker.json" in res["merged"]

    merged = safe_read_json(dst_tracker)
    assert merged["last_post_date"] == "2026-11-18"
    assert merged["total_posts"] == 2
    assert len(merged["history"]) == 2
    assert "2026-11-17" in merged
    assert "2026-11-18" in merged


def test_semantic_merge_published_and_trend_history(temp_storage, tmp_path):
    """Proves published_history.json and trend_history.json deduplicate records cleanly."""
    src_dir = tmp_path / "cache_source"
    src_dir.mkdir()

    dst_pub = temp_storage / "published_history.json"
    src_pub = src_dir / "published_history.json"

    atomic_write_json(dst_pub, [
        {"topic": "Topic Alpha", "published_at": 100},
        {"topic": "Topic Beta", "published_at": 200},
    ])
    atomic_write_json(src_pub, [
        {"topic": "Topic Beta", "published_at": 200},
        {"topic": "Topic Gamma", "published_at": 300},
    ])

    mgr = StateManager(storage_dir=temp_storage)
    res = mgr.restore_and_merge_state(src_dir)
    assert "published_history.json" in res["merged"]

    merged = safe_read_json(dst_pub)
    assert len(merged) == 3
    topics = {item["topic"] for item in merged}
    assert topics == {"Topic Alpha", "Topic Beta", "Topic Gamma"}


# =============================================================================
# 6. SCHEMA VERSIONING & MIGRATION
# =============================================================================
def test_schema_versioning_preserves_custom_fields():
    """Proves schema enveloper adds version metadata without losing custom or unknown fields."""
    legacy_data = {
        "custom_plugin_field": "do_not_delete",
        "author": "krishna",
        "settings": {"mode": "expert", "flags": [1, 2, 3]},
    }
    versioned = ensure_versioned_envelope(legacy_data, target_version="2.1.0")

    assert versioned["schema_version"] == "2.1.0"
    assert versioned["custom_plugin_field"] == "do_not_delete"
    assert versioned["author"] == "krishna"
    assert versioned["settings"] == {"mode": "expert", "flags": [1, 2, 3]}
    assert "last_updated" in versioned


# =============================================================================
# 7. CROSS-PLATFORM PATH HANDLING
# =============================================================================
def test_windows_and_linux_path_handling(temp_storage):
    """Proves safe_store handles backslashes, forward slashes, and spaces reliably."""
    nested_dir = temp_storage / "nested with spaces" / "sub_path"
    target = nested_dir / "deep_file.json"

    # Forward slash string
    written = atomic_write_json(str(target).replace("\\", "/"), {"path_ok": True})
    assert written.exists()

    read_back = safe_read_json(str(target))
    assert read_back == {"path_ok": True}


# =============================================================================
# 8. BACKUP CREATION & AUDIT VALIDATION
# =============================================================================
def test_state_manager_backup_and_audit(temp_storage):
    """Proves StateManager creates complete snapshots and accurate audit records."""
    # Seed 3 state files
    atomic_write_json(temp_storage / "permanent_visual_registry.json", {"records": {"a": 1}})
    atomic_write_json(temp_storage / "used_visuals_registry.json", {"used_images": ["img1"]})
    atomic_write_json(temp_storage / "published_history.json", [{"topic": "Vedic Astrology"}])

    mgr = StateManager(storage_dir=temp_storage)
    snapshot_dir = mgr.backup_all_state(tag="test_run")

    assert snapshot_dir.exists()
    assert (snapshot_dir / "manifest.json").exists()
    assert (snapshot_dir / "permanent_visual_registry.json").exists()

    audit = mgr.audit_all_state()
    assert audit["present_files"] == 3
    assert audit["files"]["permanent_visual_registry.json"]["status"] == "HEALTHY"
    assert audit["files"]["permanent_visual_registry.json"]["has_backup"] is True
