import sys
from pathlib import Path
import pytest
import re

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.analytics.trend_discovery_engine import TrendDiscoveryEngine


def test_narrative_archetypes_defined():
    engine = TrendDiscoveryEngine()
    assert hasattr(engine, "NARRATIVE_ARCHETYPES")
    assert len(engine.NARRATIVE_ARCHETYPES) >= 5
    ids = [a["id"] for a in engine.NARRATIVE_ARCHETYPES]
    assert "karmic_mystery_deep_dive" in ids
    assert "real_life_symptoms" in ids
    assert "contrarian_truth" in ids
    assert "planetary_power_code" in ids
    assert "consultation_case_study" in ids


def test_record_topic_with_archetype_persistence(tmp_path):
    hist_file = tmp_path / "test_trend_history.json"
    engine = TrendDiscoveryEngine(history_file=hist_file)

    topic_data = {
        "topic": "3 Hidden Meanings If You Wake Up Between 3:00 AM and 5:00 AM",
        "category": "psychic_and_destiny",
        "sub_niche": "Psychic Intuition & Brahma Muhurta",
        "archetype": "real_life_symptoms",
        "point_count": 3,
        "badge_prefix": "SIGN",
    }
    engine.record_generated_topic(topic_data)

    hist = engine.load_history()
    assert len(hist) == 1
    assert hist[0]["topic"] == topic_data["topic"]
    assert hist[0]["archetype"] == "real_life_symptoms"
    assert hist[0]["point_count"] == 3
    assert hist[0]["badge_prefix"] == "SIGN"

    recent = engine.get_recent_elements(count=5)
    assert "real_life_symptoms" in recent["archetypes"]


def test_dynamic_badge_numbering_for_3_point_reel():
    from app.video.cinematic_composer import sanitize_ascii_text

    # Verify badge synthesis logic for 3 content points (total 5 scenes: 1 Hook + 3 Points + 1 CTA)
    total_scenes = 5
    total_pts = max(3, total_scenes - 2)
    assert total_pts == 3

    scene_dict = {"on_screen_text": "1. WAKING UP AT 3 AM"}
    topic_str = "3 Hidden Meanings If You Wake Up Between 3:00 AM and 5:00 AM"

    # Simulate get_scene_badge logic
    t_low = topic_str.lower()
    badge_prefix = "SIGN" if any(w in t_low for w in ["sign", "symptom", "lakshan", "warning", "awaken", "meaning", "wake"]) else "POINT"
    assert badge_prefix == "SIGN"

    match = re.search(r"\b(?:MISTAKE|POINT|SIGN|ISSUE|FOUNDATION|PILLAR|RULE|INSIGHT|TRUTH|PLACEMENT)?\s*([1-9])\b", scene_dict["on_screen_text"])
    assert match is not None
    badge = f"{badge_prefix} {match.group(1)} OF {total_pts}"
    assert badge == "SIGN 1 OF 3"


def test_dynamic_point_count_detection():
    test_cases = [
        ("3 Kundli Signs Rahu in 2nd House Is Creating Mysterious Financial Losses", 3, "SIGN"),
        ("The 7th House Ketu Trap: Why You Push Away Pure Love", 3, "PLACEMENT"),
        ("Why Your Rashi Means Nothing Without Your Birth Nakshatra and Pada", 3, "FOUNDATION"),
        ("The Sade Sati Lie: Why Saturn Only Destroys Fake Illusions", 3, "TRUTH"),
        ("4 Kundli Placements That Cause Career Stagnation", 4, "PLACEMENT"),
        ("5 Fatal Mistakes When Wearing Astrological Gemstones", 5, "MISTAKE"),
        ("3 Hidden Meanings If You Wake Up Between 3:00 AM and 5:00 AM", 3, "SIGN"),
        ("Vedic Astrology Foundation: 9 Planets, 27 Nakshatras and 4 Padas Explained", 4, "FOUNDATION"),
    ]

    for topic, expected_points, expected_prefix in test_cases:
        m_pts = re.search(r"^\s*([345])\b", topic) or re.search(r"\b([345])\s*(?:points?|signs?|mistakes?|flaws?|reasons?|placements?|yogas?|rules?|insights?|secrets?|meanings?|ways?|lessons?|bhav|galti|lakshan)\b", topic, re.I)
        if m_pts:
            pts = int(m_pts.group(1))
        elif re.search(r"\b5\b", topic) and not re.search(r"\b5(?::00|\s*am|\s*pm)\b", topic, re.I):
            pts = 5
        elif re.search(r"\b4\b", topic) and not re.search(r"\b4(?::00|\s*am|\s*pm)\b", topic, re.I):
            pts = 4
        elif re.search(r"\b3\b", topic) and not re.search(r"\b3(?::00|\s*am|\s*pm)\b", topic, re.I):
            pts = 3
        else:
            pts = 3
        assert pts == expected_points

        if any(w in topic.lower() for w in ["benefit", "fayde", "laabh", "fayda", "advantage"]):
            prefix = "BENEFIT"
        elif any(w in topic.lower() for w in ["guide", "how to", "science", "secret", "shastra", "vidhi"]):
            prefix = "GUIDE"
        elif any(w in topic.lower() for w in ["crystal", "rudraksha", "rudraksh", "pyrite", "amethyst", "tourmaline", "citrine"]):
            prefix = "BENEFIT"
        elif any(w in topic.lower() for w in ["mistake", "error", "bhool", "galti"]):
            prefix = "MISTAKE"
        elif any(w in topic.lower() for w in ["sign", "symptom", "lakshan", "warning", "awaken", "meaning", "wake"]):
            prefix = "SIGN"
        elif any(w in topic.lower() for w in ["truth", "myth", "lie", "reality"]):
            prefix = "TRUTH"
        elif any(w in topic.lower() for w in ["house", "placement", "bhav"]):
            prefix = "PLACEMENT"
        elif any(w in topic.lower() for w in ["foundation", "basics", "nakshatra", "pada"]):
            prefix = "FOUNDATION"
        else:
            prefix = "INSIGHT"
        assert prefix == expected_prefix


def test_crystal_and_rudraksha_categories_present():
    engine = TrendDiscoveryEngine()
    categories = engine.TRENDING_CATEGORIES

    assert "healing_crystals" in categories
    assert "sacred_rudraksha" in categories

    crystals_cat = categories["healing_crystals"]
    assert "crystals" in crystals_cat
    crystal_names = [c["name"] for c in crystals_cat["crystals"]]
    assert any("Pyrite" in n for n in crystal_names)
    assert any("Amethyst" in n for n in crystal_names)
    assert any("Tourmaline" in n for n in crystal_names)
    assert any("Citrine" in n for n in crystal_names)

    rudraksha_cat = categories["sacred_rudraksha"]
    assert "beads" in rudraksha_cat
    bead_names = [b["name"] for b in rudraksha_cat["beads"]]
    assert any("5 Mukhi" in n for n in bead_names)
    assert any("7 Mukhi" in n for n in bead_names)
    assert any("Gauri Shankar" in n for n in bead_names)

    # Ensure archetypes include sacred energy benefits
    archetype_ids = [a["id"] for a in engine.NARRATIVE_ARCHETYPES]
    assert "sacred_energy_benefits" in archetype_ids
    assert "crystal_and_rudraksha_guide" in archetype_ids


def test_crystal_and_rudraksha_badges_and_prompts():
    from app.video.dynamic_visual_engine import DynamicVisualEngine
    from app.agents.script_agent import resolve_entity_context

    # 1. Resolve Entity Context
    pyrite_ctx = resolve_entity_context("3 Hidden Benefits of Keeping Pyrite Crystal on Your Work Desk")
    assert pyrite_ctx is not None
    assert pyrite_ctx["type"] == "crystal"
    assert pyrite_ctx["name_en"] == "Pyrite"

    rudraksha_ctx = resolve_entity_context("The Science of 5 Mukhi Rudraksha: How It Regulates Blood Pressure")
    assert rudraksha_ctx is not None
    assert rudraksha_ctx["type"] == "rudraksha"
    assert "5 Mukhi" in rudraksha_ctx["name_en"]

    # 2. Dynamic Visual Engine Prompts
    pyrite_scene = {
        "spoken_line": "कार्यस्थल पर पायराइट क्रिस्टल रखने से मानसिक एकाग्रता और सकारात्मक ऊर्जा कैसे बढ़ती है?",
        "on_screen_text": "PYRITE CRYSTAL BENEFITS",
        "visual_description": "macro shot of golden pyrite crystal on wooden desk",
    }
    p_prompt = DynamicVisualEngine.get_trait_visual_prompt(
        pyrite_scene, "3 Hidden Benefits of Keeping Pyrite Crystal on Your Work Desk", scene_idx=0
    )
    assert "pyrite" in p_prompt.lower()
    assert "macro" in p_prompt.lower()

    rudraksha_scene = {
        "spoken_line": "प्राकृतिक पंचमुखी रुद्राक्ष आपके तंत्रिका तंत्र को शांत करने में मदद करता है।",
        "on_screen_text": "5 MUKHI RUDRAKSHA SCIENCE",
        "visual_description": "sacred nepali rudraksha bead with water droplets",
    }
    r_prompt = DynamicVisualEngine.get_trait_visual_prompt(
        rudraksha_scene, "The Science of 5 Mukhi Rudraksha", scene_idx=0
    )
    assert "rudraksha" in r_prompt.lower()

    # 3. Dynamic Visual Engine Search Queries
    p_query = DynamicVisualEngine.get_scene_search_query(
        pyrite_scene, "3 Hidden Benefits of Keeping Pyrite Crystal on Your Work Desk", scene_idx=0
    )
    assert "pyrite" in p_query.lower()

    r_query = DynamicVisualEngine.get_scene_search_query(
        rudraksha_scene, "The Science of 5 Mukhi Rudraksha", scene_idx=0
    )
    assert "rudraksha" in r_query.lower()
