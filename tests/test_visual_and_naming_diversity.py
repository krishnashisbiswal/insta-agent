import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.script_agent import resolve_entity_context
from app.video.dynamic_visual_engine import DynamicVisualEngine, BANNED_IMAGE_NAMES


def test_resolve_entity_context_chandra():
    ctx = resolve_entity_context("Moon (चन्द्र): Vedic Astrology Master Guide on Mind, Emotional Peace & Pearl Gemstone")
    assert ctx is not None
    assert ctx["type"] == "planet"
    assert ctx["name_en"] == "Moon"
    assert ctx["name_hi_dev"] == "चन्द्र देव"
    assert ctx["name_hi_alt"] == "चन्द्रमा"
    assert "सच्चा मोती" in ctx["gemstone_hi"]
    assert "चन्द्रमसे" in ctx["mantra"]


def test_resolve_entity_context_surya():
    ctx = resolve_entity_context("Sun (सूर्य): Vedic Astrology Master Guide on Soul & Authority")
    assert ctx is not None
    assert ctx["type"] == "planet"
    assert ctx["name_en"] == "Sun"
    assert ctx["name_hi_dev"] == "सूर्य देव"


def test_banned_static_assets():
    for banned in ["2_kundli_chart.jpg", "4_sacred_havan.jpg", "5_temple_sanctum.jpg"]:
        p = Path(f"assets/cinematic_broll/{banned}")
        assert DynamicVisualEngine.is_image_used(p) is True


import uuid

def test_dynamic_visual_registry_tracking(tmp_path):
    unique_name = f"test_asset_{uuid.uuid4().hex}.jpg"
    test_img = tmp_path / unique_name
    test_img.write_text("fake image data")

    # Before registration
    assert DynamicVisualEngine.is_image_used(test_img) is False

    # After registration
    DynamicVisualEngine.register_used_image(test_img)
    assert DynamicVisualEngine.is_image_used(test_img) is True
