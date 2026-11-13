"""
Tests for Anti-Repetition Mandates:
1. Verifies that 'पैंतालीस लाख' (45 lakhs) and repetitive numerical losses are stripped.
2. Verifies that static assets (neelam_sc*, pukhraj_sc*, etc.) are permanently banned.
3. Verifies Sarvam AI speech pace defaults to 1.20x.
"""

import os
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.script_agent import sanitize_script_dialogue
from app.video.dynamic_visual_engine import DynamicVisualEngine, BANNED_IMAGE_NAMES
from config.settings import SARVAM_PACE


def test_sarvam_pace_is_1_20():
    assert SARVAM_PACE == 1.20


def test_sanitize_strips_45_lakhs_and_numerical_loss():
    raw_scenes = [
        {
            "spoken_line": "पैंतालीस लाख का भारी नुकसान हुआ हमारे क्लाइंट को जब उन्होंने नीलम पहना।",
            "on_screen_text": "45 LAKHS LOST FROM NEELAM",
            "scene_number": 1,
            "badge": "WARNING",
        },
        {
            "spoken_line": "पहला मुख्य संकेत: 45 लाख का नुकसान होने से पहले व्यापार में अचानक गिरावट आई।",
            "on_screen_text": "1. 45 LAKH LOSS",
            "scene_number": 2,
            "badge": "SIGN 1 OF 3",
        },
    ]

    sanitized = sanitize_script_dialogue(raw_scenes, topic="Blue Sapphire Caution")
    for sc in sanitized:
        assert "पैंतालीस लाख" not in sc["spoken_line"]
        assert "45 LAKHS" not in sc["on_screen_text"]
        assert "45 LAKH" not in sc["on_screen_text"]


def test_banned_static_assets_never_reused():
    legacy_candidates = [
        Path("neelam_sc1_gemstone_1794486992845.jpg"),
        Path("neelam_sc2_career_crash.jpg"),
        Path("pukhraj_sc1_gemstone.jpg"),
        Path("pukhraj_sc4_kundli.jpg"),
        Path("gemstone_blue_sapphire.jpg"),
        Path("gemstone_yellow_sapphire.jpg"),
        Path("temple_sanctum_golden_diyas.jpg"),
    ]

    for cand in legacy_candidates:
        assert DynamicVisualEngine.is_image_used(cand) is True, f"Asset {cand} should be banned from reuse"
