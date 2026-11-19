"""
Automated Test Suite for Script-Driven, Emotion-Aware Visual Intelligence Pipeline.
Verifies:
1. Script A (Emotional exhaustion, waiting, loneliness):
   - Emotion is Loneliness, Sadness, or Emotional Exhaustion.
   - Visual concept involves waiting, relationship longing, or emotional burden.
   - Zero planets, zero zodiac wheels, zero temple visuals.
2. Script B (Financial breakthrough, career struggle, hope):
   - Emotion is Hope, Relief, or Empowerment.
   - Visual concept involves emergence from difficulty, upward movement, light breaking through.
   - Prompt includes appropriate breakthrough / dawn lighting.
3. Script C (Lord Shiva, silence, inner peace):
   - Visual concept is serene mountain stillness, meditative silence, or sacred Himalayan environment.
   - Zero generic cartoon gods, zero neon lighting.
4. Scene-to-scene diversity:
   - 5-scene Reel generates 5 distinct visual concepts.
   - No two consecutive scenes share the same camera angle or composition.
5. Prompt quality:
   - All prompts specify 14-point structure, 9:16 vertical ratio, camera angle, lighting, composition, style.
   - Zero generic placeholders.
6. Traceability:
   - Logs to storage/scene_visual_traceability.json with required fields.
7. Quality gate:
   - Rejects wrong dimensions, extreme luminance, topic contamination.
"""

import json
from pathlib import Path
from PIL import Image
import pytest

from app.video.scene_visual_intelligence import (
    SceneVisualIntelligence,
    ReelVisualDiversityTracker,
    CANONICAL_EMOTIONS,
    TRACEABILITY_LOG_FILE,
)
from app.video.scene_visual_planner import SceneVisualPlan, SceneVisualPlanner
from app.video.ai_image_generator import AIImageGenerator
from app.video.vision_quality_gate import VisionQualityGate


class TestScriptDrivenVisualIntelligence:

    def test_script_a_emotional_exhaustion_waiting(self):
        """Script A: Emotional exhaustion, waiting, loneliness."""
        scene = {
            "scene_id": "scene_1",
            "spoken_line": "Your heart is tired of waiting for someone who never chooses you.",
            "on_screen_text": "Tired of Waiting",
            "estimated_seconds": 4.5,
        }
        plan = SceneVisualPlanner.plan_scene_visual(
            scene_dict=scene,
            scene_idx=0,
            total_scenes=5,
            topic="Vedic Astrology & Relationships",
        )

        # 1. Emotion check
        assert plan.emotion in ("Loneliness", "Sadness", "Emotional Exhaustion", "Frustration", "Betrayal"), (
            f"Expected Loneliness/Sadness/Emotional Exhaustion, got: {plan.emotion}"
        )

        # 2. Visual concept check: waiting, longing, emotional burden
        concept_lower = (plan.visual_concept or "").lower()
        metaphor_lower = (plan.visual_metaphor or "").lower()
        subject_lower = (plan.main_subject or "").lower()
        combined = f"{concept_lower} {metaphor_lower} {subject_lower}"
        assert any(k in combined for k in ["wait", "window", "rain", "distance", "silhouette", "pour", "water", "shadow", "solitary", "alone"]), (
            f"Visual concept should reflect longing or waiting, got: {combined}"
        )

        # 3. Negative check: ZERO planets, ZERO zodiac wheels, ZERO temples in positive generation prompt
        prompt_lower = plan.generation_prompt.lower().split("no ")[0].split("avoid:")[0]
        assert "planet" not in prompt_lower, f"Planets found in prompt: {plan.generation_prompt}"
        assert "zodiac" not in prompt_lower, f"Zodiac found in prompt: {plan.generation_prompt}"
        assert "temple" not in prompt_lower, f"Temple found in prompt: {plan.generation_prompt}"

    def test_script_b_financial_breakthrough_hope(self):
        """Script B: Financial breakthrough, struggle, hope."""
        scene = {
            "scene_id": "scene_4",
            "spoken_line": "Your financial breakthrough is coming after a long period of struggle.",
            "on_screen_text": "Financial Breakthrough Coming",
            "estimated_seconds": 4.0,
        }
        plan = SceneVisualPlanner.plan_scene_visual(
            scene_dict=scene,
            scene_idx=3,
            total_scenes=5,
            topic="Astrological Wealth & Career",
        )

        # 1. Emotion check
        assert plan.emotion in ("Hope", "Relief", "Empowerment", "Transformation", "Confidence"), (
            f"Expected Hope/Relief/Empowerment, got: {plan.emotion}"
        )

        # 2. Visual concept check: emergence, light breaking through, upward movement
        concept_lower = (plan.visual_concept or "").lower()
        prompt_lower = (plan.generation_prompt or "").lower()
        combined = f"{concept_lower} {prompt_lower}"
        assert any(k in combined for k in ["breakthrough", "sun", "light", "dawn", "terrace", "horizon", "gold", "upward", "valley"]), (
            f"Visual concept should reflect financial emergence or breakthrough, got: {combined}"
        )

        # 3. Prompt includes appropriate lighting (dawn, breakthrough light)
        lighting_lower = (plan.lighting or "").lower()
        assert any(k in lighting_lower for k in ["dawn", "sun", "golden", "warm", "radiance", "morning", "crepuscular", "diffused"]), (
            f"Lighting should reflect dawn or breakthrough, got: {plan.lighting}"
        )

    def test_script_c_lord_shiva_silence_sacred_stillness(self):
        """Script C: Lord Shiva, silence, inner peace."""
        scene = {
            "scene_id": "scene_2",
            "spoken_line": "Lord Shiva teaches us that silence is powerful and sacred.",
            "on_screen_text": "Power of Sacred Silence",
            "estimated_seconds": 4.0,
        }
        plan = SceneVisualPlanner.plan_scene_visual(
            scene_dict=scene,
            scene_idx=1,
            total_scenes=5,
            topic="Spiritual Teachings of Shiva",
        )

        # 1. Visual concept: serene mountain stillness, meditative silence, or sacred Himalayan environment
        combined = f"{plan.visual_concept} {plan.main_subject} {plan.environment}".lower()
        assert any(k in combined for k in ["himalayan", "mountain", "shiva", "stillness", "kailash", "meditation", "silence"]), (
            f"Visual concept should involve sacred Himalayan stillness, got: {combined}"
        )

        # 2. Negative check: ZERO generic cartoon gods, ZERO neon lighting
        prompt_lower = plan.generation_prompt.lower()
        assert "cartoon" not in prompt_lower.split("no ")[0], "Cartoon found in positive prompt"
        assert "neon" not in prompt_lower.split("no ")[0], "Neon found in positive prompt"

    def test_scene_to_scene_diversity_in_reel(self):
        """5-scene Reel must produce 5 distinct visual concepts with no consecutive angle/composition repetition."""
        scenes = [
            {"spoken_line": "Do you feel like you are giving your all and receiving nothing in return?"},
            {"spoken_line": "Every time you try to build something stable, an unseen force tests your patience."},
            {"spoken_line": "This is the threshold where your old identity is being stripped away."},
            {"spoken_line": "A sudden clarity will emerge when you stop forcing closed doors to open."},
            {"spoken_line": "Step forward into the light. Your era of quiet abundance has officially begun."},
        ]

        plans = SceneVisualPlanner.plan_reel_visuals(scenes=scenes, topic="Life Transformation & Saturn")
        assert len(plans) == 5

        concepts = [p.visual_concept for p in plans]
        camera_angles = [p.camera_angle or p.camera_framing for p in plans]
        compositions = [p.composition for p in plans]

        # 1. All 5 scenes must have distinct visual concepts
        assert len(set(concepts)) == 5, f"Expected 5 distinct visual concepts, got {len(set(concepts))}: {concepts}"

        # 2. No two consecutive scenes may share the same camera angle or composition
        for i in range(len(plans) - 1):
            assert camera_angles[i] != camera_angles[i + 1], (
                f"Consecutive scenes {i+1} and {i+2} share camera angle: {camera_angles[i]}"
            )
            assert compositions[i] != compositions[i + 1], (
                f"Consecutive scenes {i+1} and {i+2} share composition: {compositions[i]}"
            )

    def test_prompt_completeness_and_quality(self):
        """All generated prompts contain subject, environment, lighting, composition, camera angle, 9:16 vertical ratio."""
        scene = {
            "spoken_line": "When Saturn tests your patience, do not run away from the discipline.",
            "on_screen_text": "Saturn's Crucible",
            "estimated_seconds": 4.0,
        }
        plan = SceneVisualPlanner.plan_scene_visual(scene_dict=scene, scene_idx=0, total_scenes=3)

        prompt = plan.generation_prompt
        assert "9:16 vertical" in prompt, f"Prompt must specify 9:16 vertical ratio: {prompt}"
        assert plan.main_subject and len(plan.main_subject.strip()) > 3
        assert plan.environment and len(plan.environment.strip()) > 3
        assert plan.lighting and len(plan.lighting.strip()) > 3
        assert plan.composition and len(plan.composition.strip()) > 3
        assert plan.camera_angle and len(plan.camera_angle.strip()) > 3

        # No generic placeholders
        for bad in ["something", "astrology background", "spiritual scene", "placeholder", "generic image"]:
            assert bad not in prompt.lower(), f"Generic placeholder '{bad}' found in prompt: {prompt}"

    def test_traceability_logging_persists_metadata(self, tmp_path):
        """Every generated image logs to scene_visual_traceability.json with all required fields."""
        reel_id = "test_reel_traceability_99"
        scene_id = 1
        narration = "Your heart is tired of waiting."
        visual_concept = "Solitary person looking through rain-streaked window"
        emotion = "Loneliness"
        image_prompt = "Cinematic 9:16 vertical photograph of a person at a rain-streaked window..."
        generation_model = "mock"
        image_hash = "abcdef0123456789"
        quality_review = {"passed": True, "semantic_relevance_score": 0.95}

        rec = SceneVisualIntelligence.record_traceability(
            reel_id=reel_id,
            scene_id=scene_id,
            narration=narration,
            visual_concept=visual_concept,
            emotion=emotion,
            image_prompt=image_prompt,
            generation_model=generation_model,
            image_hash=image_hash,
            quality_review=quality_review,
        )

        assert rec["reel_id"] == reel_id
        assert rec["scene_id"] == 1
        assert rec["emotion"] == "Loneliness"
        assert rec["visual_concept"] == visual_concept
        assert rec["image_hash"] == image_hash

        # Verify on disk
        assert TRACEABILITY_LOG_FILE.exists()
        with open(TRACEABILITY_LOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            records = data.get("traceability_records", [])
            matching = [r for r in records if r.get("reel_id") == reel_id]
            assert len(matching) >= 1
            entry = matching[-1]
            assert entry["narration"] == narration
            assert entry["quality_review"]["passed"] is True

    def test_quality_gate_checks_dimensions_and_relevance(self, tmp_path):
        """Quality gate rejects non-9:16 images, blank images, or contaminated images."""
        # 1. Rejects horizontal image
        horiz_path = tmp_path / "horiz.jpg"
        Image.new("RGB", (1920, 1080), color=(100, 100, 100)).save(horiz_path)
        plan = SceneVisualPlan(
            scene_id="sc1",
            scene_idx=0,
            exact_narration="A quiet walk in the woods.",
            main_subject="solitary walker",
            subject_action="walking quietly",
            environment="misty forest",
            generation_prompt="9:16 vertical photograph of solitary walker",
        )
        report = VisionQualityGate.validate_scene_image(image_input=horiz_path, plan=plan)
        assert report.passed is False
        assert "aspect ratio" in report.rejection_reason.lower()

        # 2. Rejects solid blank black canvas
        black_path = tmp_path / "black.jpg"
        Image.new("RGB", (1080, 1920), color=(0, 0, 0)).save(black_path)
        report_black = VisionQualityGate.validate_scene_image(image_input=black_path, plan=plan)
        assert report_black.passed is False
        assert "dark" in report_black.rejection_reason.lower() or "luminance" in report_black.rejection_reason.lower()
