"""
Comprehensive Test Suite for Chunk 4: Script Intelligence & Scene Planning.

Covers:
1. Script structure and metadata completeness
2. Hook generation, scoring, and sanitization
3. Scene segmentation based on sentence boundaries
4. Accurate spoken duration calculations (Hindi & English)
5. Strict topic context isolation (zero topic contamination)
6. Scene relevance-aware entity resolution
7. Duplicate scene detection and angle diversification
8. Visual brief completeness and structured specification
9. Automatic validation and repair of invalid/generic scenes
10. Empty output and malformed AI response handling
11. Claim safety (medical & financial claim sanitization)
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.agents.script_agent import (
    calculate_spoken_duration,
    segment_narration_into_scenes,
    sanitize_script_dialogue,
    generate_hooks,
    score_hooks,
    generate_reel,
)
from app.video.scene_visual_planner import (
    SceneVisualPlan,
    SceneVisualPlanner,
    SceneValidationError,
)


# =============================================================================
# 1. DURATION CALCULATION & TIMING PRECISION
# =============================================================================
def test_calculate_spoken_duration_hindi():
    """Proves Hindi spoken duration accurately accounts for words and punctuation pauses."""
    short_line = "यह पहला मुख्य रहस्य है।"
    duration = calculate_spoken_duration(short_line, language="hindi")
    assert 2.5 <= duration <= 4.0

    longer_line = (
        "जब हमारे एक क्लाइंट ने अपनी जन्मपत्रिका का विश्लेषण करवाया, "
        "तो उनके दशम भाव में शनि और मंगल की युति स्पष्ट दिखाई दी।"
    )
    long_duration = calculate_spoken_duration(longer_line, language="hindi")
    assert 4.5 <= long_duration <= 6.5


def test_calculate_spoken_duration_english():
    """Proves English duration calculations adhere to realistic short-form WPM."""
    english_line = "Stop wearing Pyrite blindly before checking your birth chart."
    duration = calculate_spoken_duration(english_line, language="english")
    assert 2.5 <= duration <= 5.0


def test_duration_clamps_boundaries():
    """Proves durations never fall below 2.5s and never exceed 6.5s."""
    tiny = "हां।"
    assert calculate_spoken_duration(tiny) == 2.5

    massive = "शब्द " * 50
    assert calculate_spoken_duration(massive) == 6.5


# =============================================================================
# 2. SCENE SEGMENTATION
# =============================================================================
def test_segment_narration_into_scenes():
    """Proves narration divides on natural sentence boundaries without midpoint cuts."""
    narration = (
        "दस साल की अथक मेहनत के बाद भी करियर में रुकावटें क्यों आ रही थीं? "
        "जब कुंडली जांची गई, तो पंचम भाव में राहु का प्रभाव मिला। "
        "यह ऊर्जा मानसिक भटकाव और अनिद्रा को जन्म देती है। "
        "अपनी कुंडली की स्थिति नीचे कमेंट करें और विस्तृत विश्लेषण के लिए डीएम करें।"
    )
    scenes = segment_narration_into_scenes(narration, language="hindi")

    assert len(scenes) >= 3
    for sc in scenes:
        assert "spoken_line" in sc
        assert "estimated_seconds" in sc
        assert 2.5 <= sc["estimated_seconds"] <= 6.5
        # Must not end with broken words
        assert not sc["spoken_line"].endswith("के")
        assert not sc["spoken_line"].endswith("और")


def test_segment_narration_empty_handling():
    """Proves empty narration returns empty list safely."""
    assert segment_narration_into_scenes("") == []
    assert segment_narration_into_scenes("   ") == []


# =============================================================================
# 3. TOPIC CONTAMINATION PREVENTION (TASK 4)
# =============================================================================
def test_topic_contamination_prevention_rudraksha_vs_nervous_system():
    """
    CRITICAL SPECIFICATION TEST:
    Topic: 'Sacred Rudraksha Energy and Bio-Electric Secrets'
    Scene narration: 'यह ऊर्जा सीधे आपके तंत्रिका तंत्र (nervous system) और मस्तिष्क को शांत करती है।'
    
    ASSERTIONS:
    - The scene visual subject MUST be the human nervous system / brain synapses.
    - The scene visual subject MUST NOT be a Rudraksha bead.
    - 'rudraksha bead' MUST be explicitly listed in forbidden_visual_elements.
    """
    topic = "Sacred Rudraksha Energy and Bio-Electric Secrets"
    scene = {
        "spoken_line": "यह ऊर्जा सीधे आपके तंत्रिका तंत्र और मस्तिष्क को शांत करती है।",
        "on_screen_text": "CALMS NERVOUS SYSTEM",
        "visual_description": "human brain synapses and glowing neural pathways",
        "estimated_seconds": 4.0,
    }

    plan = SceneVisualPlanner.plan_scene_visual(
        scene_dict=scene,
        scene_idx=1,
        total_scenes=5,
        topic=topic,
    )

    assert plan.entity_key == "nervous_system"
    assert "nervous system" in plan.main_subject or "neural" in plan.main_subject
    assert "rudraksha" not in plan.main_subject.lower()

    # Rudraksha must be strictly forbidden in this scene to prevent model hallucination
    forbidden_lower = [f.lower() for f in plan.forbidden_visual_elements]
    assert any("rudraksha" in f for f in forbidden_lower)


def test_topic_contamination_prevention_saturn_vs_copper_water():
    """
    Topic: 'Shani Sade Sati Transit'
    Scene: 'प्रातःकाल तांबे के लोटे से पवित्र जल ग्रहण करने का नियम।'
    
    ASSERTIONS:
    - Primary subject MUST be copper water vessel.
    - Saturn planet MUST NOT be primary subject.
    - Saturn MUST be listed in forbidden elements.
    """
    topic = "Shani Sade Sati Transit and Karmic Lessons"
    scene = {
        "spoken_line": "प्रातःकाल तांबे के लोटे से जल ग्रहण करने का नियम समझें।",
        "on_screen_text": "COPPER WATER REMEDY",
        "visual_description": "",
    }

    plan = SceneVisualPlanner.plan_scene_visual(
        scene_dict=scene,
        scene_idx=2,
        total_scenes=6,
        topic=topic,
    )

    assert plan.entity_key == "copper_water_remedy"
    assert "copper" in plan.main_subject.lower()
    assert "saturn" not in plan.main_subject.lower()

    forbidden_lower = [f.lower() for f in plan.forbidden_visual_elements]
    assert any("saturn" in f for f in forbidden_lower)


# =============================================================================
# 4. STRUCTURED VISUAL BRIEF COMPLETENESS (TASK 3)
# =============================================================================
def test_scene_visual_brief_fields_completeness():
    """Proves SceneVisualPlan populates all required metadata fields with cinematic standards."""
    scene = {
        "spoken_line": "कुंडली के दशम भाव में शनि और मंगल की युति करियर में अचानक गतिरोध पैदा करती है।",
        "on_screen_text": "10TH HOUSE OBSTACLES",
        "visual_description": "",
    }

    plan = SceneVisualPlanner.plan_scene_visual(scene, scene_idx=0, total_scenes=5, topic="Astrology Case Study")

    assert plan.scene_id == "scene_1"
    assert plan.scene_idx == 0
    assert plan.aspect_ratio == "9:16"
    assert plan.main_subject
    assert plan.subject_action
    assert plan.environment
    assert plan.lighting
    assert plan.composition
    assert plan.color_palette
    assert plan.visual_style
    assert len(plan.required_visual_elements) >= 1
    assert len(plan.forbidden_visual_elements) >= 3
    assert plan.generation_prompt
    assert "cinematic photorealistic 9:16 vertical" in plan.generation_prompt


# =============================================================================
# 5. VALIDATION & REPAIR OF INVALID SCENES (TASK 5)
# =============================================================================
def test_repair_empty_or_generic_scene_plan():
    """Proves SceneVisualPlanner repairs empty or generic visual descriptions."""
    invalid_plan = SceneVisualPlan(
        scene_id="scene_bad",
        scene_idx=0,
        exact_narration="Some vague words",
        core_meaning="",
        main_subject="placeholder",  # Generic placeholder
        subject_action="",
        environment="",
        time_of_day="midnight",
        mood="",
        composition="",
        camera_framing="",
        lighting="bright daylight",  # Contradictory to midnight
        color_palette="",
        visual_style="",
    )

    repaired = SceneVisualPlanner.validate_and_repair_plan(invalid_plan)

    assert repaired.is_valid is True
    assert repaired.main_subject != "placeholder"
    assert "bright daylight" not in repaired.lighting.lower()
    assert repaired.composition
    assert repaired.generation_prompt


# =============================================================================
# 6. DUPLICATE SCENE DETECTION & DIVERSIFICATION
# =============================================================================
def test_deduplicate_reel_plans_diversifies_angles():
    """Proves consecutive scenes with same subject receive diversified camera angles and lighting."""
    scenes = [
        {"spoken_line": "प्राकृतिक पायराइट क्रिस्टल...", "on_screen_text": "PYRITE 1"},
        {"spoken_line": "पायराइट की सूर्य ऊर्जा...", "on_screen_text": "PYRITE 2"},
        {"spoken_line": "पायराइट का तीसरा रहस्य...", "on_screen_text": "PYRITE 3"},
    ]

    plans = SceneVisualPlanner.plan_reel_visuals(scenes, topic="Pyrite Energy")

    assert len(plans) == 3
    assert plans[0].entity_key == "pyrite_crystal"
    assert plans[1].entity_key == "pyrite_crystal"

    # Second occurrence must have diversified framing
    assert "overhead top-down" in plans[1].composition or "overhead" in plans[1].generation_prompt
    # Third occurrence must have macro framing
    assert "macro" in plans[2].composition or "macro" in plans[2].generation_prompt


# =============================================================================
# 7. CLAIM SAFETY & SANITIZATION (TASK 1)
# =============================================================================
def test_sanitize_script_dialogue_removes_medical_and_financial_claims():
    """Proves medical cure claims and guaranteed wealth claims are sanitized."""
    scenes = [
        {
            "spoken_line": "यह चमत्कारी रत्न आपकी बीमारी ठीक करता है और आपको रातोंरात अमीर बना देगा।",
            "on_screen_text": "100% CURES ILLNESS",
        }
    ]

    sanitized = sanitize_script_dialogue(scenes, topic="Gemstone Wisdom")
    line = sanitized[0]["spoken_line"]

    assert "बीमारी ठीक करता है" not in line
    assert "रातोंरात अमीर" not in line
    assert "शांति" in line or "अनुशासन" in line


# =============================================================================
# 8. HOOK GENERATION & SCORING
# =============================================================================
@patch("app.agents.script_agent.generate_json")
def test_generate_and_score_hooks(mock_generate_json):
    """Proves hooks are generated, parsed, scored, and returned cleanly."""
    mock_generate_json.return_value = {
        "hooks": [
            {
                "id": "1",
                "name": "Case Study",
                "spoken": "दस साल की मेहनत के बाद भी प्रमोशन क्यों रुका?",
                "on_screen": "CAREER ROADBLOCK",
                "why_it_works": "Curiosity and empathy",
            },
            {
                "id": "2",
                "name": "Warning",
                "spoken": "बिना कुंडली जांचे कोई रत्न कभी न पहनें।",
                "on_screen": "AVOID BLIND STONES",
                "why_it_works": "Direct caution",
            },
            {
                "id": "3",
                "name": "House Secret",
                "spoken": "दशम भाव में शनि होने का असली अर्थ क्या है?",
                "on_screen": "10TH HOUSE SECRET",
                "why_it_works": "Astrological intrigue",
            },
        ]
    }

    hooks = generate_hooks("10th House Saturn", niche="astrology_vedic", language="Hindi")
    assert len(hooks) == 3

    scored = score_hooks(hooks)
    assert len(scored) == 3
    assert scored[0]["score"] >= scored[1]["score"] >= scored[2]["score"]


# =============================================================================
# 9. COMPLETE GENERATE_REEL INTEGRATION WITH MOCKED AI
# =============================================================================
@patch("app.agents.script_agent.generate_json")
def test_generate_reel_complete_flow_with_visual_plans(mock_generate_json):
    """Proves generate_reel completes end-to-end, attaching structured visual plans."""
    mock_generate_json.side_effect = [
        # Call 1: generate_hooks
        {
            "hooks": [
                {
                    "id": "hook_1",
                    "name": "Hook 1",
                    "spoken": "दस साल के करियर गतिरोध का असली ज्योतिषीय रहस्य क्या था?",
                    "on_screen": "TEN YEARS STAGNATION",
                    "why_it_works": "High intrigue",
                },
                {
                    "id": "hook_2",
                    "name": "Hook 2",
                    "spoken": "कार्यक्षेत्र में अचानक रुकावटें क्यों आती हैं?",
                    "on_screen": "CAREER ROADBLOCKS",
                    "why_it_works": "Pain point",
                },
                {
                    "id": "hook_3",
                    "name": "Hook 3",
                    "spoken": "दशम भाव की स्थिति कैसे समझें?",
                    "on_screen": "10TH HOUSE SECRET",
                    "why_it_works": "Curiosity",
                },
            ]
        },
        # Call 2: generate_reel full script
        {
            "title": "Career Breakthrough Secrets",
            "topic": "Career Stagnation 10th House",
            "visual_theme": "modern_dynamic",
            "scenes": [
                {
                    "scene_num": 1,
                    "spoken_line": "दस साल के करियर गतिरोध का असली ज्योतिषीय रहस्य क्या था?",
                    "on_screen_text": "TEN YEARS STAGNATION",
                    "badge": "CAREER SECRET",
                    "visual_description": "ancient Vedic parchment chart beside brass oil lamp",
                    "estimated_seconds": 3,
                },
                {
                    "scene_num": 2,
                    "spoken_line": "पहला मुख्य संकेत: तंत्रिका तंत्र पर तनाव और मानसिक दबाव का प्रभाव।",
                    "on_screen_text": "NERVOUS SYSTEM STRESS",
                    "badge": "CORE FACTOR",
                    "visual_description": "human brain synapses glowing with neural activity",
                    "estimated_seconds": 4,
                },
                {
                    "scene_num": 3,
                    "spoken_line": "दूसरा रहस्य: कार्यस्थल पर एकाग्रता और स्पष्ट निर्णय क्षमता।",
                    "on_screen_text": "EXECUTIVE CLARITY",
                    "badge": "FOCUS CODE",
                    "visual_description": "clean executive office desk with professional focus",
                    "estimated_seconds": 4,
                },
                {
                    "scene_num": 4,
                    "spoken_line": "यह रील सेव करें। अपनी ग्रह स्थिति कमेंट करें और परामर्श के लिए डीएम करें।",
                    "on_screen_text": "SAVE REEL • DM US",
                    "badge": "CHECK PLACEMENT",
                    "visual_description": "sacred glowing brass oil lamps in temple sanctum",
                    "estimated_seconds": 4,
                },
            ],
            "caption": "Decoded through 10th house karmic placement.",
            "hashtags": ["#VedicAstrology", "#CareerKarma", "#KundliAnalysis"],
            "call_to_action": "Save and DM us",
        },
    ]

    reel = generate_reel(
        topic="Career Stagnation 10th House",
        niche="astrology_vedic",
        language="Hindi",
        duration=20,
    )

    assert "scenes" in reel
    assert len(reel["scenes"]) == 4
    assert "visual_plans" in reel
    assert len(reel["visual_plans"]) == 4

    # Verify scene 2 (nervous system) is isolated from topic
    scene_2_plan = reel["visual_plans"][1]
    assert scene_2_plan["entity_key"] == "nervous_system"
    assert "nervous system" in scene_2_plan["main_subject"]
    assert "cinematic photorealistic 9:16 vertical" in scene_2_plan["generation_prompt"]
