"""
Tests for Dynamic Vedic Kundli Chart Visual Generator.
Verifies:
1. Extraction of houses (1-12) and planets across English, Hindi (direct & oblique cases).
2. Dynamic 1080x1920 chart generation with house highlighting.
3. Anti-repetition: Distinct houses produce distinct visual outputs.
"""

from pathlib import Path
from PIL import Image
import pytest

from app.video.kundli_chart_generator import (
    KundliChartGenerator,
    HOUSE_METADATA,
    DEVANAGARI_NUMERALS,
)


def test_house_and_planet_extraction():
    """Verify extraction handles diverse Hindi inflections and English terms."""
    # 8th house with Rahu (oblique case 'आठवें')
    h8, p8 = KundliChartGenerator.extract_house_and_planet("कुंडली के आठवें भाव में राहु है")
    assert h8 == 8
    assert p8 is not None and "राहु" in p8

    # 2nd house of wealth ('दूसरे')
    h2, _ = KundliChartGenerator.extract_house_and_planet("दूसरे भाव में जब धन योग बनता है")
    assert h2 == 2

    # 10th house career with Saturn
    h10, p10 = KundliChartGenerator.extract_house_and_planet("When Saturn transits your 10th house")
    assert h10 == 10
    assert p10 is not None and "SATURN" in p10

    # 7th house marriage
    h7, _ = KundliChartGenerator.extract_house_and_planet("सप्तम भाव में विवाह का योग")
    assert h7 == 7

    # 5th house intellect ('पंचम')
    h5, _ = KundliChartGenerator.extract_house_and_planet("पंचम भाव पूर्व जन्म के कर्म दिखाता है")
    assert h5 == 5

    # 12th house foreign / losses ('द्वादश')
    h12, _ = KundliChartGenerator.extract_house_and_planet("12th house foreign settlement")
    assert h12 == 12


def test_dynamic_chart_rendering(tmp_path: Path):
    """Verify dynamic chart generates valid 1080x1920 image with correct metadata."""
    chart_p2 = tmp_path / "chart_h2.jpg"
    chart_p8 = tmp_path / "chart_h8.jpg"

    out2 = KundliChartGenerator.generate_dynamic_chart(
        highlight_house=2,
        planet_name="गुरु (JUPITER)",
        title="2ND HOUSE: WEALTH & FAMILY",
        output_path=chart_p2,
    )
    assert out2.exists()
    with Image.open(out2) as img2:
        assert img2.size == (1080, 1920)
        assert img2.mode == "RGB"

    out8 = KundliChartGenerator.generate_dynamic_chart(
        highlight_house=8,
        planet_name="राहु (RAHU)",
        title="8TH HOUSE: TRANSFORMATION",
        output_path=chart_p8,
    )
    assert out8.exists()
    with Image.open(out8) as img8:
        assert img8.size == (1080, 1920)
        assert img8.mode == "RGB"

    # Distinct houses must produce distinct files
    bytes2 = chart_p2.read_bytes()
    bytes8 = chart_p8.read_bytes()
    assert bytes2 != bytes8


def test_house_metadata_integrity():
    """Verify all 12 houses have complete English, Hindi, and Sanskrit metadata."""
    for h in range(1, 13):
        assert h in HOUSE_METADATA
        meta = HOUSE_METADATA[h]
        assert "name_hi" in meta
        assert "name_en" in meta
        assert "sanskrit" in meta
        assert "significance" in meta
        assert h in DEVANAGARI_NUMERALS


def test_generate_3d_kundli_planet_scene_all_archetypes(tmp_path: Path):
    """Verify tilted 3D Kundli with top celestial planet renders across all archetypes."""
    scenarios = [
        ({"spoken_line": "शनि सप्तम भाव में दृष्टि डाल रहे हैं", "on_screen_text": "SHANI 7TH HOUSE"}, "Saturn Shani 7th", 7),
        ({"spoken_line": "सूर्य और राहु का प्रथम भाव में ग्रहण योग", "on_screen_text": "SUN RAHU ECLIPSE"}, "Sun Rahu 1st", 1),
        ({"spoken_line": "बारहवें भाव से ऊर्जा का व्यय हो रहा है", "on_screen_text": "12TH HOUSE DRAIN"}, "12th House Vyaya", 12),
        ({"spoken_line": "मंगल प्रथम भाव में अग्नि ऊर्जा प्रदान करता है", "on_screen_text": "MARS 1ST HOUSE"}, "Mars 1st", 1),
        ({"spoken_line": "गुरु बृहस्पति नवम भाव में भाग्य को जगाते हैं", "on_screen_text": "JUPITER 9TH HOUSE"}, "Jupiter Guru 9th", 9),
        ({"spoken_line": "बुध तृतीय भाव में बुद्धि और व्यापार बढ़ाता है", "on_screen_text": "MERCURY 3RD HOUSE"}, "Mercury Budha 3rd", 3),
    ]

    for idx, (scene_dict, topic, expected_house) in enumerate(scenarios):
        out_p = tmp_path / f"test_3d_planet_{idx}.jpg"
        result_path = KundliChartGenerator.generate_3d_kundli_planet_scene(
            scene_dict=scene_dict,
            topic=topic,
            scene_idx=idx,
            output_path=out_p,
        )
        assert result_path.exists()
        with Image.open(result_path) as img:
            assert img.size == (1080, 1920)
            assert img.mode == "RGB"

