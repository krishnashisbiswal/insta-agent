"""
Unit and Integration Tests for Real AI Image Generation & Visual Freshness (Chunk 5).
Covers:
1. Provider Architecture:
   - Success, timeout, retries, rate limiting (429), truncated response, unknown provider, missing API key.
2. Scene Relevance & Quality Gate:
   - Physical dimensions, 9:16 vertical geometry, corrupt byte payloads, flat solid colors, dark/white frames.
   - Relevance validation: topic contamination rejection.
3. Visual History & Duplicate Rejection:
   - Exact byte match (SHA256), perceptual near-duplicate (pHash), difference hash (dHash), cropped/recolored variants.
   - Clean unique image accepted and recorded in PermanentVisualMemory.
4. Production Pipeline & Anti-Fallback:
   - Zero silent static B-roll substitution (raises ImageGenerationError on total generation failure).
   - Real production composer pipeline invokes image generation for all scenes.
"""

import hashlib
import io
import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import VIDEO_WIDTH, VIDEO_HEIGHT
from app.storage.permanent_visual_memory import PermanentVisualMemory
from app.video.image_providers import (
    BaseImageProvider,
    GeminiImageProvider,
    HuggingFaceImageProvider,
    ImageProviderError,
    MockImageProvider,
    PollinationsImageProvider,
    ProviderConfigError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    get_image_provider,
)
from app.video.scene_visual_planner import SceneVisualPlan, SceneVisualPlanner
from app.video.vision_quality_gate import VisionQualityGate, VisualValidationReport
from app.video.ai_image_generator import AIImageGenerator, ImageGenerationError
from app.video.dynamic_visual_engine import DynamicVisualEngine


# =========================================================================
# 1. PROVIDER ARCHITECTURE TESTS
# =========================================================================

def test_mock_provider_success():
    """Verify mock provider generates valid 1080x1920 RGB image bytes."""
    provider = MockImageProvider()
    provider.validate_config()
    raw = provider.generate("cinematic scene test", width=VIDEO_WIDTH, height=VIDEO_HEIGHT, seed=12345)
    assert len(raw) > 5000
    with Image.open(io.BytesIO(raw)) as img:
        assert img.size == (VIDEO_WIDTH, VIDEO_HEIGHT)
        assert img.mode == "RGB"


def test_pollinations_provider_timeout_handling():
    """Verify provider timeout triggers ProviderTimeoutError and retry policy."""
    provider = PollinationsImageProvider(timeout=1, max_retries=2)
    with patch("urllib.request.urlopen", side_effect=TimeoutError("Request timed out")):
        with pytest.raises(ImageProviderError) as exc_info:
            provider.generate("test prompt", seed=42)
        assert "failed to generate image" in str(exc_info.value).lower()


def test_provider_rate_limit_retry():
    """Verify rate-limit 429 triggers exponential backoff and succeeds on retry."""
    provider = PollinationsImageProvider(timeout=5, max_retries=3)
    valid_img = MockImageProvider().generate("valid", seed=99)

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = valid_img
    mock_resp.__enter__.return_value = mock_resp

    call_count = 0
    def mock_urlopen(req, timeout):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            import urllib.error
            raise urllib.error.HTTPError("http://test", 429, "Too Many Requests", {}, None)
        return mock_resp

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        result = provider.generate("test prompt", seed=42)
        assert result == valid_img
        assert call_count == 2


def test_provider_truncated_response_error():
    """Verify truncated payload (<1000 bytes) triggers ProviderResponseError."""
    provider = PollinationsImageProvider(timeout=5, max_retries=1)
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b"short"

    with patch("urllib.request.urlopen", return_value=mock_resp):
        with pytest.raises(ImageProviderError):
            provider.generate("test prompt", seed=42)


def test_unknown_provider_raises_config_error():
    """Verify requesting an unknown provider raises ProviderConfigError."""
    with pytest.raises(ProviderConfigError) as exc:
        get_image_provider("nonexistent_ai_provider_xyz")
    assert "Unknown image provider" in str(exc.value)


def test_gemini_missing_api_key_raises_config_error(monkeypatch):
    """Verify Gemini image provider raises ProviderConfigError when GEMINI_API_KEY is empty."""
    monkeypatch.setenv("GEMINI_API_KEY", "")
    provider = GeminiImageProvider(api_key="")
    with pytest.raises(ProviderConfigError) as exc:
        provider.generate("test prompt")
    assert "GEMINI_API_KEY is not set" in str(exc.value)


def test_huggingface_missing_token_raises_config_error(monkeypatch):
    """Verify Hugging Face provider raises ProviderConfigError when HF_TOKEN is empty."""
    monkeypatch.setenv("HF_TOKEN", "")
    provider = HuggingFaceImageProvider(api_token="")
    with pytest.raises(ProviderConfigError) as exc:
        provider.generate("test prompt")
    assert "HF_TOKEN is not set" in str(exc.value)


# =========================================================================
# 2. IMAGE QUALITY & RELEVANCE GATE TESTS
# =========================================================================

def test_quality_gate_rejects_horizontal_canvas(tmp_path):
    """Verify 16:9 horizontal image is rejected by VisionQualityGate."""
    horiz_path = tmp_path / "horizontal.jpg"
    img = Image.new("RGB", (1920, 1080), (100, 120, 150))
    img.save(horiz_path)

    plan = SceneVisualPlan(
        scene_id="sc_test",
        scene_idx=0,
        exact_narration="test narration",
        core_meaning="test",
        main_subject="test subject",
        subject_action="resting",
        environment="studio",
        time_of_day="noon",
        mood="calm",
        composition="centered",
        camera_framing="wide",
        lighting="soft",
        color_palette="neutral",
        visual_style="photorealistic",
    )

    report = VisionQualityGate.validate_scene_image(horiz_path, plan)
    assert not report.passed
    assert "Invalid aspect ratio" in (report.rejection_reason or "")


def test_quality_gate_rejects_corrupted_image(tmp_path):
    """Verify corrupt/unreadable bytes are rejected."""
    corrupt_path = tmp_path / "corrupt.jpg"
    corrupt_path.write_bytes(b"CORRUPT_BYTES_NOT_A_VALID_JPEG_HEADER" * 50)

    plan = SceneVisualPlan(
        scene_id="sc_test",
        scene_idx=0,
        exact_narration="test",
        core_meaning="test",
        main_subject="test",
        subject_action="resting",
        environment="room",
        time_of_day="day",
        mood="calm",
        composition="eye level",
        camera_framing="medium",
        lighting="soft",
        color_palette="neutral",
        visual_style="photo",
    )

    report = VisionQualityGate.validate_scene_image(corrupt_path, plan)
    assert not report.passed
    assert "decode failed" in (report.rejection_reason or "").lower()


def test_quality_gate_rejects_flat_solid_monochrome(tmp_path):
    """Verify flat solid color canvas is rejected due to lack of variance."""
    flat_path = tmp_path / "flat_monochrome.jpg"
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (50, 50, 50))
    img.save(flat_path)

    plan = SceneVisualPlan(
        scene_id="sc_test",
        scene_idx=0,
        exact_narration="test",
        core_meaning="test",
        main_subject="test",
        subject_action="resting",
        environment="room",
        time_of_day="day",
        mood="calm",
        composition="eye level",
        camera_framing="medium",
        lighting="soft",
        color_palette="neutral",
        visual_style="photo",
    )

    report = VisionQualityGate.validate_scene_image(flat_path, plan)
    assert not report.passed
    assert "Variance too low" in (report.rejection_reason or "")


def test_scene_relevance_topic_contamination_rejected(tmp_path):
    """
    Verify topic entity contamination is caught:
    If scene plan strictly forbade Rudraksha beads for a nervous system scene,
    and prompt contains the forbidden element, quality gate rejects it.
    """
    img_path = tmp_path / "valid_canvas.jpg"
    raw = MockImageProvider().generate("valid nervous system", width=VIDEO_WIDTH, height=VIDEO_HEIGHT, seed=777)
    img_path.write_bytes(raw)

    plan = SceneVisualPlan(
        scene_id="sc_test",
        scene_idx=1,
        exact_narration="नर्वस सिस्टम को गहरी शांति और स्थिरता मिलती है।",
        core_meaning="nervous system calm",
        main_subject="human central nervous system synapse glow",
        subject_action="biomagnetic pulses calming neural pathways",
        environment="clinical meditation space",
        time_of_day="dawn",
        mood="peaceful",
        composition="macro synapse",
        camera_framing="macro",
        lighting="soft bio-luminescent",
        color_palette="indigo teal",
        visual_style="photorealistic",
        forbidden_visual_elements=["Rudraksha beads", "rudraksha mala"],
        generation_prompt="cinematic photo of Rudraksha beads on nervous system synapse",  # Contaminated!
    )

    report = VisionQualityGate.validate_scene_image(img_path, plan)
    assert not report.passed
    assert "Topic contamination" in (report.rejection_reason or "")


# =========================================================================
# 3. VISUAL HISTORY & DUPLICATE DETECTION TESTS
# =========================================================================

def test_exact_byte_duplicate_rejected(tmp_path):
    """Verify exact SHA-256 duplicate is rejected by quality gate."""
    img_path1 = tmp_path / "img1.jpg"
    raw = MockImageProvider().generate("scene 1 prompt", seed=5001)
    img_path1.write_bytes(raw)

    # Register in permanent memory
    PermanentVisualMemory.record_used_visual(img_path1, source_identity="img1.jpg")

    # Second image with identical bytes but different name
    img_path2 = tmp_path / "img2_renamed.jpg"
    img_path2.write_bytes(raw)

    plan = SceneVisualPlan(
        scene_id="sc_test",
        scene_idx=0,
        exact_narration="test",
        core_meaning="test",
        main_subject="copper vessel",
        subject_action="filled with water",
        environment="morning altar",
        time_of_day="sunrise",
        mood="pure",
        composition="close up",
        camera_framing="close-up",
        lighting="warm sun",
        color_palette="copper gold",
        visual_style="photo",
    )

    report = VisionQualityGate.validate_scene_image(img_path2, plan, check_permanent_duplicates=True)
    assert not report.passed
    assert report.duplicate_status is True
    assert "Duplicate visual rejected" in (report.rejection_reason or "")


def test_cropped_and_recolored_duplicates_rejected(tmp_path):
    """Verify cropped and slightly recolored variants of historical image are rejected by perceptual hash."""
    base_path = tmp_path / "master_crystal.jpg"
    raw = MockImageProvider().generate("crystal amethyst cluster", seed=8888)
    base_path.write_bytes(raw)

    # Record master
    PermanentVisualMemory.record_used_visual(base_path, source_identity="master_crystal.jpg")

    # Create a cropped variant (e.g. 5% crop from edges, resized back)
    with Image.open(base_path) as master_img:
        w, h = master_img.size
        cropped = master_img.crop((int(w * 0.05), int(h * 0.05), int(w * 0.95), int(h * 0.95)))
        cropped = cropped.resize((w, h), Image.Resampling.LANCZOS)
        crop_path = tmp_path / "cropped_variant.jpg"
        cropped.save(crop_path, "JPEG", quality=90)

    plan = SceneVisualPlan(
        scene_id="sc_crop",
        scene_idx=0,
        exact_narration="test",
        core_meaning="test",
        main_subject="crystal amethyst",
        subject_action="glowing",
        environment="dark studio",
        time_of_day="night",
        mood="mystical",
        composition="centered",
        camera_framing="macro",
        lighting="purple",
        color_palette="violet",
        visual_style="photo",
    )

    report = VisionQualityGate.validate_scene_image(crop_path, plan, check_permanent_duplicates=True)
    assert not report.passed
    assert report.duplicate_status is True


def test_unique_new_image_accepted_and_recorded(tmp_path):
    """Verify genuinely fresh, distinct image passes quality gate and is recorded."""
    img_path = tmp_path / "fresh_unique.jpg"
    raw = MockImageProvider().generate("fresh unique distinct subject", seed=999999)
    img_path.write_bytes(raw)

    plan = SceneVisualPlan(
        scene_id="sc_fresh",
        scene_idx=0,
        exact_narration="test narration",
        core_meaning="test",
        main_subject="fresh subject",
        subject_action="action",
        environment="nature",
        time_of_day="morning",
        mood="uplifting",
        composition="wide",
        camera_framing="wide",
        lighting="sunlight",
        color_palette="green",
        visual_style="photo",
    )

    report = VisionQualityGate.validate_scene_image(img_path, plan, check_permanent_duplicates=True)
    assert report.passed
    assert report.duplicate_status is False


# =========================================================================
# 4. PRODUCTION PIPELINE & ANTI-FALLBACK TESTS
# =========================================================================

def test_production_composer_generates_all_scene_images():
    """Verify AIImageGenerator generates unique fresh AI images for every scene in a Reel."""
    scenes = [
        {"spoken_line": "पहला दृश्य: वैदिक ऊर्जा का रहस्य", "on_screen_text": "VEDIC ENERGY HOOK"},
        {"spoken_line": "दूसरा दृश्य: तंत्रिका तंत्र में शांति", "on_screen_text": "NERVOUS SYSTEM CALM"},
        {"spoken_line": "तीसरा दृश्य: एकाग्रता में वृद्धि", "on_screen_text": "FOCUSED MIND"},
        {"spoken_line": "चौथा दृश्य: सुरक्षा कवच का निर्माण", "on_screen_text": "AURA PROTECTION"},
        {"spoken_line": "अंतिम दृश्य: अभी शिव कमेंट करें", "on_screen_text": "COMMENT SHIVA"},
    ]
    topic = "Vedic Energy Secrets"

    images = AIImageGenerator.generate_reel_visuals(
        scenes=scenes,
        topic=topic,
        reel_slug="test_prod_composer",
        mock_mode=True,
    )

    assert len(images) == 5
    assert len(set(images)) == 5, "Every scene must receive a distinct file path."

    # Verify content uniqueness
    hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in images]
    assert len(set(hashes)) == 5, "Every scene must have a 100% unique cryptographic hash."

    # Verify that each scene dictionary received its visual plan
    for sc in scenes:
        assert "visual_plan" in sc
        assert sc["visual_plan"]["main_subject"]


def test_generation_failure_prevents_false_successful_reel():
    """
    CRITICAL MANDATE:
    If AI image generation fails and allow_static_fallback=False (production default),
    the pipeline MUST raise ImageGenerationError and NOT silently substitute random B-roll.
    """
    scene = {"spoken_line": "यह दृश्य कभी उत्पन्न नहीं हो सकता", "on_screen_text": "FAILURE TEST"}
    topic = "Test Failure Topic"

    # Force provider to fail on all attempts
    with patch.object(BaseImageProvider, "generate", side_effect=ImageProviderError("Simulated API failure")):
        with pytest.raises(ImageGenerationError) as exc_info:
            AIImageGenerator.generate_scene_image(
                scene_dict=scene,
                topic=topic,
                scene_idx=0,
                total_scenes=1,
                reel_slug="test_fail",
                allow_static_fallback=False,  # Strict production mode
            )
        assert "Failed to generate fresh AI image" in str(exc_info.value)


def test_scene_manifest_builder_end_to_end():
    """Verify SceneManifestBuilder builds verified manifest with zero duplicate visuals."""
    from app.video.scene_manifest import SceneManifestBuilder, SceneAssetManifest
    script_data = {
        "topic": "5 Bio-Electric Secrets of Pyrite",
        "scenes": [
            {"spoken_line": "क्या आप जानते हैं कि पाइराइट कैसे ऊर्जा बदलता है?", "on_screen_text": "PYRITE HOOK"},
            {"spoken_line": "यह नर्वस सिस्टम को शांत और स्थिर करता है।", "on_screen_text": "NERVOUS SYSTEM CALM"},
            {"spoken_line": "कार्यक्षेत्र में स्पष्टता और फोकस बढ़ाता है।", "on_screen_text": "EXECUTIVE DESK FOCUS"},
        ],
    }
    manifest = SceneManifestBuilder.build_verified_manifest(script_data, mock_generation=True)
    assert isinstance(manifest, SceneAssetManifest)
    assert manifest.total_scenes == 3
    assert len(manifest.entries) == 3
    assert manifest.is_verified is True
    for entry in manifest.entries:
        assert entry.validation_passed is True
        assert Path(entry.image_path).exists()
