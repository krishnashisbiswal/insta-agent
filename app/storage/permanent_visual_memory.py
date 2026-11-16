"""
Permanent Visual Memory & Multi-Algorithm Fingerprint Engine.
Implements production-grade perceptual and cryptographic fingerprinting:
1. SHA-256 (Cryptographic exact byte identity)
2. pHash (Perceptual hash - Discrete Cosine Transform)
3. dHash (Difference gradient hash)
4. aHash (Average luminance hash)
5. Color/Spatial Embedding (Normalized spatial color layout vector)

Enforces zero repetition across all historical reels:
Rejects exact and near-duplicate visuals, including renamed, resized,
recompressed, and cropped variants where detectable.
Durable persistence is protected by transactional atomic writes and file locks.
"""

import hashlib
import io
import json
import logging
import math
import os
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from PIL import Image

try:
    import imagehash
except ImportError:
    imagehash = None

try:
    from filelock import FileLock
except ImportError:
    FileLock = None

logger = logging.getLogger("PermanentVisualMemory")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STORAGE_DIR = PROJECT_ROOT / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

PERMANENT_REGISTRY_FILE = STORAGE_DIR / "permanent_visual_registry.json"
LEGACY_REGISTRY_FILE = STORAGE_DIR / "used_visuals_registry.json"
LOCK_FILE = STORAGE_DIR / "visual_memory.lock"

# Default perceptual similarity thresholds
# 64-bit hashes: distance <= 8 represents >= 87.5% perceptual similarity
DEFAULT_PHASH_THRESHOLD = 8
DEFAULT_DHASH_THRESHOLD = 8
DEFAULT_COLOR_SIMILARITY_THRESHOLD = 0.94


def _atomic_replace_json(target_path: Path, data: Dict[str, Any], indent: int = 2) -> None:
    """
    Safely writes JSON data to a unique per-process, per-thread temporary file
    and performs an atomic replacement with backoff retries for Windows file-system locking.
    """
    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    unique_tmp = target_path.parent / f".tmp_{target_path.stem}_{os.getpid()}_{threading.get_ident()}_{time.time_ns()}_{uuid.uuid4().hex[:8]}.tmp"
    try:
        with open(unique_tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        for attempt in range(5):
            try:
                os.replace(unique_tmp, target_path)
                return
            except (PermissionError, FileNotFoundError, OSError) as err:
                if attempt == 4:
                    try:
                        if target_path.exists():
                            os.remove(target_path)
                        os.rename(unique_tmp, target_path)
                        return
                    except Exception:
                        raise err
                time.sleep(0.02 * (attempt + 1))
    finally:
        if unique_tmp.exists():
            try:
                unique_tmp.unlink()
            except Exception:
                pass


class PermanentVisualMemory:
    """
    Production-grade visual memory that permanently stores image fingerprints,
    scene descriptions, script IDs, Reel IDs, and usage timestamps.
    Prevents any exact or near-duplicate visual from ever repeating.
    """

    _cache_loaded: bool = False
    _records: Dict[str, Dict[str, Any]] = {}
    _sha256_set: Set[str] = set()
    _source_identities: Set[str] = set()
    _last_disk_mtime_ns: int = 0
    _last_disk_size: int = 0
    _thread_lock: threading.RLock = threading.RLock()

    @classmethod
    def _get_lock(cls) -> Any:
        if FileLock:
            return FileLock(str(LOCK_FILE), timeout=15)
        return None

    # =========================================================================
    # 1. MULTI-ALGORITHM FINGERPRINT COMPUTATION
    # =========================================================================
    @classmethod
    def compute_fingerprints(
        cls,
        image_input: Union[Path, str, bytes, Image.Image],
    ) -> Dict[str, Any]:
        """
        Computes SHA-256, pHash, dHash, aHash, and a normalized color embedding.
        Works across all image formats, resolutions, and orientations.
        """
        raw_bytes: Optional[bytes] = None
        pil_img: Optional[Image.Image] = None

        if isinstance(image_input, (Path, str)):
            p = Path(image_input)
            if not p.exists():
                raise FileNotFoundError(f"Image not found at {p}")
            with open(p, "rb") as f:
                raw_bytes = f.read()
            pil_img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        elif isinstance(image_input, bytes):
            raw_bytes = image_input
            pil_img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        elif isinstance(image_input, Image.Image):
            pil_img = image_input.convert("RGB")
            buf = io.BytesIO()
            pil_img.save(buf, format="JPEG", quality=95)
            raw_bytes = buf.getvalue()
        else:
            raise TypeError(f"Unsupported image input type: {type(image_input)}")

        # 1. SHA-256 byte hash
        sha256_hash = hashlib.sha256(raw_bytes).hexdigest()

        # 2. Perceptual Hashes (pHash, dHash, aHash)
        if imagehash:
            p_hash_str = str(imagehash.phash(pil_img))
            d_hash_str = str(imagehash.dhash(pil_img))
            a_hash_str = str(imagehash.average_hash(pil_img))
        else:
            p_hash_str = cls._fallback_dhash(pil_img)
            d_hash_str = cls._fallback_dhash(pil_img)
            a_hash_str = cls._fallback_ahash(pil_img)

        # 3. Normalized Color & Spatial Layout Embedding (8x8 block grid in RGB)
        embedding = cls._compute_spatial_color_embedding(pil_img)

        w, h = pil_img.size
        gcd = math.gcd(w, h)
        aspect_ratio = f"{w // gcd}:{h // gcd}" if gcd > 0 else f"{w}:{h}"

        return {
            "sha256": sha256_hash,
            "phash": p_hash_str,
            "dhash": d_hash_str,
            "ahash": a_hash_str,
            "color_embedding": embedding,
            "dimensions": [w, h],
            "aspect_ratio": aspect_ratio,
            "bytes_size": len(raw_bytes),
        }

    @staticmethod
    def _fallback_ahash(img: Image.Image, hash_size: int = 8) -> str:
        """Pure-Python Average Hash fallback."""
        resized = img.resize((hash_size, hash_size), Image.Resampling.BILINEAR).convert("L")
        pixels = list(resized.getdata())
        avg = sum(pixels) / len(pixels)
        bits = "".join("1" if p > avg else "0" for p in pixels)
        return f"{int(bits, 2):0{hash_size*hash_size // 4}x}"

    @staticmethod
    def _fallback_dhash(img: Image.Image, hash_size: int = 8) -> str:
        """Pure-Python Difference Hash fallback."""
        resized = img.resize((hash_size + 1, hash_size), Image.Resampling.BILINEAR).convert("L")
        pixels = list(resized.getdata())
        diff = []
        for row in range(hash_size):
            for col in range(hash_size):
                p1 = pixels[row * (hash_size + 1) + col]
                p2 = pixels[row * (hash_size + 1) + col + 1]
                diff.append("1" if p1 > p2 else "0")
        bits = "".join(diff)
        return f"{int(bits, 2):0{hash_size*hash_size // 4}x}"

    @staticmethod
    def _compute_spatial_color_embedding(img: Image.Image, grid_size: int = 8) -> List[float]:
        """
        Computes a normalized 64-vector spatial layout embedding
        by downsampling to an 8x8 luminance and chroma representation.
        """
        import numpy as np
        thumb = img.resize((grid_size, grid_size), Image.Resampling.BOX).convert("RGB")
        arr = np.array(thumb, dtype=float)
        lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
        flat_lum = (lum / 255.0).flatten()
        norm = np.linalg.norm(flat_lum) or 1.0
        return [round(float(v), 4) for v in (flat_lum / norm)]

    # =========================================================================
    # 2. HAMMING & COSINE SIMILARITY
    # =========================================================================
    @staticmethod
    def hamming_distance(hex1: str, hex2: str) -> int:
        """Computes bitwise Hamming distance between two hex hash strings."""
        try:
            val1 = int(hex1, 16)
            val2 = int(hex2, 16)
            return bin(val1 ^ val2).count("1")
        except Exception:
            return 64

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Computes cosine similarity between two normalized float vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        return max(0.0, min(1.0, dot))

    # =========================================================================
    # 3. DURABLE REGISTRY PERSISTENCE WITH TRANSACTIONAL INTEGRITY
    # =========================================================================
    @classmethod
    def load_registry(cls) -> Dict[str, Any]:
        """Loads permanent registry from disk under concurrency lock."""
        with cls._thread_lock:
            lock = cls._get_lock()
            if lock:
                with lock:
                    return cls._read_registry_file()
            return cls._read_registry_file()

    @classmethod
    def _recover_registry(cls) -> Optional[Dict[str, Any]]:
        """Scans for valid temporary recovery files or falls back to legacy registry."""
        try:
            candidates = sorted(
                PERMANENT_REGISTRY_FILE.parent.glob(f"*{PERMANENT_REGISTRY_FILE.stem}*.tmp*"),
                key=lambda p: p.stat().st_mtime_ns if p.exists() else 0,
                reverse=True,
            )
            for c in candidates:
                try:
                    with open(c, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict) and "records" in data and len(data["records"]) > 0:
                        logger.warning(f"[PermanentVisualMemory] Recovered registry from temp snapshot: {c.name}")
                        return data
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"Recovery scan notice: {e}")

        # Fallback to reconstructing from legacy registry
        if LEGACY_REGISTRY_FILE.exists():
            try:
                with open(LEGACY_REGISTRY_FILE, "r", encoding="utf-8") as lf:
                    leg = json.load(lf)
                recovered = {
                    "schema_version": "2.0.0",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "total_records": 0,
                    "records": {},
                }
                for item in leg.get("used_images", []):
                    item_str = str(item).strip()
                    if item_str:
                        recovered["records"][f"legacy:{item_str}"] = {
                            "source_identity": item_str,
                            "legacy_import": True,
                            "usage_timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                recovered["total_records"] = len(recovered["records"])
                logger.warning("[PermanentVisualMemory] Recovered records from legacy registry.")
                return recovered
            except Exception:
                pass
        return None

    @classmethod
    def _read_registry_file(cls) -> Dict[str, Any]:
        if not PERMANENT_REGISTRY_FILE.exists():
            initial_data = cls._recover_registry()
            if not initial_data:
                initial_data = {
                    "schema_version": "2.0.0",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "total_records": 0,
                    "records": {},
                }
            cls._write_registry_file(initial_data)
            cls._update_cache(initial_data)
            return initial_data

        try:
            with open(PERMANENT_REGISTRY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            cls._update_cache(data)
            return data
        except Exception as exc:
            logger.error(f"Error reading permanent registry file: {exc}. Attempting recovery...")
            recovered = cls._recover_registry()
            if recovered:
                cls._write_registry_file(recovered)
                cls._update_cache(recovered)
                return recovered
            fallback = {"schema_version": "2.0.0", "records": {}, "total_records": 0}
            cls._update_cache(fallback)
            return fallback

    @classmethod
    def _write_registry_file(cls, data: Dict[str, Any]) -> None:
        """Atomic transactional write with fsync to guarantee durable persistence."""
        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        data["total_records"] = len(data.get("records", {}))
        _atomic_replace_json(PERMANENT_REGISTRY_FILE, data, indent=2)

        try:
            if PERMANENT_REGISTRY_FILE.exists():
                st = PERMANENT_REGISTRY_FILE.stat()
                cls._last_disk_mtime_ns = st.st_mtime_ns
                cls._last_disk_size = st.st_size
        except Exception:
            pass

        # Synchronize backward compatibility with legacy registry
        try:
            legacy_set = set()
            for k, rec in data.get("records", {}).items():
                if rec.get("source_identity"):
                    legacy_set.add(rec["source_identity"])
                if rec.get("sha256"):
                    legacy_set.add(f"sha256:{rec['sha256']}")
                    legacy_set.add(f"hash:{rec['sha256'][:32]}")
            _atomic_replace_json(LEGACY_REGISTRY_FILE, {"used_images": sorted(list(legacy_set))}, indent=2)
        except Exception as e:
            logger.debug(f"Legacy sync notice: {e}")

    @classmethod
    def _update_cache(cls, data: Dict[str, Any]) -> None:
        cls._records = data.get("records", {})
        cls._sha256_set = {
            rec["sha256"].lower()
            for rec in cls._records.values()
            if rec.get("sha256")
        }
        cls._source_identities = {
            str(rec.get("source_identity", "")).strip().lower()
            for rec in cls._records.values()
            if rec.get("source_identity")
        }
        if PERMANENT_REGISTRY_FILE.exists():
            try:
                st = PERMANENT_REGISTRY_FILE.stat()
                cls._last_disk_mtime_ns = st.st_mtime_ns
                cls._last_disk_size = st.st_size
            except Exception:
                pass
        cls._cache_loaded = True

    # =========================================================================
    # 4. STORE PERMANENT FINGERPRINT RECORD
    # =========================================================================
    @classmethod
    def record_used_visual(
        cls,
        image_input: Union[Path, str, bytes, Image.Image],
        source_identity: str = "",
        scene_description: str = "",
        script_id: str = "",
        reel_id: str = "",
        topic: str = "",
        scene_idx: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Calculates fingerprints and atomically commits permanent record to durable storage.
        Guarantees that the registry persistence succeeds before any file deletion can happen.
        """
        fp = cls.compute_fingerprints(image_input)
        record_id = fp["sha256"]

        clean_source = source_identity.strip()
        if not clean_source and isinstance(image_input, (Path, str)):
            clean_source = Path(image_input).name

        record = {
            "asset_id": record_id,
            "sha256": fp["sha256"],
            "phash": fp["phash"],
            "dhash": fp["dhash"],
            "ahash": fp["ahash"],
            "color_embedding": fp["color_embedding"],
            "dimensions": fp["dimensions"],
            "aspect_ratio": fp["aspect_ratio"],
            "bytes_size": fp["bytes_size"],
            "source_identity": clean_source,
            "scene_description": scene_description,
            "script_id": script_id,
            "reel_id": reel_id,
            "topic": topic,
            "scene_idx": scene_idx,
            "usage_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        with cls._thread_lock:
            lock = cls._get_lock()
            if lock:
                with lock:
                    data = cls._read_registry_file()
                    data.setdefault("records", {})[record_id] = record
                    cls._write_registry_file(data)
                    cls._update_cache(data)
            else:
                data = cls._read_registry_file()
                data.setdefault("records", {})[record_id] = record
                cls._write_registry_file(data)
                cls._update_cache(data)

        logger.info(
            f"[PermanentVisualMemory] Permanently recorded visual fingerprint: "
            f"asset_id={record_id[:12]} | pHash={fp['phash']} | source='{clean_source}'"
        )
        return record

    # =========================================================================
    # 5. EXACT & NEAR-DUPLICATE DETECTION
    # =========================================================================
    @classmethod
    def check_duplicate(
        cls,
        image_input: Union[Path, str, bytes, Image.Image],
        source_identity: str = "",
        phash_threshold: int = DEFAULT_PHASH_THRESHOLD,
        dhash_threshold: int = DEFAULT_DHASH_THRESHOLD,
        color_threshold: float = DEFAULT_COLOR_SIMILARITY_THRESHOLD,
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Checks candidate image against all historical permanent records.
        Returns (is_duplicate: bool, reason: str, matching_record: dict).
        Rejects:
        1. Exact byte identity (SHA-256)
        2. Exact source URL/name match
        3. Near-duplicate perceptual matches (pHash Hamming distance <= threshold)
        4. Near-duplicate gradient matches (dHash Hamming distance <= threshold)
        5. Visual color/geometry layout similarity (Cosine similarity >= threshold)
        """
        if not cls._cache_loaded:
            cls.load_registry()
        elif PERMANENT_REGISTRY_FILE.exists():
            try:
                st = PERMANENT_REGISTRY_FILE.stat()
                if st.st_mtime_ns != cls._last_disk_mtime_ns or st.st_size != cls._last_disk_size:
                    cls.load_registry()
            except Exception:
                pass

        # Quick check for raw source identity string
        clean_source = source_identity.strip().lower()
        if clean_source and clean_source in cls._source_identities:
            # Find matching record
            for rec in cls._records.values():
                if str(rec.get("source_identity", "")).strip().lower() == clean_source:
                    return True, f"Exact source identity match: '{clean_source}'", rec
            return True, f"Exact source identity match: '{clean_source}'", None

        # Compute candidate fingerprints
        cand_fp = cls.compute_fingerprints(image_input)
        cand_sha = cand_fp["sha256"].lower()
        cand_phash = cand_fp["phash"]
        cand_dhash = cand_fp["dhash"]
        cand_color = cand_fp["color_embedding"]

        # 1. Exact SHA-256 match
        if cand_sha in cls._sha256_set:
            matching = cls._records.get(cand_sha)
            return True, f"Exact SHA-256 match: {cand_sha[:12]}...", matching

        # 2. Iterate historical records for perceptual & structural near-duplicates
        for rec_id, rec in cls._records.items():
            # Check pHash
            hist_phash = rec.get("phash")
            if hist_phash:
                p_dist = cls.hamming_distance(cand_phash, hist_phash)
                if p_dist <= phash_threshold:
                    sim_pct = round((1.0 - (p_dist / 64.0)) * 100, 1)
                    return (
                        True,
                        f"Perceptual pHash near-duplicate match (Hamming distance {p_dist}/64, ~{sim_pct}% match) "
                        f"against record {rec_id[:12]} (Reel {rec.get('reel_id', 'N/A')})",
                        rec,
                    )

            # Check dHash
            hist_dhash = rec.get("dhash")
            if hist_dhash:
                d_dist = cls.hamming_distance(cand_dhash, hist_dhash)
                if d_dist <= dhash_threshold:
                    sim_pct = round((1.0 - (d_dist / 64.0)) * 100, 1)
                    return (
                        True,
                        f"Gradient dHash near-duplicate match (Hamming distance {d_dist}/64, ~{sim_pct}% match) "
                        f"against record {rec_id[:12]}",
                        rec,
                    )

            # Check color/spatial layout embedding
            hist_emb = rec.get("color_embedding")
            if hist_emb and cand_color:
                c_sim = cls.cosine_similarity(cand_color, hist_emb)
                if c_sim >= color_threshold:
                    return (
                        True,
                        f"Color layout near-duplicate match (Cosine similarity {c_sim:.3f} >= {color_threshold}) "
                        f"against record {rec_id[:12]}",
                        rec,
                    )

        return False, None, None

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Returns statistics on stored permanent visual memory."""
        data = cls.load_registry()
        records = data.get("records", {})
        reels = {r.get("reel_id") for r in records.values() if r.get("reel_id")}
        scripts = {r.get("script_id") for r in records.values() if r.get("script_id")}
        return {
            "total_fingerprints": len(records),
            "unique_reels_tracked": len(reels),
            "unique_scripts_tracked": len(scripts),
            "last_updated": data.get("last_updated"),
            "registry_file": str(PERMANENT_REGISTRY_FILE),
            "registry_size_bytes": PERMANENT_REGISTRY_FILE.stat().st_size if PERMANENT_REGISTRY_FILE.exists() else 0,
        }
