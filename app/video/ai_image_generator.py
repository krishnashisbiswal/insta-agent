"""
Dedicated AI Image Generation Engine & Pipeline.
Generates brand-new, scene-specific 9:16 vertical photorealistic images
using configurable AI providers (Pollinations, Gemini/Imagen, Hugging Face, or Mock).

Key Principles:
1. Genuine Fresh Generation: Every scene receives a dedicated, brand-new visual generated from its SceneVisualPlan.
2. Strict Prompt Composition: Prompts are built from the scene's exact visual brief (subject, action, environment, framing, lighting, palette). The overall topic NEVER overrides scene meaning.
3. No Silent Static Fallback: If AI generation fails after configured retries and alternative providers, the system fails clearly with ImageGenerationError. It NEVER silently substitutes unrelated static B-roll.
4. Comprehensive Quality Gate: Every generated image is verified for decodability, 9:16 vertical geometry (1080x1920), luminance/variance, and scene relevance.
5. Zero Repetition / Duplicate Detection: Perceptual and cryptographic fingerprints (SHA256, pHash, dHash) are validated against PermanentVisualMemory and within the current Reel.
6. Persistent Metadata: Generation details, fingerprints, dimensions, and scene associations are committed to durable permanent visual memory.
"""

import hashlib
import io
import logging
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from PIL import Image, ImageOps

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    VIDEO_HEIGHT,
    VIDEO_WIDTH,
    IMAGE_PROVIDER,
    IMAGE_FALLBACK_PROVIDER,
    IMAGE_MAX_RETRIES,
    IMAGE_TIMEOUT,
    ALLOW_STATIC_FALLBACK,
)
from app.storage.permanent_visual_memory import PermanentVisualMemory
from app.video.image_providers import (
    BaseImageProvider,
    ImageProviderError,
    ProviderConfigError,
    get_image_provider,
)
from app.video.scene_visual_planner import SceneVisualPlan, SceneVisualPlanner
from app.video.vision_quality_gate import VisionQualityGate, VisualValidationReport

logger = logging.getLogger("AIImageGenerator")
GENERATED_BROLL_DIR = PROJECT_ROOT / "assets" / "generated_broll"
GENERATED_BROLL_DIR.mkdir(parents=True, exist_ok=True)


class ImageGenerationError(Exception):
    """Raised when an AI image generation request fails or violates quality/relevance policies."""
    pass


class AIImageGenerator:
    """
    Authoritative image generator for scene-level visual assets.
    """

    MAX_RETRIES = IMAGE_MAX_RETRIES

    @classmethod
    def generate_scene_image(
        cls,
        scene_dict: Dict[str, Any],
        topic: str,
        scene_idx: int,
        total_scenes: int = 5,
        reel_slug: Optional[str] = None,
        used_images: Optional[Set[Any]] = None,
        target_dir: Optional[Path] = None,
        provider_name: Optional[str] = None,
        mock_mode: bool = False,
        allow_static_fallback: Optional[bool] = None,
    ) -> Path:
        """
        Generates a dedicated, brand-new 9:16 vertical AI image for a scene.
        """
        # 1. Resolve SceneVisualPlan
        raw_plan = scene_dict.get("visual_plan")
        if isinstance(raw_plan, dict):
            # Reconstruct dataclass from dict
            clean_fields = {k: v for k, v in raw_plan.items() if k in SceneVisualPlan.__dataclass_fields__}
            plan = SceneVisualPlan(**clean_fields)
        elif isinstance(raw_plan, SceneVisualPlan):
            plan = raw_plan
        else:
            plan = SceneVisualPlanner.create_scene_visual_plan(
                scene=scene_dict,
                topic=topic,
                scene_idx=scene_idx,
                total_scenes=total_scenes,
            )

        # 2. Extract or build generation prompt
        prompt = getattr(plan, "image_prompt", None) or getattr(plan, "generation_prompt", "")
        if not prompt or not prompt.strip():
            prompt = SceneVisualPlanner.build_scene_visual_prompt(plan)
            plan.generation_prompt = prompt
            if hasattr(plan, "image_prompt"):
                plan.image_prompt = prompt

        clean_slug = re.sub(r"[^\w]", "_", (reel_slug or topic).lower())[:20].strip("_")
        out_dir = Path(target_dir) if target_dir else GENERATED_BROLL_DIR
        out_dir.mkdir(parents=True, exist_ok=True)

        # Gather used hashes within the current Reel
        used_reel_hashes: Set[str] = set()
        if used_images:
            for item in used_images:
                if isinstance(item, (Path, str)):
                    p_item = Path(item)
                    if p_item.exists() and p_item.is_file():
                        try:
                            with open(p_item, "rb") as f:
                                used_reel_hashes.add(hashlib.sha256(f.read()).hexdigest())
                        except Exception:
                            pass
                elif isinstance(item, str) and len(item) == 64:
                    used_reel_hashes.add(item)

        # 3. Configure providers
        is_testing = (
            mock_mode
            or os.getenv("TESTING", "").lower() in ("true", "1")
            or os.getenv("MOCK_IMAGE_GEN", "").lower() in ("true", "1")
        )

        active_provider_name = "mock" if is_testing else (provider_name or IMAGE_PROVIDER)
        primary_provider = get_image_provider(active_provider_name)
        should_check_perm = active_provider_name not in ("curated", "mock", "synthetic")

        fallback_provider: Optional[BaseImageProvider] = None
        if not is_testing and IMAGE_FALLBACK_PROVIDER and IMAGE_FALLBACK_PROVIDER != active_provider_name:
            if IMAGE_FALLBACK_PROVIDER.lower() not in ("mock", "none", ""):
                try:
                    fallback_provider = get_image_provider(IMAGE_FALLBACK_PROVIDER)
                except Exception as e:
                    logger.debug(f"Fallback provider init notice: {e}")

        # 4. Execute generation loop with retries and alternate seeds
        last_error: Optional[Exception] = None
        fallback_allowed = allow_static_fallback if allow_static_fallback is not None else ALLOW_STATIC_FALLBACK
        total_attempts = 1 if fallback_allowed else cls.MAX_RETRIES

        for attempt in range(1, total_attempts + 1):
            seed = random.randint(100000, 99999999) + (scene_idx * 1000) + (attempt * 100)
            unique_id = hashlib.sha256(f"{clean_slug}_{scene_idx}_{seed}_{attempt}_{time.time_ns()}".encode()).hexdigest()[:10]
            target_filename = f"{clean_slug}_sc{scene_idx + 1}_{unique_id}.jpg"
            target_path = out_dir / target_filename

            # Choose provider for this attempt
            provider = primary_provider
            raw_bytes: Optional[bytes] = None

            try:
                raw_bytes = provider.generate(
                    prompt=prompt,
                    width=VIDEO_WIDTH,
                    height=VIDEO_HEIGHT,
                    seed=seed,
                    scene_idx=scene_idx,
                )
            except ImageProviderError as pe:
                last_error = pe
                if fallback_provider and attempt >= 2:
                    logger.warning(f"Primary provider failed ({pe}). Attempting fallback provider '{fallback_provider.name}'...")
                    try:
                        raw_bytes = fallback_provider.generate(
                            prompt=prompt,
                            width=VIDEO_WIDTH,
                            height=VIDEO_HEIGHT,
                            seed=seed,
                            scene_idx=scene_idx,
                        )
                    except Exception as fe:
                        last_error = fe
                        logger.warning(f"Fallback provider also failed: {fe}")
                else:
                    logger.warning(f"Attempt {attempt}/{total_attempts} generation failed: {pe}")
                    time.sleep(1.0 * attempt)
                    continue

            if not raw_bytes:
                continue

            # 5. Process and normalize image geometry
            try:
                img = Image.open(io.BytesIO(raw_bytes))
                img.verify()
                img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")

                # Guarantee vertical 9:16 (1080x1920) fit
                if img.size != (VIDEO_WIDTH, VIDEO_HEIGHT):
                    img = ImageOps.fit(img, (VIDEO_WIDTH, VIDEO_HEIGHT), Image.Resampling.LANCZOS)

                # Save candidate to disk for validation
                img.save(target_path, "JPEG", quality=95)
            except Exception as proc_err:
                last_error = proc_err
                logger.warning(f"Failed processing generated image bytes on attempt {attempt}: {proc_err}")
                if target_path.exists():
                    target_path.unlink()
                continue

            # 6. Quality & Relevance Gate
            should_check_perm = active_provider_name not in ("curated", "mock", "synthetic")
            report: VisualValidationReport = VisionQualityGate.validate_scene_image(
                image_input=target_path,
                plan=plan,
                check_permanent_duplicates=should_check_perm,
                used_reel_hashes=used_reel_hashes,
            )

            if not report.passed:
                last_error = ImageGenerationError(f"Quality gate rejected asset: {report.rejection_reason}")
                logger.warning(f"[AIImageGenerator] Scene {scene_idx + 1} attempt {attempt} rejected: {report.rejection_reason}")
                if target_path.exists():
                    target_path.unlink()
                # If duplicate detected, vary the prompt framing slightly for the next attempt
                if report.duplicate_status:
                    prompt = f"{prompt}, angle variation {attempt}, distinct lighting"
                time.sleep(0.5 * attempt)
                continue

            # 7. Success! Commit to Permanent Visual Memory & Traceability
            plan.validation_passed = True
            rec = PermanentVisualMemory.record_used_visual(
                image_input=target_path,
                source_identity=target_path.name,
                scene_description=prompt,
                script_id=clean_slug,
                reel_id=clean_slug,
                topic=topic,
                scene_idx=scene_idx,
            )
            if hasattr(plan, "used_fingerprints"):
                plan.used_fingerprints.append(rec["sha256"])

            # Persist Script-to-Image Traceability Metadata (Task 10)
            try:
                from app.video.scene_visual_intelligence import SceneVisualIntelligence
                SceneVisualIntelligence.record_traceability(
                    reel_id=clean_slug,
                    scene_id=scene_idx + 1,
                    narration=getattr(plan, "narration", getattr(plan, "exact_narration", "")),
                    visual_concept=getattr(plan, "visual_concept", getattr(plan, "main_subject", "")),
                    emotion=getattr(plan, "emotion", getattr(plan, "mood", "")),
                    image_prompt=prompt,
                    generation_model=active_provider_name,
                    image_hash=rec.get("sha256", ""),
                    quality_review={
                        "passed": report.passed,
                        "semantic_relevance_score": getattr(report, "semantic_relevance_score", 1.0),
                        "rejection_reason": report.rejection_reason,
                    },
                )
            except Exception as tr_err:
                logger.debug(f"Traceability record notice: {tr_err}")

            if used_images is not None:
                used_images.add(target_path)
                used_images.add(target_path.name)
                used_images.add(rec["sha256"])

            logger.info(
                f"[AIImageGenerator] Scene {scene_idx + 1}/{total_scenes}: Successfully generated fresh AI visual -> {target_path.name} "
                f"(SHA256={rec['sha256'][:10]}... | Subject='{plan.primary_subject}')"
            )
            return target_path

        # 8. Primary generation exhausted/rejected -> Trigger MANDATORY SEMANTIC FALLBACK
        fallback_strategy = getattr(plan, "fallback_visual_strategy", "")
        fallback_prompt = getattr(plan, "fallback_generation_prompt", "")
        if not fallback_prompt or not fallback_strategy:
            sem = SceneVisualPlanner.resolve_semantic_strategies(getattr(plan, "exact_narration", ""), topic)
            fallback_strategy = sem["fallback_visual_strategy"]
            fallback_prompt = sem["fallback_generation_prompt"]
            plan.fallback_visual_strategy = fallback_strategy
            plan.fallback_generation_prompt = fallback_prompt
            if not getattr(plan, "visual_intent", ""):
                plan.visual_intent = sem["visual_intent"]
            if not getattr(plan, "required_entities", []):
                plan.required_entities = sem["required_entities"]
            if not getattr(plan, "primary_visual_strategy", ""):
                plan.primary_visual_strategy = sem["primary_visual_strategy"]

        logger.info(
            f"[AIImageGenerator] Triggering SEMANTIC FALLBACK: '{fallback_strategy}' "
            f"for scene {scene_idx + 1} narration: '{getattr(plan, 'exact_narration', '')}'"
        )

        # Execute semantic fallback generation attempts
        fb_attempts = 1 if (is_testing or fallback_allowed) else cls.MAX_RETRIES
        for fb_attempt in range(1, fb_attempts + 1):
            fb_seed = random.randint(100000, 99999999) + (scene_idx * 2000) + (fb_attempt * 300)
            fb_unique_id = hashlib.sha256(f"{clean_slug}_{scene_idx}_fb_{fb_seed}_{fb_attempt}_{time.time_ns()}".encode()).hexdigest()[:10]
            fb_target_filename = f"{clean_slug}_sc{scene_idx + 1}_fallback_{fb_unique_id}.jpg"
            fb_target_path = out_dir / fb_target_filename

            fb_bytes: Optional[bytes] = None
            try:
                fb_bytes = primary_provider.generate(
                    prompt=fallback_prompt,
                    width=VIDEO_WIDTH,
                    height=VIDEO_HEIGHT,
                    seed=fb_seed,
                    scene_idx=scene_idx,
                )
            except Exception as pe:
                last_error = pe
                if fallback_provider:
                    try:
                        fb_bytes = fallback_provider.generate(
                            prompt=fallback_prompt,
                            width=VIDEO_WIDTH,
                            height=VIDEO_HEIGHT,
                            seed=fb_seed,
                            scene_idx=scene_idx,
                        )
                    except Exception as fe:
                        last_error = fe
                if not fb_bytes:
                    continue

            # Process and normalize image geometry
            try:
                fb_img = Image.open(io.BytesIO(fb_bytes))
                fb_img.verify()
                fb_img = Image.open(io.BytesIO(fb_bytes)).convert("RGB")
                if fb_img.size != (VIDEO_WIDTH, VIDEO_HEIGHT):
                    fb_img = ImageOps.fit(fb_img, (VIDEO_WIDTH, VIDEO_HEIGHT), Image.Resampling.LANCZOS)
                fb_img.save(fb_target_path, "JPEG", quality=95)
            except Exception as proc_err:
                last_error = proc_err
                if fb_target_path.exists():
                    fb_target_path.unlink()
                continue

            # Validate fallback asset against plan & duplicate history
            fb_report = VisionQualityGate.validate_scene_image(
                image_input=fb_target_path,
                plan=plan,
                check_permanent_duplicates=should_check_perm,
                used_reel_hashes=used_reel_hashes,
            )

            if not fb_report.passed:
                last_error = ImageGenerationError(f"Semantic fallback rejected by quality gate: {fb_report.rejection_reason}")
                logger.warning(f"[AIImageGenerator] Scene {scene_idx + 1} semantic fallback rejected: {fb_report.rejection_reason}")
                if fb_target_path.exists():
                    fb_target_path.unlink()
                time.sleep(0.5 * fb_attempt)
                continue

            # Semantic fallback accepted!
            plan.validation_passed = True
            rec = PermanentVisualMemory.record_used_visual(
                image_input=fb_target_path,
                source_identity=fb_target_path.name,
                scene_description=fallback_prompt,
                script_id=clean_slug,
                reel_id=clean_slug,
                topic=topic,
                scene_idx=scene_idx,
            )

            if hasattr(plan, "used_fingerprints"):
                plan.used_fingerprints.append(rec["sha256"])

            # Traceability record
            try:
                from app.video.scene_visual_intelligence import SceneVisualIntelligence
                SceneVisualIntelligence.record_traceability(
                    reel_id=clean_slug,
                    scene_id=scene_idx + 1,
                    narration=getattr(plan, "narration", getattr(plan, "exact_narration", "")),
                    visual_concept=fallback_strategy,
                    emotion=getattr(plan, "emotion", getattr(plan, "mood", "")),
                    image_prompt=fallback_prompt,
                    generation_model=active_provider_name,
                    image_hash=rec.get("sha256", ""),
                    quality_review={
                        "passed": True,
                        "is_semantic_fallback": True,
                        "fallback_visual_strategy": fallback_strategy,
                    },
                )
            except Exception as tr_err:
                logger.debug(f"Traceability record notice: {tr_err}")

            if used_images is not None:
                used_images.add(fb_target_path)
                used_images.add(fb_target_path.name)
                used_images.add(rec["sha256"])

            logger.info(
                f"[AIImageGenerator] Scene {scene_idx + 1}/{total_scenes}: Successfully generated SEMANTIC FALLBACK visual -> {fb_target_path.name} "
                f"(SHA256={rec['sha256'][:10]}... | Fallback Strategy='{fallback_strategy}')"
            )
            return fb_target_path

        # 9. Exhausted both primary and semantic fallback
        plan.validation_passed = False
        if fallback_allowed:
            logger.warning(f"[AIImageGenerator] AI generation & semantic fallback exhausted, but ALLOW_STATIC_FALLBACK=True. Delegating to static fallback...")
            from app.video.dynamic_visual_engine import DynamicVisualEngine
            return DynamicVisualEngine._legacy_static_broll_fallback(
                scene_dict=scene_dict,
                topic=topic,
                scene_idx=scene_idx,
                total_scenes=total_scenes,
                target_file=out_dir / f"{clean_slug}_sc{scene_idx + 1}_fallback.jpg",
                used_images=used_images or set(),
            )

        # STRICT MANDATE: Fail safely! Never silently substitute unrelated B-roll.
        raise ImageGenerationError(
            f"Failed to generate fresh AI image / scene-appropriate visual for scene {scene_idx + 1}/{total_scenes} "
            f"('{getattr(plan, 'exact_narration', '')}'). Exhausted primary strategy ('{getattr(plan, 'primary_visual_strategy', '')}') "
            f"and semantic fallback strategy ('{fallback_strategy}'). Last error: {last_error}"
        )

    @classmethod
    def generate_reel_visuals(
        cls,
        scenes: List[Dict[str, Any]],
        topic: str,
        reel_slug: Optional[str] = None,
        used_images: Optional[Set[Any]] = None,
        target_dir: Optional[Path] = None,
        mock_mode: bool = False,
    ) -> List[Path]:
        """
        Generates dedicated, 100% unique fresh AI images for all scenes in a Reel.
        Guarantees that each scene gets an independently generated image matching its visual brief.
        """
        if not scenes:
            raise ImageGenerationError("Cannot generate visuals: Script contains no scenes.")

        assigned_images: List[Path] = []
        tracking_set: Set[Any] = set(used_images) if used_images else set()
        clean_slug = reel_slug or re.sub(r"[^\w]", "_", topic.lower())[:20].strip("_")

        # Plan visuals for all scenes with diversity across consecutive scenes
        plans = SceneVisualPlanner.plan_reel_visuals(scenes=scenes, topic=topic)

        for idx, sc in enumerate(scenes):
            sc["visual_plan"] = plans[idx].to_dict()
            img_path = cls.generate_scene_image(
                scene_dict=sc,
                topic=topic,
                scene_idx=idx,
                total_scenes=len(scenes),
                reel_slug=clean_slug,
                used_images=tracking_set,
                target_dir=target_dir,
                mock_mode=mock_mode,
            )
            assigned_images.append(img_path)
            tracking_set.add(img_path)
            tracking_set.add(img_path.name)

        return assigned_images
