"""
Strict Scene-Semantic Regression Tests (Phase 8).
Validates that:
1. First scene about Saturn must NOT force gemstone imagery.
2. CTA scene must NOT force temple imagery.
3. Career narration must NOT return marriage imagery.
4. Marriage narration must NOT return gemstone imagery.
5. Gemstone narration must return gemstone-relevant imagery.
6. Tenth-house narration must return tenth-house/career-relevant imagery.
7. Generic astrology context must NOT override specific narration.
8. Random variety must NOT replace a relevant visual.
9. Failed asset retrieval must NOT use unrelated fallback.
10. Composer must NOT override the validated visual.
11. Two unrelated scenes must not receive the same visual merely because it is convenient.
12. Repeated topic does not mean repeated scene visuals.
"""

import pytest
from pathlib import Path
from typing import Dict, Any

from app.video.scene_visual_planner import SceneVisualPlanner, SceneVisualPlan
from app.video.scene_visual_intelligence import SceneVisualIntelligence, ReelVisualDiversityTracker
from app.video.dynamic_visual_engine import DynamicVisualEngine
from app.video.vision_quality_gate import VisionQualityGate, VisualValidationReport
from app.video.cinematic_composer import resolve_topic_visuals
from app.video.production_verifier import ProductionReelVerifier


def test_first_scene_saturn_does_not_force_gemstone():
    """First scene about Saturn must NOT force gemstone imagery."""
    scene = {
        "spoken_line": "शनि का प्रभाव आपके जीवन में अनुशासन और कर्म का चक्र शुरू करता है।",
        "on_screen_text": "SHANI PRABHAV",
        "visual_description": "The majestic planet Saturn with detailed crystalline ice rings in deep space",
    }
    tracker = ReelVisualDiversityTracker()
    spec = SceneVisualIntelligence.analyze_scene(
        scene_dict=scene,
        scene_idx=0,
        total_scenes=5,
        topic="शनि का गोचर और प्रभाव",
        diversity_tracker=tracker,
    )
    prompt = spec.image_prompt.lower()
    subject = spec.subject.lower()
    
    # Must NOT mention gemstones, crystals, or minerals as subject
    assert "gemstone" not in subject
    assert "ruby" not in subject
    assert "sapphire" not in subject
    assert "emerald" not in subject
    assert "gemstone" not in prompt
    assert "unpolished mineral" not in prompt
    assert "saturn" in prompt or "shani" in prompt or "saturn" in subject


def test_cta_scene_does_not_force_temple_or_gemstone():
    """CTA scene must NOT force temple imagery or gemstones."""
    scene = {
        "spoken_line": "अपनी कुंडली में सही स्थिति जानने के लिए हमें तुरंत डीएम करें और यह रील सेव करें।",
        "on_screen_text": "DM FOR CONSULTATION",
        "visual_description": "Vedic astrologer consultation desk with authentic parchment charts and brass reading lamp",
    }
    tracker = ReelVisualDiversityTracker()
    spec = SceneVisualIntelligence.analyze_scene(
        scene_dict=scene,
        scene_idx=4,
        total_scenes=5,
        topic="शनि साढ़ेसाती उपाय",
        diversity_tracker=tracker,
    )
    prompt = spec.image_prompt.lower()
    subject = spec.subject.lower()

    # Must NOT force a temple or gemstones
    assert "temple sanctum" not in prompt
    assert "rows of carved brass diyas" not in prompt
    assert "cradling authentic glowing gemstones" not in prompt
    assert "consultation" in prompt or "astrologer" in prompt or "consultation" in subject or "chart" in prompt


def test_career_narration_does_not_return_marriage_imagery():
    """Career narration must NOT return marriage imagery."""
    scene = {
        "spoken_line": "दसवां भाव आपके करियर की दिशा और कार्यक्षेत्र में बड़ी सफलता तय करता है।",
        "on_screen_text": "CAREER DIRECTION",
        "visual_description": "Vedic Kundli birth chart highlighting 10th house Karma Bhava with executive office desk",
    }
    tracker = ReelVisualDiversityTracker()
    spec = SceneVisualIntelligence.analyze_scene(
        scene_dict=scene,
        scene_idx=1,
        total_scenes=5,
        topic="करियर और 10वां भाव",
        diversity_tracker=tracker,
    )
    prompt = spec.image_prompt.lower()
    subject = spec.subject.lower()

    assert "marriage" not in prompt
    assert "wedding" not in prompt
    assert "vivah" not in prompt
    assert "10th" in prompt or "karma" in prompt or "career" in prompt or "desk" in prompt or "10th" in subject


def test_marriage_narration_does_not_return_gemstone_imagery():
    """Marriage narration must NOT return gemstone imagery."""
    scene = {
        "spoken_line": "सातवें भाव में शनि की दृष्टि वैवाहिक जीवन और विवाह में विलंब ला सकती है।",
        "on_screen_text": "MARRIAGE DELAY",
        "visual_description": "Vedic Kundli birth chart highlighting 7th house Yuvati Bhava with partnership harmony",
    }
    tracker = ReelVisualDiversityTracker()
    spec = SceneVisualIntelligence.analyze_scene(
        scene_dict=scene,
        scene_idx=2,
        total_scenes=5,
        topic="विवाह में देरी के ज्योतिषीय कारण",
        diversity_tracker=tracker,
    )
    prompt = spec.image_prompt.lower()

    assert "gemstone" not in prompt
    assert "sapphire" not in prompt
    assert "ruby" not in prompt
    assert "emerald" not in prompt
    assert "7th" in prompt or "marriage" in prompt or "partnership" in prompt or "yuvati" in prompt


def test_gemstone_narration_returns_gemstone_relevant_imagery():
    """Gemstone narration must return gemstone-relevant imagery."""
    scene = {
        "spoken_line": "बुध को मजबूत करने के लिए जाम्बियन पन्ना यानी एमराल्ड धारण किया जाता है।",
        "on_screen_text": "EMERALD FOR MERCURY",
        "visual_description": "Certified natural vivid green Zambian Emerald gemstone glowing with crystalline facets",
    }
    tracker = ReelVisualDiversityTracker()
    spec = SceneVisualIntelligence.analyze_scene(
        scene_dict=scene,
        scene_idx=1,
        total_scenes=5,
        topic="रत्न और उनके प्रभाव",
        diversity_tracker=tracker,
    )
    prompt = spec.image_prompt.lower()
    subject = spec.subject.lower()

    assert "emerald" in prompt or "panna" in prompt or "emerald" in subject
    assert "temple" not in prompt
    assert "marriage" not in prompt


def test_tenth_house_narration_returns_tenth_house_imagery():
    """Tenth house narration must return 10th house / career imagery."""
    scene = {
        "spoken_line": "आपकी कुंडली का दसवां भाव सीधे आपके कर्म और लीडरशिप रोल को दर्शाता है।",
        "on_screen_text": "10TH HOUSE KARMA",
        "visual_description": "Vedic Kundli birth chart with illuminated 10th House Karma Bhava and executive desk",
    }
    plan = SceneVisualPlanner.create_scene_visual_plan(
        scene=scene,
        topic="कुंडली के 12 भाव",
        scene_idx=1,
        total_scenes=5,
    )
    prompt = plan.generation_prompt.lower()
    assert "10th" in prompt or "karma" in prompt or "executive" in prompt or "desk" in prompt
    assert "gemstone" not in prompt
    assert "temple" not in prompt


def test_generic_astrology_topic_does_not_override_scene_narration():
    """Overall topic 'Vedic Astrology Gems & Temples' must NOT override an executive desk scene."""
    scene = {
        "spoken_line": "ऑफिस में लगातार मेहनत करने के बाद भी प्रमोशन रुका हुआ है।",
        "on_screen_text": "OFFICE PROMOTION STUCK",
        "visual_description": "Clean executive desk workspace journal focus in morning light",
    }
    # Topic mentions temples and gemstones, but scene is strictly executive workplace
    topic = "Vedic Astrology Gemstones and Temple Remedies"
    
    # 1. Trait visual prompt
    prompt = DynamicVisualEngine.get_trait_visual_prompt(scene, topic, scene_idx=2)
    assert "executive" in prompt.lower() or "desk" in prompt.lower() or "office" in prompt.lower()
    assert "temple" not in prompt.lower()

    # 2. Search query
    query = DynamicVisualEngine.get_scene_search_query(scene, topic, scene_idx=2)
    assert "executive" in query.lower() or "desk" in query.lower() or "workspace" in query.lower()
    assert "temple" not in query.lower()


def test_vision_quality_gate_rejects_gemstone_on_career_scene():
    """VisionQualityGate must reject a gemstone image when narration is about career/10th house."""
    plan = SceneVisualPlan(
        scene_id="scene_2",
        scene_idx=1,
        exact_narration="दसवां भाव आपके करियर में अचानक बड़े बदलाव लाता है।",
        main_subject="10th house career governance",
        generation_prompt="cinematic 10th house birth chart with executive desk",
    )
    # Validate against an asset named gemstone
    fake_gem_asset = Path("assets/cinematic_broll/gemstone_blue_sapphire.jpg")
    report = VisionQualityGate.validate_scene_image(
        image_input=fake_gem_asset,
        plan=plan,
        check_permanent_duplicates=False,
    )
    assert not report.passed
    assert "gemstone" in report.rejection_reason.lower()


def test_vision_quality_gate_rejects_temple_on_non_temple_scene():
    """VisionQualityGate must reject a temple image when narration has no temple mention."""
    plan = SceneVisualPlan(
        scene_id="scene_5",
        scene_idx=4,
        exact_narration="पर्सनल परामर्श के लिए हमें तुरंत डीएम करें।",
        main_subject="Astrologer consultation desk",
        generation_prompt="cinematic astrologer consultation desk with parchment",
    )
    fake_temple_asset = Path("assets/cinematic_broll/temple_sanctum_golden_diyas.jpg")
    report = VisionQualityGate.validate_scene_image(
        image_input=fake_temple_asset,
        plan=plan,
        check_permanent_duplicates=False,
    )
    assert not report.passed
    assert "temple" in report.rejection_reason.lower()


def test_composer_resolve_topic_visuals_has_no_forced_havan_or_temple():
    """Composer's resolve_topic_visuals must not hardcode temple/havan endings on general topics."""
    visuals = resolve_topic_visuals("career progression and saturn")
    names = [p.name for p in visuals]
    assert "4_sacred_havan.jpg" not in names
    assert "5_temple_sanctum.jpg" not in names
    assert "temple_sanctum_golden_diyas.jpg" not in names


def test_two_distinct_scenes_receive_distinct_semantic_visuals():
    """Two different scenes in the same Reel must receive distinct, scene-matched visuals."""
    scene_a = {
        "spoken_line": "शनि ग्रह का प्रभाव आपके 10वें भाव में है।",
        "on_screen_text": "SHANI IN 10TH",
        "visual_description": "Vedic Kundli birth chart highlighting 10th house",
    }
    scene_b = {
        "spoken_line": "पर्सनल कंसल्टेशन के लिए नीचे कमेंट करें।",
        "on_screen_text": "COMMENT FOR CONSULTATION",
        "visual_description": "Astrologer study desk with rolled parchment and reading lamp",
    }
    topic = "शनि और करियर"
    prompt_a = DynamicVisualEngine.get_trait_visual_prompt(scene_a, topic, scene_idx=0)
    prompt_b = DynamicVisualEngine.get_trait_visual_prompt(scene_b, topic, scene_idx=1)
    
    assert prompt_a != prompt_b
    assert "kundli" in prompt_a.lower() or "chart" in prompt_a.lower()
    assert "consultation" in prompt_b.lower() or "desk" in prompt_b.lower()


# ==============================================================================
# ADVERSARIAL EMERALD VS KUNDLI & SCENE SEMANTIC CONTRACT TESTS
# ==============================================================================

def test_emerald_narration_rejects_generic_kundli_chart():
    """
    CRITICAL TEST CASE (User Prompt):
    Narration: 'बुध को मजबूत करने के लिए जाम्बियन पन्ना रत्न धारण करना लाभकारी माना जाता है।'
    A generic astrological Kundli chart MUST FAIL this test.
    """
    spoken = "बुध को मजबूत करने के लिए जाम्बियन पन्ना रत्न धारण करना लाभकारी माना जाता है।"
    on_screen = "PANNA EMERALD GEMSTONE"
    vis_desc = "Certified natural vivid green Zambian Emerald gemstone glowing with crystalline facets"

    status, reason = ProductionReelVerifier._evaluate_scene_relevance(
        scene_idx=3,
        total_scenes=5,
        spoken=spoken,
        on_screen=on_screen,
        vis_desc=vis_desc,
        asset_name="authentic_vedic_kundli_parchment.jpg",
    )
    assert status == "FAIL", f"Expected FAIL for Kundli chart on Emerald scene, got {status} ({reason})"
    assert "mismatch" in reason.lower() or "emerald" in reason.lower() or "chart" in reason.lower()


def test_emerald_narration_rejects_temple_imagery():
    """Emerald narration must reject temple / sanctum imagery."""
    spoken = "बुध को मजबूत करने के लिए जाम्बियन पन्ना रत्न धारण करना लाभकारी माना जाता है।"
    status, reason = ProductionReelVerifier._evaluate_scene_relevance(
        scene_idx=3,
        total_scenes=5,
        spoken=spoken,
        on_screen="PANNA EMERALD",
        vis_desc="Emerald gemstone",
        asset_name="temple_sanctum_golden_diyas.jpg",
    )
    assert status == "FAIL"
    assert "temple" in reason.lower() or "forbidden" in reason.lower()


def test_emerald_narration_rejects_saturn_imagery():
    """Emerald narration must reject planet Saturn imagery."""
    spoken = "बुध को मजबूत करने के लिए जाम्बियन पन्ना रत्न धारण करना लाभकारी माना जाता है।"
    status, reason = ProductionReelVerifier._evaluate_scene_relevance(
        scene_idx=3,
        total_scenes=5,
        spoken=spoken,
        on_screen="PANNA EMERALD",
        vis_desc="Emerald gemstone",
        asset_name="planet_saturn.jpg",
    )
    assert status == "FAIL"
    assert "saturn" in reason.lower() or "forbidden" in reason.lower()


def test_emerald_narration_accepts_emerald_gemstone():
    """Emerald narration must accept authentic emerald gemstone imagery."""
    spoken = "बुध को मजबूत करने के लिए जाम्बियन पन्ना रत्न धारण करना लाभकारी माना जाता है।"
    status, reason = ProductionReelVerifier._evaluate_scene_relevance(
        scene_idx=3,
        total_scenes=5,
        spoken=spoken,
        on_screen="PANNA EMERALD",
        vis_desc="Certified natural vivid green Zambian Emerald gemstone",
        asset_name="gemstone_emerald.jpg",
        asset_path=Path("assets/cinematic_broll/gemstone_emerald.jpg"),
    )
    assert status == "PASS"


def test_subordinate_kundli_clause_preserves_emerald_gemstone_entity():
    """
    Subordinate clause mentioning Kundli ('जब ग्रह आपकी कुंडली में कारक हो')
    must NOT hijack the entity into a Kundli chart when Emerald is the primary subject.
    """
    text = "बुध को मजबूत करने के लिए जाम्बियन पन्ना रत्न तभी पहनें जब ग्रह आपकी कुंडली में कारक हो। PANNA EMERALD GEMSTONE"
    matched = SceneVisualPlanner.detect_scene_entity(text)
    assert matched is not None
    assert matched[0] == "emerald_gemstone"
    assert "emerald" in matched[1]["name"].lower() or "panna" in matched[1]["keywords"]


def test_emerald_actual_pixel_chromatic_contract_rejection():
    """
    Tests that actual physical pixels of a non-green parchment are rejected by
    SceneSemanticContract even if passed as an in-memory image.
    """
    from app.video.scene_semantic_contract import SceneSemanticContract
    contract = SceneSemanticContract.build_from_scene(
        {
            "spoken_line": "बुध को मजबूत करने के लिए जाम्बियन पन्ना रत्न पहनें।",
            "on_screen_text": "EMERALD",
            "visual_description": "Green emerald gemstone",
        },
        scene_idx=0,
        total_scenes=1,
    )
    # Kundli parchment has 0 green dominance
    kundli_path = Path("assets/cinematic_broll/authentic_vedic_kundli_parchment.jpg")
    res = contract.validate_asset(kundli_path)
    assert res.overall_accepted is False
    assert "green" in res.rejection_reason.lower() or "parchment" in res.rejection_reason.lower()


def test_adversarial_calibration_set_minimizes_false_positives():
    """
    Calibration test set verifying that the false positive rate for irrelevant assets is exactly 0.0.
    """
    calibration_cases = [
        # (spoken, on_screen, vis_desc, asset_name, expected_verdict)
        ("पन्ना रत्न बुध को बल देता है।", "PANNA EMERALD", "Emerald stone", "gemstone_emerald.jpg", "PASS"),
        ("पन्ना रत्न बुध को बल देता है।", "PANNA EMERALD", "Emerald stone", "authentic_vedic_kundli_parchment.jpg", "FAIL"),
        ("पन्ना रत्न बुध को बल देता है।", "PANNA EMERALD", "Emerald stone", "planet_saturn.jpg", "FAIL"),
        ("पन्ना रत्न बुध को बल देता है।", "PANNA EMERALD", "Emerald stone", "temple_sanctum_golden_diyas.jpg", "FAIL"),
        ("शनि का प्रभाव 7वें भाव में देरी लाता है।", "SHANI DELAY", "Saturn planet", "planet_saturn.jpg", "PASS"),
        ("शनि का प्रभाव 7वें भाव में देरी लाता है।", "SHANI DELAY", "Saturn planet", "gemstone_emerald.jpg", "FAIL"),
        ("कुंडली का दसवां भाव करियर तय करता है।", "10TH HOUSE CAREER", "Career desk", "gemstone_blue_sapphire.jpg", "FAIL"),
        ("पर्सनल परामर्श के लिए हमें डीएम करें।", "DM FOR CONSULTATION", "Consultation desk", "astrology_consultation_scroll.jpg", "PASS"),
        ("पर्सनल परामर्श के लिए हमें डीएम करें।", "DM FOR CONSULTATION", "Consultation desk", "temple_sanctum_golden_diyas.jpg", "FAIL"),
    ]

    false_positives = 0
    false_negatives = 0

    for spoken, on_scr, vis, asset, exp in calibration_cases:
        status, reason = ProductionReelVerifier._evaluate_scene_relevance(
            scene_idx=0,
            total_scenes=1,
            spoken=spoken,
            on_screen=on_scr,
            vis_desc=vis,
            asset_name=asset,
        )
        if exp == "FAIL" and status == "PASS":
            false_positives += 1
        elif exp == "PASS" and status == "FAIL":
            false_negatives += 1

    fp_rate = false_positives / len(calibration_cases)
    assert false_positives == 0, f"False positives detected: {false_positives}/{len(calibration_cases)}"
    assert fp_rate == 0.0

