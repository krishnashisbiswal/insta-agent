"""
Tests for Anti-Repetition Mandates:
1. Verifies that 'पैंतालीस लाख' (45 lakhs) and repetitive numerical losses are stripped.
2. Verifies that static assets (neelam_sc*, pukhraj_sc*, etc.) are permanently banned.
3. Verifies Sarvam AI speech pace defaults to 1.20x.
"""

import hashlib
import os
import sys
import uuid
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
        Path("1_gemstone_hook.jpg"),
        Path("2_kundli_chart.jpg"),
        Path("3_shani_saturn.jpg"),
        Path("4_sacred_havan.jpg"),
        Path("5_temple_sanctum.jpg"),
    ]

    for cand in legacy_candidates:
        assert DynamicVisualEngine.is_image_used(cand) is True, f"Asset {cand} should be banned from reuse"


def test_purge_old_generated_images():
    """Verify pre-generation purge deletes all temporary intermediate files."""
    test_file = PROJECT_ROOT / "assets" / "generated_broll" / "test_dummy_old_frame.jpg"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("test_old_bytes")
    assert test_file.exists()

    purged_count = DynamicVisualEngine.purge_old_generated_images()
    assert purged_count >= 1
    assert not test_file.exists(), "Old generated image should be purged before new video generation"


def test_zero_image_repetition_and_in_context_pyrite():
    """Verify 7-scene Pyrite reel produces 7 completely unique images with ZERO planetary/kundli mismatch."""
    topic = "5 scientific and spiritual energy shifts of Pyrite Crystal"
    scenes = [
        {"spoken_line": "क्या आप जानते हैं कि पाइराइट क्रिस्टल आपकी ऊर्जा को कैसे बदलता है?", "on_screen_text": "PYRITE CRYSTAL REVEALED"},
        {"spoken_line": "पहला लाभ: यह आपके नर्वस सिस्टम को शांति और गहरी स्थिरता प्रदान करता है।", "on_screen_text": "INSTANT NERVOUS STABILITY"},
        {"spoken_line": "दूसरा लाभ: कार्यस्थल पर यह एकाग्रता और समृद्धि की ऊर्जा आकर्षित करता है।", "on_screen_text": "EXECUTIVE DESK ABUNDANCE"},
        {"spoken_line": "तीसरा लाभ: यह आपके आभामंडल को नकारात्मक ऊर्जा से सुरक्षित रखता है।", "on_screen_text": "AURA PROTECTION SHIELD"},
        {"spoken_line": "चौथा लाभ: इसकी बायो-इलेक्ट्रिक फ्रीक्वेंसी शरीर में ऊर्जा का संतुलन बनाती है।", "on_screen_text": "BIO-ENERGY BALANCE"},
        {"spoken_line": "सावधानी: नकली पत्थरों के बजाय केवल प्राकृतिक लैब-प्रमाणित पाइराइट ही पहनें।", "on_screen_text": "AUTHENTICITY VERIFICATION"},
        {"spoken_line": "पूर्ण विवरण के लिए अभी 'पायराइट' कमेंट करें और अपनी ऊर्जा को सक्रिय करें।", "on_screen_text": "SAVE REEL • COMMENT PYRITE"},
    ]

    used_images = set()
    assigned = []
    for idx, sc in enumerate(scenes):
        img_p = DynamicVisualEngine.get_or_generate_scene_image(
            scene_dict=sc,
            topic=topic,
            scene_idx=idx,
            total_scenes=len(scenes),
            reel_slug="test_pyrite_anti_rep",
            used_images=used_images,
        )
        assigned.append(img_p)

    # 1. Strict Anti-Repetition Assertion
    assert len(assigned) == 7
    assert len(set(assigned)) == 7, f"Duplicates detected in assigned images: {[p.name for p in assigned]}"
    hashes = [hashlib.md5(p.read_bytes()).hexdigest() for p in assigned]
    assert len(set(hashes)) == 7, f"Duplicate content hashes detected across Pyrite scenes: {hashes}"

    # 2. Strict In-Context Assertion: Zero Saturn, Kundli parchment, or hardcoded havan/temple in Pyrite video
    for p in assigned:
        fname = p.name.lower()
        assert "planet_saturn" not in fname, f"Out-of-context Saturn visual found in Pyrite video: {fname}"
        assert "kundli_parchment" not in fname, f"Out-of-context Kundli chart found in Pyrite video: {fname}"
        assert "consultation_scroll" not in fname, f"Out-of-context Consultation scroll found in Pyrite video: {fname}"
        assert "sacred_havan" not in fname, f"Hardcoded repetitive havan altar found in Pyrite video: {fname}"
        assert "sacred_temple" not in fname, f"Hardcoded repetitive temple lamps found in Pyrite video: {fname}"


def test_zero_image_repetition_and_in_context_rudraksha():
    """Verify 7-scene 5 Mukhi Rudraksha reel produces 7 unique images with 100% relevant visuals."""
    topic = "5 bio-electric turning points of 5 Mukhi Rudraksha"
    scenes = [
        {"spoken_line": "नेपाली पंचमुखी रुद्राक्ष आपके शरीर और मन पर क्या चमत्कारी प्रभाव डालता है?", "on_screen_text": "5 MUKHI RUDRAKSHA"},
        {"spoken_line": "पहला बिंदु: यह मानसिक तनाव और चिंता को तुरंत शांत करता है।", "on_screen_text": "DEEP MENTAL PEACE"},
        {"spoken_line": "दूसरा बिंदु: हृदय गति और रक्तचाप के संतुलन में सहायक होता है।", "on_screen_text": "HEART & BLOOD PRESSURE"},
        {"spoken_line": "तीसरा बिंदु: ध्यान और एकाग्रता को कई गुना बढ़ा देता है।", "on_screen_text": "FOCUSED MEDITATION"},
        {"spoken_line": "चौथा बिंदु: यह सूक्ष्म आभामंडल को पवित्र ऊर्जा से भर देता है।", "on_screen_text": "SACRED AURA GLOW"},
        {"spoken_line": "सावधानी: नक्काशीदार नकली मोतियों के बजाय प्राकृतिक मुखी रेखाएं देखकर ही लें।", "on_screen_text": "NATURAL MUKHI GROOVES"},
        {"spoken_line": "अपने जीवन में सकारात्मक बदलाव के लिए अभी 'शिव' कमेंट करें।", "on_screen_text": "SAVE REEL • COMMENT SHIVA"},
    ]

    used_images = set()
    assigned = []
    for idx, sc in enumerate(scenes):
        img_p = DynamicVisualEngine.get_or_generate_scene_image(
            scene_dict=sc,
            topic=topic,
            scene_idx=idx,
            total_scenes=len(scenes),
            reel_slug="test_rudraksha_anti_rep",
            used_images=used_images,
        )
        assigned.append(img_p)

    # 1. Strict Anti-Repetition Assertion
    assert len(assigned) == 7
    assert len(set(assigned)) == 7, f"Duplicates detected in assigned images: {[p.name for p in assigned]}"
    hashes = [hashlib.md5(p.read_bytes()).hexdigest() for p in assigned]
    assert len(set(hashes)) == 7, f"Duplicate content hashes detected across Pyrite scenes: {hashes}"

    # 2. Strict In-Context Assertion: Zero out-of-context planetary or hardcoded assets
    for p in assigned:
        fname = p.name.lower()
        assert "planet_saturn" not in fname, f"Out-of-context Saturn visual found in Rudraksha video: {fname}"
        assert "planet_mars" not in fname, f"Out-of-context Mars visual found in Rudraksha video: {fname}"
        assert "sacred_havan" not in fname, f"Hardcoded repetitive havan altar found in Rudraksha video: {fname}"
        assert "sacred_temple" not in fname, f"Hardcoded repetitive temple lamps found in Rudraksha video: {fname}"


def test_no_repetition_of_last_two_images_across_consecutive_videos():
    """Verify that Scene 6 and Scene 7 do NOT repeat identical images across consecutive videos."""
    pyrite_scenes = [
        {"spoken_line": "पायराइट हुक", "on_screen_text": "PYRITE HOOK"},
        {"spoken_line": "पायराइट 1", "on_screen_text": "PYRITE 1"},
        {"spoken_line": "पायराइट 2", "on_screen_text": "PYRITE 2"},
        {"spoken_line": "पायराइट 3", "on_screen_text": "PYRITE 3"},
        {"spoken_line": "पायराइट 4", "on_screen_text": "PYRITE 4"},
        {"spoken_line": "सावधानी: बिना जांचे न लें", "on_screen_text": "CAUTION"},
        {"spoken_line": "अभी कमेंट करें", "on_screen_text": "COMMENT"},
    ]
    amethyst_scenes = [
        {"spoken_line": "कटेला जामुनिया हुक", "on_screen_text": "AMETHYST HOOK"},
        {"spoken_line": "कटेला 1", "on_screen_text": "AMETHYST 1"},
        {"spoken_line": "कटेला 2", "on_screen_text": "AMETHYST 2"},
        {"spoken_line": "कटेला 3", "on_screen_text": "AMETHYST 3"},
        {"spoken_line": "कटेला 4", "on_screen_text": "AMETHYST 4"},
        {"spoken_line": "सावधानी: नकली कांच से बचें", "on_screen_text": "CAUTION"},
        {"spoken_line": "अभी संपर्क करें", "on_screen_text": "COMMENT"},
    ]

    vid1_assigned = []
    used_v1 = set()
    for i, sc in enumerate(pyrite_scenes):
        img = DynamicVisualEngine.get_or_generate_scene_image(
            scene_dict=sc, topic="Pyrite Crystal Benefits", scene_idx=i, total_scenes=7, reel_slug="pyrite_v1", used_images=used_v1
        )
        vid1_assigned.append(img)

    vid2_assigned = []
    used_v2 = set()
    for i, sc in enumerate(amethyst_scenes):
        img = DynamicVisualEngine.get_or_generate_scene_image(
            scene_dict=sc, topic="Amethyst Crystal Healing", scene_idx=i, total_scenes=7, reel_slug="amethyst_v2", used_images=used_v2
        )
        vid2_assigned.append(img)

    # Assert Scene 6 is different across videos
    assert vid1_assigned[5].name != vid2_assigned[5].name
    # Assert Scene 7 is different across videos
    assert vid1_assigned[6].name != vid2_assigned[6].name

    # Neither video should end with the hardcoded havan or temple lamps
    assert "sacred_havan" not in vid1_assigned[5].name.lower()
    assert "sacred_havan" not in vid2_assigned[5].name.lower()
    assert "sacred_temple" not in vid1_assigned[6].name.lower()
    assert "sacred_temple" not in vid2_assigned[6].name.lower()


def test_content_hash_and_url_repetition_blocked():
    """Verify that identical source URLs and content byte hashes are permanently blocked."""
    u_id = uuid.uuid4().hex
    test_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/Sample_Amethyst_{u_id}.jpg?width=1080"
    test_bytes = f"unique_amethyst_photograph_test_bytes_{u_id}".encode()

    # Before registration
    assert DynamicVisualEngine.is_image_used(test_url, file_bytes=test_bytes) is False

    # Register
    DynamicVisualEngine.register_used_image(test_url, file_bytes=test_bytes)

    # 1. Exact URL matches
    assert DynamicVisualEngine.is_image_used(test_url) is True

    # 2. Base URL (without query params) matches
    base_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/Sample_Amethyst_{u_id}.jpg"
    assert DynamicVisualEngine.is_image_used(base_url) is True

    # 3. Content hash matches even if path is completely different
    different_filename = Path(f"completely_different_scene_{u_id}.jpg")
    assert DynamicVisualEngine.is_image_used(different_filename, file_bytes=test_bytes) is True
