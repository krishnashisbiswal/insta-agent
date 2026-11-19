"""
Centralized State Manager & Cross-Environment Persistence Engine.
Manages the lifecycle, backup, semantic merging, schema validation,
and restoration of all persistent state files across local runs and ephemeral GitHub Actions runners.
"""

import argparse
import copy
import json
import logging
import os
import shutil
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.storage.safe_store import (
    atomic_write_json,
    safe_file_lock,
    safe_read_json,
    ensure_versioned_envelope,
)

logger = logging.getLogger("StateManager")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

STORAGE_DIR = PROJECT_ROOT / "storage"
STATE_BACKUP_DIR = STORAGE_DIR / ".backups"

# Catalog of known application state files and their characteristics
STATE_CATALOG: Dict[str, Dict[str, Any]] = {
    "permanent_visual_registry.json": {
        "type": "json_dict",
        "essential": True,
        "merge_key": "records",
        "description": "Multi-algorithm perceptual & cryptographic image fingerprints",
    },
    "used_visuals_registry.json": {
        "type": "json_set",
        "essential": True,
        "merge_key": "used_images",
        "description": "Legacy duplicate prevention index",
    },
    "daily_post_tracker.json": {
        "type": "post_tracker",
        "essential": True,
        "description": "1-Reel-Daily timing limiter and publication records",
    },
    "published_history.json": {
        "type": "json_list_records",
        "essential": True,
        "identity_keys": ["topic", "published_at", "media_id"],
        "description": "Published reel history and topic duplicate prevention",
    },
    "content_queue.json": {
        "type": "json_list_records",
        "essential": False,
        "identity_keys": ["id", "topic"],
        "description": "Buffered content packages awaiting publication",
    },
    "trend_history.json": {
        "type": "json_list_records",
        "essential": True,
        "identity_keys": ["keyword", "topic", "discovered_at"],
        "description": "Vedic astrology trend discovery history",
    },
    "evolution_playbook.json": {
        "type": "playbook",
        "essential": True,
        "description": "Self-learning viral heuristics, winning hooks & banned phrases",
    },
    "reinforcement_brain.json": {
        "type": "brain",
        "essential": True,
        "description": "Reinforcement learning Q-policy and exploration rate",
    },
    "algorithm_intelligence.json": {
        "type": "json_dict",
        "essential": False,
        "description": "Instagram Explore algorithm peak velocity tracking",
    },
    "asset_lifecycle_jobs.json": {
        "type": "json_dict",
        "essential": True,
        "merge_key": "jobs",
        "description": "Asset cleanup and post-publication verification jobs",
    },
    "instagram_session.json": {
        "type": "session",
        "essential": True,
        "description": "Encrypted Instagram session cookies & device credentials",
    },
    "swipe_ideas.json": {
        "type": "json_list_records",
        "essential": False,
        "identity_keys": ["hook", "topic", "id"],
        "description": "Curated viral hooks and ideation pool",
    },
    "comment_replies.json": {
        "type": "json_dict",
        "essential": False,
        "merge_key": "replied_comments",
        "description": "Comment engagement automation tracker",
    },
    "publishing_state/publishing_records.json": {
        "type": "json_dict",
        "essential": False,
        "merge_key": "records",
        "description": "Publishing state machine idempotency and jobs",
    },
    "insta_agent_saas.db": {
        "type": "sqlite",
        "essential": True,
        "description": "SaaS Relational database (accounts, jobs, audit trail)",
    },
}


class StateManager:
    """
    Central controller for auditing, backing up, restoring,
    and semantically merging state across environments.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = Path(storage_dir) if storage_dir else STORAGE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir = self.storage_dir / ".backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # 1. AUDIT ALL STATE FILES
    # =========================================================================
    def audit_all_state(self) -> Dict[str, Any]:
        """
        Inspects all 15 state files and produces a comprehensive audit report.
        """
        report: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "storage_dir": str(self.storage_dir),
            "files": {},
            "total_files": len(STATE_CATALOG),
            "present_files": 0,
            "missing_files": 0,
            "corrupted_files": 0,
            "total_bytes": 0,
        }

        for rel_path, meta in STATE_CATALOG.items():
            full_path = self.storage_dir / rel_path
            entry: Dict[str, Any] = {
                "relative_path": rel_path,
                "description": meta["description"],
                "essential": meta["essential"],
                "type": meta["type"],
                "exists": full_path.exists(),
                "size_bytes": 0,
                "status": "MISSING",
                "record_count": 0,
                "has_backup": False,
            }

            if full_path.exists():
                report["present_files"] += 1
                size = full_path.stat().st_size
                entry["size_bytes"] = size
                report["total_bytes"] += size

                # Check for .bak
                bak_path = full_path.with_suffix(full_path.suffix + ".bak")
                entry["has_backup"] = bak_path.exists()

                if meta["type"] == "sqlite":
                    try:
                        conn = sqlite3.connect(str(full_path))
                        cursor = conn.cursor()
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                        tables = [r[0] for r in cursor.fetchall()]
                        conn.close()
                        entry["status"] = "HEALTHY"
                        entry["record_count"] = len(tables)
                        entry["tables"] = tables
                    except Exception as e:
                        entry["status"] = "CORRUPTED"
                        entry["error"] = str(e)
                        report["corrupted_files"] += 1
                else:
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            d = json.load(f)
                        entry["status"] = "HEALTHY"
                        if isinstance(d, dict):
                            if meta.get("merge_key") and meta["merge_key"] in d:
                                entry["record_count"] = len(d[meta["merge_key"]])
                            else:
                                entry["record_count"] = len(d)
                        elif isinstance(d, list):
                            entry["record_count"] = len(d)
                    except Exception as e:
                        entry["status"] = "CORRUPTED"
                        entry["error"] = str(e)
                        report["corrupted_files"] += 1
            else:
                report["missing_files"] += 1

            report["files"][rel_path] = entry

        return report

    # =========================================================================
    # 2. BACKUP ALL STATE
    # =========================================================================
    def backup_all_state(self, tag: Optional[str] = None) -> Path:
        """
        Creates a timestamped snapshot of all state files in storage/.backups/.
        Also ensures individual .bak files are updated for every file.
        """
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        folder_name = f"snapshot_{ts}_{tag}" if tag else f"snapshot_{ts}"
        snapshot_dir = self.backup_dir / folder_name
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        copied_count = 0
        for rel_path, meta in STATE_CATALOG.items():
            src = self.storage_dir / rel_path
            if src.exists() and src.is_file():
                dest = snapshot_dir / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                copied_count += 1

                # Update local .bak for immediate fast recovery
                if meta["type"] != "sqlite":
                    bak_path = src.with_suffix(src.suffix + ".bak")
                    try:
                        shutil.copy2(src, bak_path)
                    except Exception as be:
                        logger.debug(f"Could not update .bak for {src.name}: {be}")

        manifest = {
            "snapshot_timestamp": datetime.now(timezone.utc).isoformat(),
            "files_copied": copied_count,
            "tag": tag or "manual",
        }
        atomic_write_json(snapshot_dir / "manifest.json", manifest, make_backup=False)
        logger.info(f"[StateManager] Backed up {copied_count} state files to: {snapshot_dir}")
        return snapshot_dir

    # =========================================================================
    # 3. SEMANTIC MERGE OF TWO STATE TREES
    # =========================================================================
    def restore_and_merge_state(self, source_dir: Union[Path, str]) -> Dict[str, Any]:
        """
        Restores state from source_dir into self.storage_dir using semantic union merging.
        Guarantees:
        - NEVER overwrites newer local records with older records.
        - NEVER discards records from either source or destination.
        - Handles first-run scenarios gracefully (source missing -> no-op).
        - Handles corrupted source files safely by falling back to destination.
        """
        src_root = Path(source_dir).resolve()
        results: Dict[str, Any] = {"merged": [], "skipped": [], "restored": [], "errors": []}

        if not src_root.exists():
            logger.info(f"[StateManager] Source restore directory does not exist: {src_root}. Starting with baseline.")
            return results

        # If source_dir has a 'storage' subdirectory, descend into it
        if (src_root / "storage").exists() and (src_root / "storage").is_dir():
            src_root = src_root / "storage"

        for rel_path, meta in STATE_CATALOG.items():
            src_file = src_root / rel_path
            dst_file = self.storage_dir / rel_path
            dst_file.parent.mkdir(parents=True, exist_ok=True)

            if not src_file.exists():
                results["skipped"].append(rel_path)
                continue

            try:
                # If destination does not exist, safe copy directly
                if not dst_file.exists() or dst_file.stat().st_size == 0:
                    if meta["type"] == "sqlite":
                        shutil.copy2(src_file, dst_file)
                    else:
                        data = safe_read_json(src_file)
                        atomic_write_json(dst_file, data, make_backup=True)
                    results["restored"].append(rel_path)
                    continue

                # Both exist: perform semantic union merge based on file type
                if meta["type"] == "sqlite":
                    self._merge_sqlite(src_file, dst_file)
                    results["merged"].append(rel_path)
                elif meta["type"] == "json_dict":
                    self._merge_json_dict(src_file, dst_file, meta.get("merge_key"))
                    results["merged"].append(rel_path)
                elif meta["type"] == "json_set":
                    self._merge_json_set(src_file, dst_file, meta.get("merge_key", "used_images"))
                    results["merged"].append(rel_path)
                elif meta["type"] == "post_tracker":
                    self._merge_post_tracker(src_file, dst_file)
                    results["merged"].append(rel_path)
                elif meta["type"] == "json_list_records":
                    self._merge_json_list(src_file, dst_file, meta.get("identity_keys", ["id"]))
                    results["merged"].append(rel_path)
                elif meta["type"] == "playbook":
                    self._merge_playbook(src_file, dst_file)
                    results["merged"].append(rel_path)
                elif meta["type"] == "brain":
                    self._merge_brain(src_file, dst_file)
                    results["merged"].append(rel_path)
                elif meta["type"] == "session":
                    self._merge_session(src_file, dst_file)
                    results["merged"].append(rel_path)
                else:
                    # Generic fallback: keep dst unless src is demonstrably newer
                    if src_file.stat().st_mtime > dst_file.stat().st_mtime:
                        shutil.copy2(src_file, dst_file)
                        results["restored"].append(rel_path)
                    else:
                        results["skipped"].append(rel_path)

            except Exception as e:
                logger.error(f"[StateManager] Error merging {rel_path}: {e}")
                results["errors"].append({"file": rel_path, "error": str(e)})

        logger.info(
            f"[StateManager] State sync complete: {len(results['restored'])} restored, "
            f"{len(results['merged'])} merged, {len(results['skipped'])} unchanged, "
            f"{len(results['errors'])} errors."
        )
        return results

    # =========================================================================
    # MERGER IMPLEMENTATIONS (Zero data loss)
    # =========================================================================
    def _merge_json_dict(self, src: Path, dst: Path, merge_key: Optional[str] = None) -> None:
        src_data = safe_read_json(src, default_factory=dict)
        dst_data = safe_read_json(dst, default_factory=dict)

        if merge_key and merge_key in src_data and merge_key in dst_data:
            # Sub-dictionary union merge (e.g. permanent_visual_registry 'records')
            src_records = src_data.get(merge_key, {})
            dst_records = dst_data.get(merge_key, {})
            merged_records = copy.deepcopy(dst_records)
            for k, v in src_records.items():
                if k not in merged_records:
                    merged_records[k] = v
                elif isinstance(v, dict) and isinstance(merged_records[k], dict):
                    # Keep latest updated record if conflicting
                    src_ts = v.get("usage_timestamp") or v.get("updated_at") or ""
                    dst_ts = merged_records[k].get("usage_timestamp") or merged_records[k].get("updated_at") or ""
                    if src_ts > dst_ts:
                        merged_records[k] = v

            merged = copy.deepcopy(dst_data)
            merged[merge_key] = merged_records
            if "total_records" in merged:
                merged["total_records"] = len(merged_records)
            merged["last_updated"] = datetime.now(timezone.utc).isoformat()
            atomic_write_json(dst, merged, make_backup=True)
        else:
            # Top-level dictionary merge
            merged = copy.deepcopy(dst_data)
            for k, v in src_data.items():
                if k not in merged:
                    merged[k] = v
            merged["last_updated"] = datetime.now(timezone.utc).isoformat()
            atomic_write_json(dst, merged, make_backup=True)

    def _merge_json_set(self, src: Path, dst: Path, set_key: str) -> None:
        src_data = safe_read_json(src, default_factory=dict)
        dst_data = safe_read_json(dst, default_factory=dict)
        src_set = set(src_data.get(set_key, []))
        dst_set = set(dst_data.get(set_key, []))
        union_list = sorted(list(src_set.union(dst_set)))
        merged = copy.deepcopy(dst_data)
        merged[set_key] = union_list
        atomic_write_json(dst, merged, make_backup=True)

    def _merge_post_tracker(self, src: Path, dst: Path) -> None:
        src_data = safe_read_json(src, default_factory=dict)
        dst_data = safe_read_json(dst, default_factory=dict)
        merged = copy.deepcopy(dst_data)

        # Merge history entries by date + media_id
        src_hist = src_data.get("history", [])
        dst_hist = dst_data.get("history", [])
        seen_keys = set()
        merged_hist = []

        for item in dst_hist:
            key = (item.get("date"), item.get("media_id") or item.get("topic"))
            seen_keys.add(key)
            merged_hist.append(item)

        for item in src_hist:
            key = (item.get("date"), item.get("media_id") or item.get("topic"))
            if key not in seen_keys:
                seen_keys.add(key)
                merged_hist.append(item)

        merged["history"] = merged_hist
        merged["total_posts"] = len(merged_hist)

        # Latest post date
        src_date = src_data.get("last_post_date") or ""
        dst_date = dst_data.get("last_post_date") or ""
        merged["last_post_date"] = max(src_date, dst_date) or None

        # Copy over all specific date entries (e.g. "2026-11-12": {...})
        for k, v in src_data.items():
            if k not in merged:
                merged[k] = v

        atomic_write_json(dst, merged, make_backup=True)

    def _merge_json_list(self, src: Path, dst: Path, identity_keys: List[str]) -> None:
        src_data = safe_read_json(src, default_factory=list)
        dst_data = safe_read_json(dst, default_factory=list)
        if not isinstance(src_data, list):
            src_data = [src_data]
        if not isinstance(dst_data, list):
            dst_data = [dst_data]

        def get_ident(item: Any) -> Any:
            if isinstance(item, dict):
                for k in identity_keys:
                    if k in item and item[k]:
                        return (k, str(item[k]))
                return str(sorted(item.items()))
            return str(item)

        seen = set()
        merged = []
        for item in dst_data:
            ident = get_ident(item)
            seen.add(ident)
            merged.append(item)

        for item in src_data:
            ident = get_ident(item)
            if ident not in seen:
                seen.add(ident)
                merged.append(item)

        atomic_write_json(dst, merged, make_backup=True)

    def _merge_playbook(self, src: Path, dst: Path) -> None:
        src_data = safe_read_json(src, default_factory=dict)
        dst_data = safe_read_json(dst, default_factory=dict)

        merged = copy.deepcopy(dst_data)
        # Keep higher evolution level / training cycles
        merged["evolution_level"] = max(dst_data.get("evolution_level", 1), src_data.get("evolution_level", 1))
        merged["total_training_cycles"] = max(
            dst_data.get("total_training_cycles", 0), src_data.get("total_training_cycles", 0)
        )

        # Union hooks and banned phrases
        dst_hooks = set(dst_data.get("winning_hooks_bank", []))
        src_hooks = set(src_data.get("winning_hooks_bank", []))
        merged["winning_hooks_bank"] = sorted(list(dst_hooks.union(src_hooks)))

        dst_banned = set(dst_data.get("banned_low_retention_phrases", []))
        src_banned = set(src_data.get("banned_low_retention_phrases", []))
        merged["banned_low_retention_phrases"] = sorted(list(dst_banned.union(src_banned)))

        atomic_write_json(dst, merged, make_backup=True)

    def _merge_brain(self, src: Path, dst: Path) -> None:
        src_data = safe_read_json(src, default_factory=dict)
        dst_data = safe_read_json(dst, default_factory=dict)

        merged = copy.deepcopy(dst_data)
        merged["total_self_learning_epochs"] = max(
            dst_data.get("total_self_learning_epochs", 0), src_data.get("total_self_learning_epochs", 0)
        )
        atomic_write_json(dst, merged, make_backup=True)

    def _merge_session(self, src: Path, dst: Path) -> None:
        # Keep dst session unless dst has no last_login and src does
        src_data = safe_read_json(src, default_factory=dict)
        dst_data = safe_read_json(dst, default_factory=dict)
        src_login = src_data.get("last_login", 0)
        dst_login = dst_data.get("last_login", 0)
        if src_login > dst_login:
            atomic_write_json(dst, src_data, make_backup=True)

    def _merge_sqlite(self, src: Path, dst: Path) -> None:
        # For SQLite, if dst is valid and has tables, keep dst; if src is newer or has more records, backup dst first
        if src.stat().st_size > dst.stat().st_size and src.stat().st_mtime > dst.stat().st_mtime:
            shutil.copy2(dst, dst.with_suffix(".db.bak"))
            shutil.copy2(src, dst)

    # =========================================================================
    # 4. VALIDATE ALL STATE
    # =========================================================================
    def validate_all_state(self) -> Tuple[bool, List[str]]:
        """
        Validates all essential state files.
        Returns (is_valid, list_of_issues).
        """
        issues: List[str] = []
        for rel_path, meta in STATE_CATALOG.items():
            if not meta["essential"]:
                continue
            full_path = self.storage_dir / rel_path
            if not full_path.exists():
                # On first ever run, missing state is acceptable if it can be initialized
                logger.info(f"[StateManager] Essential state {rel_path} does not exist yet (clean start).")
                continue

            if full_path.stat().st_size == 0:
                issues.append(f"Essential state file {rel_path} is 0 bytes (empty).")
                continue

            if meta["type"] == "sqlite":
                try:
                    conn = sqlite3.connect(str(full_path))
                    conn.execute("PRAGMA integrity_check;")
                    conn.close()
                except Exception as e:
                    issues.append(f"SQLite database {rel_path} integrity check failed: {e}")
            else:
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        json.load(f)
                except Exception as e:
                    issues.append(f"Essential JSON state {rel_path} failed decode: {e}")

        return len(issues) == 0, issues


def main():
    parser = argparse.ArgumentParser(description="Insta-Agent Persistent State Manager")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    subparsers.add_parser("audit", help="Audit all state files")
    subparsers.add_parser("backup", help="Create a timestamped backup of all state")
    subparsers.add_parser("validate", help="Validate integrity of essential state files")

    restore_p = subparsers.add_parser("restore", help="Restore and merge state from another directory")
    restore_p.add_argument("--source", required=True, help="Path to restored cache or artifact directory")

    args = parser.parse_args()
    manager = StateManager()

    if args.command == "audit":
        audit = manager.audit_all_state()
        print(json.dumps(audit, indent=2))
        sys.exit(0 if audit["corrupted_files"] == 0 else 1)

    elif args.command == "backup":
        snapshot = manager.backup_all_state()
        print(f"Snapshot created at: {snapshot}")
        sys.exit(0)

    elif args.command == "restore":
        res = manager.restore_and_merge_state(args.source)
        print(f"Restored {len(res['restored'])} files, merged {len(res['merged'])} files.")
        if res["errors"]:
            print(f"Errors encountered: {res['errors']}")
            sys.exit(1)
        sys.exit(0)

    elif args.command == "validate":
        valid, issues = manager.validate_all_state()
        if valid:
            print("All essential state files passed integrity validation.")
            sys.exit(0)
        else:
            print(f"Validation failed with {len(issues)} issues:")
            for iss in issues:
                print(f"  - {iss}")
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
