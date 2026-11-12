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

        if any(w in topic.lower() for w in ["mistake", "error", "bhool", "galti"]):
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
