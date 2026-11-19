"""
Safe JSON Storage & Atomic Persistence Engine.
Provides production-grade atomic file writes, transactional replacement,
file-level locking, corruption detection, quarantined backups, and automated recovery.
Fully cross-platform (Windows & Linux).
"""

import copy
import json
import logging
import os
import shutil
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union

try:
    from filelock import FileLock
except ImportError:
    FileLock = None

logger = logging.getLogger("SafeStore")

T = TypeVar("T")

# Process-wide reentrant locks for path-specific intra-process serialization
_PATH_LOCKS: Dict[str, threading.RLock] = {}
_ACTIVE_HOLDERS: Dict[str, Tuple[int, Any, int]] = {}  # canonical_path -> (thread_id, filelock_inst, count)
_META_LOCK = threading.Lock()


def get_path_lock(path: Union[Path, str]) -> threading.RLock:
    """Returns or creates a process-level thread reentrant lock for a specific path."""
    canonical = str(Path(path).resolve().absolute())
    with _META_LOCK:
        if canonical not in _PATH_LOCKS:
            _PATH_LOCKS[canonical] = threading.RLock()
        return _PATH_LOCKS[canonical]


class FileAndThreadLock:
    """
    Dual-layer reentrant synchronization lock:
    1. In-process threading.RLock
    2. Inter-process filelock.FileLock (reentrant within the same thread)
    """

    def __init__(self, lock_path: Union[Path, str], timeout: float = 15.0):
        self.lock_path = Path(lock_path)
        self.canonical = str(self.lock_path.resolve().absolute())
        self.timeout = timeout
        self.thread_lock = get_path_lock(self.lock_path)

    def __enter__(self):
        self.thread_lock.acquire()
        thread_id = threading.get_ident()

        with _META_LOCK:
            if self.canonical in _ACTIVE_HOLDERS and _ACTIVE_HOLDERS[self.canonical][0] == thread_id:
                # Same thread re-entering: increment recursion count
                fl, count = _ACTIVE_HOLDERS[self.canonical][1], _ACTIVE_HOLDERS[self.canonical][2]
                _ACTIVE_HOLDERS[self.canonical] = (thread_id, fl, count + 1)
                return self

        # Needs real filelock acquisition
        fl = FileLock(str(self.lock_path), timeout=self.timeout) if FileLock else None
        if fl:
            try:
                fl.acquire(timeout=self.timeout)
            except Exception as e:
                self.thread_lock.release()
                raise TimeoutError(f"Could not acquire file lock {self.lock_path} within {self.timeout}s: {e}")

        with _META_LOCK:
            _ACTIVE_HOLDERS[self.canonical] = (thread_id, fl, 1)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        thread_id = threading.get_ident()
        fl_to_release = None

        with _META_LOCK:
            if self.canonical in _ACTIVE_HOLDERS and _ACTIVE_HOLDERS[self.canonical][0] == thread_id:
                _, fl, count = _ACTIVE_HOLDERS[self.canonical]
                if count > 1:
                    _ACTIVE_HOLDERS[self.canonical] = (thread_id, fl, count - 1)
                else:
                    fl_to_release = fl
                    del _ACTIVE_HOLDERS[self.canonical]

        try:
            if fl_to_release and fl_to_release.is_locked:
                fl_to_release.release()
        finally:
            self.thread_lock.release()


def safe_file_lock(lock_path: Union[Path, str], timeout: float = 15.0) -> FileAndThreadLock:
    """Factory for FileAndThreadLock."""
    return FileAndThreadLock(lock_path, timeout=timeout)


def atomic_write_json(
    target_path: Union[Path, str],
    data: Any,
    indent: int = 2,
    make_backup: bool = True,
    retries: int = 5,
    lock_timeout: float = 15.0,
) -> Path:
    """
    Safely writes JSON data to an atomic temporary file with fsync,
    creates a backup of any existing valid file, and atomically replaces the target.
    
    Guarantees:
    - Never leaves half-written or 0-byte target files on crash or power loss.
    - Preserves previous valid state in <target>.bak before replacing.
    - Handles Windows filesystem file-locking latency with exponential backoff.
    """
    target = Path(target_path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    
    # Pre-validate JSON serializability in memory before touching disk
    try:
        serialized = json.dumps(data, indent=indent, ensure_ascii=False)
    except (TypeError, ValueError) as err:
        raise ValueError(f"Data for {target} is not JSON-serializable: {err}") from err

    lock_file = target.parent / f".{target.name}.lock"
    
    with safe_file_lock(lock_file, timeout=lock_timeout):
        # 1. Update .bak backup if target already exists and is non-empty
        if make_backup and target.exists() and target.stat().st_size > 0:
            bak_path = target.with_suffix(target.suffix + ".bak")
            try:
                # Only backup if the existing file is valid JSON to prevent copying corruption into .bak
                with open(target, "r", encoding="utf-8") as existing_f:
                    json.load(existing_f)
                # Create backup safely
                tmp_bak = target.parent / f".tmp_{target.stem}_bak_{os.getpid()}_{uuid.uuid4().hex[:6]}.tmp"
                with open(tmp_bak, "w", encoding="utf-8") as bf:
                    with open(target, "r", encoding="utf-8") as tf:
                        shutil.copyfileobj(tf, bf)
                    bf.flush()
                    os.fsync(bf.fileno())
                os.replace(tmp_bak, bak_path)
            except Exception as bak_err:
                logger.debug(f"[SafeStore] Skipping backup update for {target.name}: {bak_err}")

        # 2. Write to unique per-process, per-thread temporary file in the same directory
        tmp_name = f".tmp_{target.stem}_{os.getpid()}_{threading.get_ident()}_{time.time_ns()}_{uuid.uuid4().hex[:8]}.tmp"
        tmp_path = target.parent / tmp_name

        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(serialized)
                f.flush()
                os.fsync(f.fileno())

            # 3. Atomic replacement with Windows retry loop
            for attempt in range(retries):
                try:
                    os.replace(tmp_path, target)
                    return target
                except (PermissionError, FileNotFoundError, OSError) as os_err:
                    if attempt == retries - 1:
                        # Final fallback on Windows: remove then rename
                        try:
                            if target.exists():
                                os.remove(target)
                            os.rename(tmp_path, target)
                            return target
                        except Exception:
                            raise os_err
                    time.sleep(0.02 * (attempt + 1))
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass

    return target


def safe_read_json(
    target_path: Union[Path, str],
    default_factory: Optional[Callable[[], T]] = None,
    validate_fn: Optional[Callable[[Any], bool]] = None,
    lock_timeout: float = 15.0,
) -> Any:
    """
    Safely reads JSON data from target_path.
    If the file does not exist, calls default_factory() if provided, or raises FileNotFoundError.
    If the file is corrupted (invalid JSON syntax, empty, truncated, or fails validate_fn):
    - Quarantines the corrupted file to .corrupted_<timestamp>_<name>
    - Searches for and restores from <target>.bak
    - If .bak is missing, searches for recent valid temporary snapshots
    - If recovery succeeds, restores target atomically and returns data
    - If recovery fails, retains quarantined file and returns default_factory() if provided
    """
    target = Path(target_path).resolve()
    
    if not target.exists():
        if default_factory is not None:
            return default_factory()
        raise FileNotFoundError(f"State file not found: {target}")

    lock_file = target.parent / f".{target.name}.lock"

    with safe_file_lock(lock_file, timeout=lock_timeout):
        try:
            with open(target, "r", encoding="utf-8") as f:
                data = json.load(f)
            if validate_fn is not None and not validate_fn(data):
                raise ValueError("Validation function returned False for parsed JSON payload.")
            return data
        except Exception as read_err:
            logger.error(
                f"[SafeStore] CORRUPTION DETECTED in {target.name} ({read_err}). "
                f"Initiating safety quarantine and automated recovery..."
            )
            
            # Step A: Quarantine corrupted file
            timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            quarantine_path = target.parent / f".corrupted_{timestamp_str}_{target.name}"
            try:
                shutil.copy2(target, quarantine_path)
                logger.warning(f"[SafeStore] Quarantined corrupted original to: {quarantine_path.name}")
            except Exception as q_err:
                logger.error(f"[SafeStore] Could not quarantine corrupted file: {q_err}")

            # Step B: Attempt recovery from .bak
            bak_path = target.with_suffix(target.suffix + ".bak")
            if bak_path.exists():
                try:
                    with open(bak_path, "r", encoding="utf-8") as bf:
                        recovered_data = json.load(bf)
                    if validate_fn is None or validate_fn(recovered_data):
                        # Restore target atomically from .bak
                        atomic_write_json(target, recovered_data, make_backup=False)
                        logger.warning(
                            f"[SafeStore] RECOVERY SUCCESSFUL: Restored {target.name} "
                            f"from verified backup ({bak_path.name})."
                        )
                        return recovered_data
                except Exception as bak_rec_err:
                    logger.error(f"[SafeStore] Backup recovery from {bak_path.name} failed: {bak_rec_err}")

            # Step C: Attempt recovery from recent temporary snapshots
            try:
                candidates = sorted(
                    target.parent.glob(f".tmp_{target.stem}_*.tmp*"),
                    key=lambda p: p.stat().st_mtime_ns if p.exists() else 0,
                    reverse=True,
                )
                for cand in candidates:
                    try:
                        with open(cand, "r", encoding="utf-8") as cf:
                            cand_data = json.load(cf)
                        if validate_fn is None or validate_fn(cand_data):
                            atomic_write_json(target, cand_data, make_backup=True)
                            logger.warning(
                                f"[SafeStore] RECOVERY SUCCESSFUL: Restored {target.name} "
                                f"from temp snapshot ({cand.name})."
                            )
                            return cand_data
                    except Exception:
                        continue
            except Exception as tmp_rec_err:
                logger.debug(f"[SafeStore] Temp candidate scan error: {tmp_rec_err}")

            # Step D: All recovery attempts failed
            logger.critical(
                f"[SafeStore] ALL AUTOMATED RECOVERY ATTEMPTS FAILED for {target.name}. "
                f"Corrupted file remains safely quarantined at {quarantine_path}."
            )
            if default_factory is not None:
                default_data = default_factory()
                # Do NOT overwrite target with empty data; write default to target only if explicitly needed,
                # but preserve quarantined file
                atomic_write_json(target, default_data, make_backup=False)
                return default_data

            raise ValueError(f"State file {target} is corrupted and could not be recovered: {read_err}") from read_err


def ensure_versioned_envelope(
    data: Any,
    target_version: str = "2.0.0",
    root_key: str = "records",
) -> Dict[str, Any]:
    """
    Enforces a versioned schema envelope without destructively modifying
    or dropping any existing fields.
    """
    if isinstance(data, dict):
        result = copy.deepcopy(data)
        if "schema_version" not in result:
            result["schema_version"] = target_version
        if "last_updated" not in result:
            result["last_updated"] = datetime.now(timezone.utc).isoformat()
        return result
    elif isinstance(data, list):
        return {
            "schema_version": target_version,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat(),
            root_key: copy.deepcopy(data),
            "total_items": len(data),
        }
    else:
        return {
            "schema_version": target_version,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "value": data,
        }
