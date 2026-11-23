"""
Visual Quality Gate & Vision Verification Engine.
Enforces multi-layer inspection before any generated image is accepted into video composition:
1. Physical Image Verification: Format integrity, vertical 9:16 aspect ratio (1080x1920), minimum resolution.
2. Luminance & Content Check: Rejects blank, corrupted, washed out, or flat solid monochrome frames.
3. Cryptographic & Perceptual Duplicate Detection: Checks against PermanentVisualMemory.
4. Scene Relevance & Topic Contamination Gate: Ensures the visual matches the scene narration and rejects topic-override contamination.
5. Structured Validation Report: Returns pass/fail status, relevance score, and actionable rejection reasons.
"""

import hashlib
import io
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from PIL import Image, ImageStat

from app.storage.permanent_visual_memory import PermanentVisualMemory
from app.video.scene_visual_planner import SceneVisualPlan

logger = logging.getLogger("VisionQualityGate")


@dataclass
class VisualValidationReport:
    """Structured report returned by the visual quality gate for each asset."""
    scene_idx: int
    image_path: str
    expected_subject: str
    expected_action: str
    actual_detected_subject: str
    actual_detected_action: str
    semantic_relevance_score: float
    duplicate_status: bool
    passed: bool
    rejection_reason: Optional[str] = None
    sha256: str = ""
    phash: str = ""
    aspect_ratio: str = "9:16"
    dimensions: Tuple[int, int] = (1080, 1920)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_idx": self.scene_idx,
            "image_path": self.image_path,
            "expected_subject": self.expected_subject,
            "expected_action": self.expected_action,
            "actual_detected_subject": self.actual_detected_subject,
            "actual_detected_action": self.actual_detected_action,
            "semantic_relevance_score": self.semantic_relevance_score,
            "duplicate_status": self.duplicate_status,
            "passed": self.passed,
            "rejection_reason": self.rejection_reason,
            "sha256": self.sha256,
            "phash": self.phash,
            "aspect_ratio": self.aspect_ratio,
            "dimensions": list(self.dimensions),
        }


class VisionQualityGate:
    """
    Quality gate validating generated images before they reach the video composer.
    """

    MIN_LUMINANCE = 8.0     # Reject near-total black canvases
    MAX_LUMINANCE = 248.0   # Reject washed out near-total white canvases
    MIN_VARIANCE = 5.0      # Reject flat solid colors
    ACCEPTANCE_THRESHOLD = 0.70
    MIN_WIDTH = 720
    MIN_HEIGHT = 1280

    @classmethod
    def validate_scene_image(
        cls,
        image_input: Optional[Union[Path, str, bytes, Image.Image]] = None,
        plan: Optional[SceneVisualPlan] = None,
        acceptance_threshold: float = ACCEPTANCE_THRESHOLD,
        check_permanent_duplicates: bool = True,
        used_reel_hashes: Optional[set] = None,
        used_reel_phashes: Optional[set] = None,
        image_path: Optional[Union[Path, str]] = None,
    ) -> VisualValidationReport:
        """
        Runs comprehensive physical, duplicate, and relevance validation on an image asset against its scene plan.
        """
        target_input = image_input if image_input is not None else image_path
        if target_input is None:
            raise ValueError("validate_scene_image requires image_input or image_path.")

        scene_idx = getattr(plan, "scene_idx", 0) if plan else 0
        expected_subject = getattr(plan, "primary_subject", getattr(plan, "main_subject", "scene subject")) if plan else "scene subject"
        expected_action = getattr(plan, "action", getattr(plan, "subject_action", "scene action")) if plan else "scene action"
        image_path_str = str(target_input) if isinstance(target_input, (Path, str)) else "<memory_bytes>"

        # 1. Physical file existence and decode check
        img: Optional[Image.Image] = None
        try:
            if isinstance(target_input, (Path, str)):
                p = Path(target_input)
                if not p.exists() or p.stat().st_size < 1000:
                    return VisualValidationReport(
                        scene_idx=scene_idx,
                        image_path=image_path_str,
                        expected_subject=expected_subject,
                        expected_action=expected_action,
                        actual_detected_subject="missing_file",
                        actual_detected_action="none",
                        semantic_relevance_score=0.0,
                        duplicate_status=False,
                        passed=False,
                        rejection_reason=f"File does not exist or is too small (<1KB): {p}",
                    )
                with open(p, "rb") as f:
                    data = f.read()
                img = Image.open(io.BytesIO(data))
                img.verify()
                img = Image.open(io.BytesIO(data))
            elif isinstance(target_input, bytes):
                if len(target_input) < 1000:
                    return VisualValidationReport(
                        scene_idx=scene_idx,
                        image_path="<bytes>",
                        expected_subject=expected_subject,
                        expected_action=expected_action,
                        actual_detected_subject="truncated_bytes",
                        actual_detected_action="none",
                        semantic_relevance_score=0.0,
                        duplicate_status=False,
                        passed=False,
                        rejection_reason=f"Image bytes payload is truncated ({len(target_input)} bytes)",
                    )
                img = Image.open(io.BytesIO(target_input))
                img.verify()
                img = Image.open(io.BytesIO(target_input))
            elif isinstance(target_input, Image.Image):
                img = target_input
            else:
                raise ValueError(f"Unsupported image input type: {type(target_input)}")
        except Exception as exc:
            return VisualValidationReport(
                scene_idx=scene_idx,
                image_path=image_path_str,
                expected_subject=expected_subject,
                expected_action=expected_action,
                actual_detected_subject="corrupted_file",
                actual_detected_action="decode_failure",
                semantic_relevance_score=0.0,
                duplicate_status=False,
                passed=False,
                rejection_reason=f"Image decode failed: {exc}",
            )

        # 2. Dimensions & Aspect Ratio Check
        w, h = img.size

        # Check orientation and vertical aspect ratio first
        if w >= h:
            return VisualValidationReport(
                scene_idx=scene_idx,
                image_path=image_path_str,
                expected_subject=expected_subject,
                expected_action=expected_action,
                actual_detected_subject="horizontal_canvas",
                actual_detected_action="landscape_orientation",
                semantic_relevance_score=0.2,
                duplicate_status=False,
                passed=False,
                rejection_reason=f"Invalid aspect ratio: Image is horizontal/landscape ({w}x{h}), expected vertical 9:16 (1080x1920).",
                dimensions=(w, h),
            )

        ratio = w / h
        # Ideal 9:16 vertical ratio is ~0.5625. Must be within [0.45, 0.70]
        if ratio > 0.70 or ratio < 0.45:
            return VisualValidationReport(
                scene_idx=scene_idx,
                image_path=image_path_str,
                expected_subject=expected_subject,
                expected_action=expected_action,
                actual_detected_subject="skewed_vertical_canvas",
                actual_detected_action="irregular_aspect_ratio",
                semantic_relevance_score=0.2,
                duplicate_status=False,
                passed=False,
                rejection_reason=f"Invalid aspect ratio ({w}x{h}, ratio={ratio:.3f}). Expected vertical 9:16 (~0.5625).",
                dimensions=(w, h),
            )

        if w < cls.MIN_WIDTH or h < cls.MIN_HEIGHT:
            return VisualValidationReport(
                scene_idx=scene_idx,
                image_path=image_path_str,
                expected_subject=expected_subject,
                expected_action=expected_action,
                actual_detected_subject="low_resolution",
                actual_detected_action="low_res",
                semantic_relevance_score=0.2,
                duplicate_status=False,
                passed=False,
                rejection_reason=f"Image resolution too low ({w}x{h}), minimum required is {cls.MIN_WIDTH}x{cls.MIN_HEIGHT}.",
                dimensions=(w, h),
            )

        # 3. Luminance and Variance (prevent solid black, white, or monochrome flat cards)
        stat = ImageStat.Stat(img.convert("L"))
        mean_lum = stat.mean[0]
        var_lum = stat.var[0]

        if mean_lum < cls.MIN_LUMINANCE:
            return VisualValidationReport(
                scene_idx=scene_idx,
                image_path=image_path_str,
                expected_subject=expected_subject,
                expected_action=expected_action,
                actual_detected_subject="blank_black_canvas",
                actual_detected_action="underexposed",
                semantic_relevance_score=0.0,
                duplicate_status=False,
                passed=False,
                rejection_reason=f"Luminance too low ({mean_lum:.1f}), image appears completely dark.",
                dimensions=(w, h),
            )

        if mean_lum > cls.MAX_LUMINANCE:
            return VisualValidationReport(
                scene_idx=scene_idx,
                image_path=image_path_str,
                expected_subject=expected_subject,
                expected_action=expected_action,
                actual_detected_subject="washed_out_white_canvas",
                actual_detected_action="overexposed",
                semantic_relevance_score=0.0,
                duplicate_status=False,
                passed=False,
                rejection_reason=f"Luminance too high ({mean_lum:.1f}), image appears completely washed out white.",
                dimensions=(w, h),
            )

        if var_lum < cls.MIN_VARIANCE:
            return VisualValidationReport(
                scene_idx=scene_idx,
                image_path=image_path_str,
                expected_subject=expected_subject,
                expected_action=expected_action,
                actual_detected_subject="solid_flat_color",
                actual_detected_action="untextured",
                semantic_relevance_score=0.1,
                duplicate_status=False,
                passed=False,
                rejection_reason=f"Variance too low ({var_lum:.1f}), image appears to be a flat solid color.",
                dimensions=(w, h),
            )

        # 4. Fingerprints & Duplicate Detection
        target_fp_input = target_input if isinstance(target_input, (Path, str, bytes)) else img
        fp = PermanentVisualMemory.compute_fingerprints(target_fp_input)
        sha256 = fp["sha256"]
        phash = fp["phash"]

        # Check within current Reel
        if used_reel_hashes and sha256 in used_reel_hashes:
            return VisualValidationReport(
                scene_idx=scene_idx,
                image_path=image_path_str,
                expected_subject=expected_subject,
                expected_action=expected_action,
                actual_detected_subject="reel_duplicate",
                actual_detected_action="repeated_within_reel",
                semantic_relevance_score=0.0,
                duplicate_status=True,
                passed=False,
                rejection_reason="Duplicate visual detected within the same Reel (identical content hash).",
                sha256=sha256,
                phash=phash,
                dimensions=(w, h),
            )

        if used_reel_phashes:
            for uh in used_reel_phashes:
                if uh and PermanentVisualMemory.hamming_distance(phash, uh) <= 5:
                    return VisualValidationReport(
                        scene_idx=scene_idx,
                        image_path=image_path_str,
                        expected_subject=expected_subject,
                        expected_action=expected_action,
                        actual_detected_subject="reel_duplicate",
                        actual_detected_action="perceptual_duplicate_within_reel",
                        semantic_relevance_score=0.0,
                        duplicate_status=True,
                        passed=False,
                        rejection_reason=f"Perceptual near-duplicate visual detected within the same Reel (pHash distance <= 5).",
                        sha256=sha256,
                        phash=phash,
                        dimensions=(w, h),
                    )

        # Check against historical permanent visual registry
        if check_permanent_duplicates:
            is_dup, reason, matching_rec = PermanentVisualMemory.check_duplicate(
                target_fp_input,
                source_identity=Path(image_path_str).name if isinstance(image_input, (Path, str)) else "",
            )
            if is_dup:
                return VisualValidationReport(
                    scene_idx=scene_idx,
                    image_path=image_path_str,
                    expected_subject=expected_subject,
                    expected_action=expected_action,
                    actual_detected_subject="historical_duplicate",
                    actual_detected_action="duplicate_reused",
                    semantic_relevance_score=0.0,
                    duplicate_status=True,
                    passed=False,
                    rejection_reason=f"Duplicate visual rejected by PermanentVisualMemory: {reason}",
                    sha256=sha256,
                    phash=phash,
                    dimensions=(w, h),
                )

        # 5. Strict Scene Semantic Contract & Multi-Dimensional Validation
        from app.video.scene_semantic_contract import SceneSemanticContract

        scene_dict = {
            "spoken_line": getattr(plan, "exact_narration", "") or getattr(plan, "narration", ""),
            "on_screen_text": getattr(plan, "on_screen_text", ""),
            "visual_description": getattr(plan, "visual_description", "") or getattr(plan, "generation_prompt", ""),
        }
        contract = SceneSemanticContract.build_from_scene(
            scene_dict=scene_dict,
            topic=getattr(plan, "topic", ""),
            scene_idx=scene_idx,
            total_scenes=getattr(plan, "total_scenes", 1),
        )

        narration_text = (getattr(plan, "exact_narration", "") or getattr(plan, "narration", "")).lower()
        asset_identity = Path(image_path_str).name.lower()

        contract_res = contract.validate_asset(
            image_input=img,
            asset_identity=asset_identity,
            metadata={"subject": expected_subject},
        )

        if not contract_res.overall_accepted:
            relevance_score = contract_res.confidence_score
            rejection_reason = f"Semantic contract failure: {contract_res.rejection_reason}"
        else:
            relevance_score = 0.95
            rejection_reason = None

        # Additional domain checks
        gem_terms = ["gemstone", "sapphire", "ruby", "emerald", "diamond", "pearl", "coral", "neelam", "pukhraj", "panna", "manik", "heera", "रत्न"]
        if any(g in asset_identity for g in ["gemstone", "sapphire", "ruby", "emerald", "diamond", "pearl", "coral"]):
            if not any(g in narration_text for g in gem_terms):
                relevance_score = 0.2
                rejection_reason = "Semantic mismatch: Gemstone visual assigned to scene without gemstone narration."

        # 2. Temple rejection when narration does NOT mention temple
        if ("temple" in asset_identity or "diya" in asset_identity) and not any(k in narration_text for k in ["temple", "mandir", "दीपक", "दीप", "sanctum"]):
            relevance_score = 0.2
            rejection_reason = "Semantic mismatch: Temple visual assigned to scene without temple mention in narration."

        # 3. Havan/fire rejection when narration does NOT mention havan
        if ("havan" in asset_identity or "fire_altar" in asset_identity) and not any(k in narration_text for k in ["havan", "fire", "altar", "हवन", "अग्नि", "यज्ञ"]):
            relevance_score = 0.2
            rejection_reason = "Semantic mismatch: Sacred fire/havan visual assigned to scene without havan/fire narration."

        # 4. Career narration must NOT receive marriage imagery
        if any(c in narration_text for c in ["career", "करियर", "10th house", "tenth house", "दसवां भाव", "job", "नौकरी", "workplace"]):
            if any(m in asset_identity for m in ["marriage", "vivah", "shaadi", "wedding", "love"]):
                relevance_score = 0.2
                rejection_reason = "Semantic mismatch: Marriage imagery assigned to career/10th house narration."

        # 5. Marriage narration must NOT receive gemstone imagery
        if any(m in narration_text for m in ["marriage", "विवाह", "7th house", "seventh house", "सातवां भाव", "relationship", "spouse"]):
            if not any(g in narration_text for g in gem_terms) and any(g in asset_identity for g in ["gemstone", "sapphire", "ruby", "emerald", "diamond"]):
                relevance_score = 0.2
                rejection_reason = "Semantic mismatch: Gemstone imagery assigned to marriage/7th house narration."

        # Check topic entity contamination in positive generation elements:
        # If the scene plan specifies forbidden entity elements (e.g., Rudraksha barred from nervous system scene),
        # ensure the main subject or positive prompt (before 'no ' or 'avoid:') does not contain them.
        forbidden = getattr(plan, "forbidden_visual_elements", [])
        prompt_text = getattr(plan, "generation_prompt", "").lower()
        positive_prompt = prompt_text.split("no ")[0].split("avoid:")[0]
        subject_text = getattr(plan, "main_subject", "").lower()

        # Generic style exclusions are negative prompt constraints, not entity contaminations
        STYLE_EXCLUSIONS = {"3d renders", "cgi cartoons", "animated illustrations", "stock models", "wireframes", "cartoons", "cgi", "drawings"}
        topic_lower = getattr(plan, "topic", "").lower()
        for forb in forbidden:
            forb_clean = forb.lower().strip()
            if forb_clean and forb_clean not in STYLE_EXCLUSIONS and forb_clean not in topic_lower:
                if forb_clean in positive_prompt or forb_clean in subject_text:
                    relevance_score = 0.3
                    rejection_reason = f"Topic contamination: Scene forbidden element '{forb}' was detected in scene subject/prompt."
                    break

        passed = (relevance_score >= acceptance_threshold) and (rejection_reason is None)

        return VisualValidationReport(
            scene_idx=scene_idx,
            image_path=image_path_str,
            expected_subject=expected_subject,
            expected_action=expected_action,
            actual_detected_subject=expected_subject,
            actual_detected_action=expected_action,
            semantic_relevance_score=relevance_score,
            duplicate_status=False,
            passed=passed,
            rejection_reason=rejection_reason,
            sha256=sha256,
            phash=phash,
            dimensions=(w, h),
        )
