"""
Scene-to-Asset Manifest & Integrity Validator.
Creates, validates, and manages the immutable binding between script scenes
and verified visual assets prior to video composition.

Guarantees:
1. Exactly one verified image per scene.
2. No missing scene images.
3. Zero duplicate images within the same Reel (SHA-256 & pHash).
4. Zero historical image reuse.
5. Strict scene order and narration-to-image association.
6. Video composer consumes ONLY verified manifest assets.
"""

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from app.storage.permanent_visual_memory import PermanentVisualMemory
from app.video.ai_image_generator import AIImageGenerator
from app.video.scene_visual_planner import SceneVisualPlan, SceneVisualPlanner
from app.video.vision_quality_gate import VisionQualityGate, VisualValidationReport

logger = logging.getLogger("SceneManifest")


class ManifestIntegrityError(Exception):
    """Raised when a SceneAssetManifest fails integrity verification."""
    pass


@dataclass
class SceneAssetEntry:
    """Immutable manifest entry for a single scene."""
    scene_idx: int
    spoken_line: str
    on_screen_text: str
    visual_description: str
    primary_subject: str
    generation_prompt: str
    image_path: str
    sha256: str
    phash: str
    validation_passed: bool
    semantic_relevance_score: float
    rejection_reason: Optional[str] = None


@dataclass
class SceneAssetManifest:
    """Complete, verified manifest for an entire Reel."""
    reel_id: str
    topic: str
    total_scenes: int
    entries: List[SceneAssetEntry] = field(default_factory=list)
    is_verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save(self, output_path: Path) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        return output_path


class SceneManifestBuilder:
    """
    Coordinates planning, generation, validation, and manifest creation for a Reel.
    """

    @classmethod
    def build_verified_manifest(
        cls,
        script_data: Dict[str, Any],
        reel_id: Optional[str] = None,
        mock_generation: bool = False,
    ) -> SceneAssetManifest:
        """
        Builds and verifies a complete scene-to-asset manifest.
        Fails safely if any scene cannot obtain a verified matching image.
        """
        scenes = script_data.get("scenes", [])
        if not scenes:
            raise ManifestIntegrityError("Cannot build manifest: Script contains no scenes.")

        topic = script_data.get("topic", "Instagram Reel")
        total_scenes = len(scenes)
        r_id = reel_id or f"reel_{hashlib.sha256(topic.encode()).hexdigest()[:12]}"

        # Step 1: Plan all scene visuals independently
        plans = SceneVisualPlanner.plan_reel_visuals(scenes=scenes, topic=topic)

        # Step 2: Generate and validate assets for each scene
        manifest_entries: List[SceneAssetEntry] = []
        assigned_sha256_set: Set[str] = set()
        assigned_phash_set: Set[str] = set()

        for idx, plan in enumerate(plans):
            sc = scenes[idx]
            sc["visual_plan"] = plan.to_dict()
            img_path = AIImageGenerator.generate_scene_image(
                scene_dict=sc,
                topic=topic,
                scene_idx=idx,
                total_scenes=total_scenes,
                reel_slug=r_id,
                mock_mode=mock_generation,
            )

            # Step 3: Run Visual Quality Gate (PermanentVisualMemory already verified during generation)
            report = VisionQualityGate.validate_scene_image(
                image_path=img_path,
                plan=plan,
                check_permanent_duplicates=False,
            )

            if not report.passed:
                raise ManifestIntegrityError(
                    f"Visual Quality Gate failed for scene {idx + 1}: {report.rejection_reason}"
                )

            # Intra-reel uniqueness check
            if report.sha256 in assigned_sha256_set:
                raise ManifestIntegrityError(
                    f"Intra-reel duplicate detected at scene {idx + 1}: Identical SHA-256 hash."
                )
            assigned_sha256_set.add(report.sha256)

            # Perceptual hash intra-reel check (Hamming distance <= 6)
            for existing_phash in assigned_phash_set:
                dist = PermanentVisualMemory.hamming_distance(report.phash, existing_phash)
                if dist <= 6:
                    raise ManifestIntegrityError(
                        f"Intra-reel near-duplicate visual detected at scene {idx + 1} "
                        f"(pHash distance {dist} <= 6)."
                    )
            assigned_phash_set.add(report.phash)

            entry = SceneAssetEntry(
                scene_idx=idx,
                spoken_line=sc.get("spoken_line", ""),
                on_screen_text=sc.get("on_screen_text", ""),
                visual_description=sc.get("visual_description", ""),
                primary_subject=plan.primary_subject,
                generation_prompt=plan.generation_prompt,
                image_path=str(img_path.resolve()),
                sha256=report.sha256,
                phash=report.phash,
                validation_passed=True,
                semantic_relevance_score=report.semantic_relevance_score,
            )
            manifest_entries.append(entry)

        # Step 4: Final manifest integrity check
        manifest = SceneAssetManifest(
            reel_id=r_id,
            topic=topic,
            total_scenes=total_scenes,
            entries=manifest_entries,
            is_verified=True,
        )
        cls.verify_manifest_integrity(manifest)
        return manifest

    @classmethod
    def verify_manifest_integrity(cls, manifest: SceneAssetManifest) -> bool:
        """
        Final pre-render integrity audit on the manifest:
        1. Correct number of entries matching total_scenes.
        2. Exactly 1 verified image per scene.
        3. All referenced image files physically exist.
        4. Zero intra-reel duplicates.
        """
        if len(manifest.entries) != manifest.total_scenes:
            raise ManifestIntegrityError(
                f"Manifest scene count mismatch: Expected {manifest.total_scenes}, got {len(manifest.entries)}."
            )

        seen_indices = set()
        seen_hashes = set()

        for entry in manifest.entries:
            if entry.scene_idx in seen_indices:
                raise ManifestIntegrityError(f"Duplicate scene index in manifest: {entry.scene_idx}")
            seen_indices.add(entry.scene_idx)

            p = Path(entry.image_path)
            if not p.exists():
                raise ManifestIntegrityError(f"Manifest asset file missing from disk: {p}")

            if entry.sha256 in seen_hashes:
                raise ManifestIntegrityError(f"Duplicate image hash in manifest: {entry.sha256}")
            seen_hashes.add(entry.sha256)

            if not entry.validation_passed:
                raise ManifestIntegrityError(f"Scene {entry.scene_idx + 1} asset is marked unverified.")

        return True
