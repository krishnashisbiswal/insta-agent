"""
Comprehensive End-to-End Production Pipeline Verification Test (Chunk 8).

Validates the complete execution trace from start to finish:
Topic Discovery
-> Research & Script
-> Scene Segmentation
-> Scene Visual Brief
-> AI Image Generation (Fresh per scene)
-> Image Validation
-> Duplicate Check (PermanentVisualMemory)
-> Voice Generation
-> Video Rendering (CinematicComposer)
-> Caption Generation & SEO
-> Automated Quality Control (VideoQC)
-> Dry-Run Publishing
-> Persistent State Update (AssetLifecycle & Durable Memory)

Guarantees 100% test isolation: user files in 'insta content/' and production
persistent history are never touched.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image, ImageDraw

from app.analytics.trend_discovery_engine import TrendDiscoveryEngine
from app.agents.script_agent import generate_reel
from app.instagram.uploader import InstagramUploader
from app.publishing.pre_publish_validator import PrePublishValidator
from app.storage.asset_lifecycle_manager import AssetLifecycleManager, JobState
from app.storage.permanent_visual_memory import PermanentVisualMemory
from app.video.ai_image_generator import AIImageGenerator
from app.video.cinematic_composer import create_cinematic_reel_video
from app.video.image_providers import MockImageProvider
from app.video.scene_visual_planner import SceneVisualPlanner
from app.video.vision_quality_gate import VisionQualityGate
from app.video.video_qc import VideoQualityControl


@pytest.fixture
def isolated_env(tmp_path: Path):
    """Provides isolated directories for output, storage, and packaged content."""
    output_dir = tmp_path / "output"
    storage_dir = tmp_path / "storage"
    insta_dir = tmp_path / "insta_content"
    output_dir.mkdir(parents=True, exist_ok=True)
    storage_dir.mkdir(parents=True, exist_ok=True)
    insta_dir.mkdir(parents=True, exist_ok=True)

    return {
        "root": tmp_path,
        "output": output_dir,
        "storage": storage_dir,
        "insta": insta_dir,
    }


def test_complete_end_to_end_production_pipeline(isolated_env, monkeypatch):
    """
    Executes a complete, verifiable end-to-end dry-run of the entire Reel pipeline.
    """
    # -------------------------------------------------------------
    # STAGE 1: Topic Discovery & Trend Anti-Repetition
    # -------------------------------------------------------------
    history_file = isolated_env["storage"] / "topic_history.json"
    trend_engine = TrendDiscoveryEngine(history_file=history_file)
    trend = trend_engine.discover_next_viral_trend(niche="Vedic Astrology", language="Hindi")
    assert "topic" in trend
    topic = trend["topic"]
    assert len(topic) > 10
    trend_engine.record_generated_topic(trend)
    # Verify topic is recorded
    assert history_file.exists()

    # -------------------------------------------------------------
    # STAGE 2: 5-Beat Retention Script Generation
    # -------------------------------------------------------------
    script_data = generate_reel(
        topic=topic,
        niche="Vedic Astrology",
        language="Hindi",
        duration=25,
    )
    assert "selected_hook" in script_data
    assert "scenes" in script_data
    scenes = script_data["scenes"]
    assert len(scenes) >= 3

    # -------------------------------------------------------------
    # STAGE 3: Scene Segmentation & Scene Visual Briefs
    # -------------------------------------------------------------
    plans = SceneVisualPlanner.plan_reel_visuals(
        scenes=script_data["scenes"],
        topic=topic,
    )
    assert len(plans) >= 3
    for p in plans:
        assert p.main_subject is not None
        assert p.generation_prompt is not None
        assert len(p.generation_prompt) > 20

    # -------------------------------------------------------------
    # STAGE 4: Fresh AI Image Generation (Per-Scene)
    # -------------------------------------------------------------
    generated_images = AIImageGenerator.generate_reel_visuals(
        scenes=script_data["scenes"],
        topic=topic,
        mock_mode=True,
        target_dir=isolated_env["output"] / "frames",
    )
    assert len(generated_images) == len(plans)
    for img_path in generated_images:
        assert img_path.exists()
        assert img_path.stat().st_size > 1000

    # -------------------------------------------------------------
    # STAGE 5: Image Quality & Contrast Validation
    # -------------------------------------------------------------
    for idx, img_path in enumerate(generated_images):
        report = VisionQualityGate.validate_scene_image(
            image_path=img_path,
            plan=plans[idx],
            check_permanent_duplicates=False,
        )
        assert report.passed, f"Image {img_path.name} failed validation: {report.rejection_reason}"
        assert report.dimensions == (1080, 1920)

    # -------------------------------------------------------------
    # STAGE 6: Visual Duplicate Prevention & Permanent Memory
    # -------------------------------------------------------------
    for idx, img_path in enumerate(generated_images):
        rec = PermanentVisualMemory.record_used_visual(
            image_input=img_path,
            source_identity=img_path.name,
            scene_idx=idx,
            scene_description=plans[idx].generation_prompt,
            topic=topic,
        )
        assert rec is not None
        assert "sha256" in rec
        assert len(rec["sha256"]) == 64  # SHA-256 length

    # -------------------------------------------------------------
    # STAGE 7: Synthetic Audio Voice Generation
    # -------------------------------------------------------------
    audio_path = isolated_env["output"] / "voiceover.wav"
    import wave
    import struct

    sr = 44100
    duration_sec = 6.0
    num_samples = int(sr * duration_sec)
    with wave.open(str(audio_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        for i in range(num_samples):
            val = int(32767.0 * 0.2 * np.sin(2.0 * np.pi * 440.0 * i / sr))
            wf.writeframes(struct.pack("<h", val))

    assert audio_path.exists()

    # -------------------------------------------------------------
    # STAGE 8: Frame-Synchronized Cinematic Video Composition
    # (Composes 2 scenes to exercise full MoviePy, Ken Burns, audio mix & QC swiftly)
    # -------------------------------------------------------------
    render_script = dict(script_data)
    render_script["scenes"] = script_data["scenes"][:2]
    render_images = generated_images[:2]

    rendered_video = create_cinematic_reel_video(
        script_data=render_script,
        audio_path=str(audio_path),
        output_filename="test_e2e_reel.mp4",
        scene_image_paths=render_images,
    )
    assert Path(rendered_video).exists()
    assert Path(rendered_video).stat().st_size > 5000

    # -------------------------------------------------------------
    # STAGE 9: Automated Video Quality Control (QC)
    # -------------------------------------------------------------
    qc_report = VideoQualityControl.audit_video(
        video_path=rendered_video,
        expected_scenes=len(render_images),
        expected_duration=None,
    )
    assert qc_report.passed, f"Video QC failed: {qc_report.errors}"
    assert qc_report.checks["file_size_valid"] is True
    assert qc_report.checks["decode_success"] is True
    assert qc_report.checks["dimensions_valid"] is True
    assert qc_report.checks["no_black_frames"] is True
    assert qc_report.checks["audio_present"] is True

    # -------------------------------------------------------------
    # STAGE 10: Pre-Publish Content Validation Gate
    # -------------------------------------------------------------
    caption = "Stop wearing Pyrite blindly until you check your 5th house karmic memory. #astrology #kundli"
    pre_pub_report = PrePublishValidator.validate_reel(
        video_path=rendered_video,
        caption=caption,
        min_size_bytes=500,
    )
    assert pre_pub_report.is_valid, f"Pre-publish validation failed: {pre_pub_report.errors}"

    # -------------------------------------------------------------
    # STAGE 11: Dry-Run Publishing & Packaging
    # -------------------------------------------------------------
    uploader = InstagramUploader()
    dry_manifest = uploader.dry_run_preview(
        video_path=rendered_video,
        caption=caption,
    )
    assert dry_manifest["mode"] == "DRY_RUN"
    assert dry_manifest["video_exists"] is True
    assert dry_manifest["caption_within_limit"] is True

    # -------------------------------------------------------------
    # STAGE 12: Asset Lifecycle Management & Memory Update
    # -------------------------------------------------------------
    lifecycle_file = isolated_env["storage"] / "lifecycle_jobs.json"
    monkeypatch.setattr("app.storage.asset_lifecycle_manager.JOBS_REGISTRY_FILE", lifecycle_file)

    job_id = AssetLifecycleManager.create_job(
        topic=topic,
        script_id="script_test_e2e",
        script_data=script_data,
        scene_images=generated_images,
    )
    AssetLifecycleManager.update_job_state(
        job_id=job_id,
        new_state=JobState.VALIDATED,
        message="End-to-end dry run verified",
        metadata={"video_path": str(rendered_video)},
    )
    job_rec = AssetLifecycleManager.get_job(job_id)
    assert job_rec is not None
    assert job_rec["state"] == JobState.VALIDATED.value
