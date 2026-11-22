"""
Targeted Verification Tests for Script-Driven Astrology Visual Intelligence.
Validates all 10 mandatory scenarios:
- Case A: House only ("The 12th house becomes important.") -> House 12, no planet.
- Case B: Planet only ("Jupiter brings wisdom.") -> Jupiter, no house, no aspect, no conjunction.
- Case C: Planet and house ("Sun in the 8th house.") -> Sun in House 8.
- Case D: Explicit conjunction ("Sun and Rahu are conjunct in the 8th house.") -> Sun + Rahu in House 8.
- Case E: Two planets mentioned but not conjunct ("Sun brings vitality while Rahu represents disruption.") -> Both planets detected, NOT conjunction.
- Case F: Aspect with target only ("Saturn aspects the 12th house.") -> Saturn detected, target House 12, source unknown (None), no invented source.
- Case G: Verified aspect -> Verified chart data provides source and valid aspect.
- Case H: Unknown aspecting planet ("The 12th house receives an aspect.") -> Target House 12, no invented planet.
- Case I: Three-planet conjunction ("Sun, Mercury and Venus are conjunct in the 1st house.") -> All 3 planets displayed cleanly, no truncation.
- Case J: Scene transition (Scene 1: "Venus in the 7th house." Scene 2: "The 12th house becomes important.") -> Scene 1 Venus in House 7; Scene 2 House 12 only; Venus does not linger.
"""

from pathlib import Path
from PIL import Image
import pytest

from app.video.kundli_chart_generator import KundliChartGenerator, AstrologyScenePlan


class TestTargetedAstrologyCorrections:

    def test_case_a_house_only(self, tmp_path: Path):
        """Case A: 'The 12th house becomes important.' -> House 12 detected, no planet invented."""
        narration = "The 12th house becomes important."
        plan = KundliChartGenerator.parse_astrology_scene(narration)

        assert plan.intent == "HOUSE_ONLY"
        assert plan.primary_house == 12
        assert plan.target_house is None
        assert len(plan.planets) == 0, f"Expected 0 planets, got {plan.planets}"

        # Visual rendering
        out_p = tmp_path / "case_a.jpg"
        res = KundliChartGenerator.generate_3d_kundli_planet_scene(
            scene_dict={"spoken_line": narration},
            topic="Spiritual Secrets",
            scene_idx=0,
            output_path=out_p,
        )
        assert res.exists()
        with Image.open(res) as img:
            assert img.size == (1080, 1920)

    def test_case_b_planet_only(self, tmp_path: Path):
        """Case B: 'Jupiter brings wisdom.' -> Jupiter detected, no house/aspect/conjunction invented."""
        narration = "Jupiter brings wisdom."
        plan = KundliChartGenerator.parse_astrology_scene(narration)

        assert plan.intent == "PLANET_ONLY"
        assert plan.primary_house is None, f"Expected None for house, got {plan.primary_house}"
        assert plan.target_house is None
        assert plan.planets == ["jupiter"]
        assert plan.aspect_type is None
        assert plan.relationship == "archetype"

        # Visual rendering
        out_p = tmp_path / "case_b.jpg"
        res = KundliChartGenerator.generate_3d_kundli_planet_scene(
            scene_dict={"spoken_line": narration},
            topic="Guru Wisdom",
            scene_idx=1,
            output_path=out_p,
        )
        assert res.exists()
        with Image.open(res) as img:
            assert img.size == (1080, 1920)

    def test_case_c_planet_and_house(self, tmp_path: Path):
        """Case C: 'Sun in the 8th house.' -> Sun detected, House 8 detected, Sun in house 8."""
        narration = "Sun in the 8th house."
        plan = KundliChartGenerator.parse_astrology_scene(narration)

        assert plan.intent == "PLANET_IN_HOUSE"
        assert plan.primary_house == 8
        assert plan.planets == ["sun"]
        assert plan.relationship == "placement"

        # Visual rendering
        out_p = tmp_path / "case_c.jpg"
        res = KundliChartGenerator.generate_3d_kundli_planet_scene(
            scene_dict={"spoken_line": narration},
            topic="Transformation",
            scene_idx=2,
            output_path=out_p,
        )
        assert res.exists()
        with Image.open(res) as img:
            assert img.size == (1080, 1920)

    def test_case_d_explicit_conjunction(self, tmp_path: Path):
        """Case D: 'Sun and Rahu are conjunct in the 8th house.' -> Both in house 8, conjunction."""
        narration = "Sun and Rahu are conjunct in the 8th house."
        plan = KundliChartGenerator.parse_astrology_scene(narration)

        assert plan.intent == "CONJUNCTION"
        assert plan.primary_house == 8
        assert "sun" in plan.planets
        assert "rahu" in plan.planets
        assert len(plan.planets) == 2
        assert plan.relationship == "conjunction"

        # Visual rendering
        out_p = tmp_path / "case_d.jpg"
        res = KundliChartGenerator.generate_3d_kundli_planet_scene(
            scene_dict={"spoken_line": narration},
            topic="Solar Eclipse Yoga",
            scene_idx=3,
            output_path=out_p,
        )
        assert res.exists()
        with Image.open(res) as img:
            assert img.size == (1080, 1920)

    def test_case_e_two_planets_not_conjunct(self, tmp_path: Path):
        """Case E: 'Sun brings vitality while Rahu represents disruption.' -> NOT a conjunction."""
        narration = "Sun brings vitality while Rahu represents disruption."
        plan = KundliChartGenerator.parse_astrology_scene(narration)

        assert plan.intent == "MULTI_PLANET", f"Expected MULTI_PLANET, got {plan.intent}"
        assert plan.relationship == "contrast"
        assert "sun" in plan.planets
        assert "rahu" in plan.planets
        assert plan.primary_house is None, f"Expected no house invented, got {plan.primary_house}"

        # Visual rendering
        out_p = tmp_path / "case_e.jpg"
        res = KundliChartGenerator.generate_3d_kundli_planet_scene(
            scene_dict={"spoken_line": narration},
            topic="Archetypal Contrast",
            scene_idx=4,
            output_path=out_p,
        )
        assert res.exists()
        with Image.open(res) as img:
            assert img.size == (1080, 1920)

    def test_case_f_aspect_with_target_only(self, tmp_path: Path):
        """Case F: 'Saturn aspects the 12th house.' -> Target 12, Source unknown (None), no invented house."""
        narration = "Saturn aspects the 12th house."
        plan = KundliChartGenerator.parse_astrology_scene(narration)

        assert plan.intent == "ASPECT"
        assert plan.planets == ["saturn"]
        assert plan.target_house == 12
        assert plan.primary_house is None, f"Expected source to be unknown (None), got {plan.primary_house}"
        assert plan.source_explicit is False
        assert plan.target_explicit is True

        # Visual rendering
        out_p = tmp_path / "case_f.jpg"
        res = KundliChartGenerator.generate_3d_kundli_planet_scene(
            scene_dict={"spoken_line": narration},
            topic="Shani Drishti",
            scene_idx=5,
            output_path=out_p,
        )
        assert res.exists()
        with Image.open(res) as img:
            assert img.size == (1080, 1920)

    def test_case_g_verified_aspect(self, tmp_path: Path):
        """Case G: Verified chart data provides source placement and aspect verification."""
        narration = "Saturn aspects the 12th house."
        chart_data = {"saturn": 6}  # Saturn in 6th house casting 7th aspect onto 12th house
        plan = KundliChartGenerator.parse_astrology_scene(narration, chart_data=chart_data)

        assert plan.intent == "ASPECT"
        assert plan.planets == ["saturn"]
        assert plan.primary_house == 6
        assert plan.target_house == 12
        assert plan.aspect_verified is True
        assert plan.aspect_count == 7

        # Visual rendering
        out_p = tmp_path / "case_g.jpg"
        res = KundliChartGenerator.generate_3d_kundli_planet_scene(
            scene_dict={"spoken_line": narration, "chart_data": chart_data},
            topic="Verified Shani Drishti",
            scene_idx=6,
            output_path=out_p,
        )
        assert res.exists()
        with Image.open(res) as img:
            assert img.size == (1080, 1920)

    def test_case_h_unknown_aspecting_planet(self, tmp_path: Path):
        """Case H: 'The 12th house receives an aspect.' -> Target 12, no invented planet."""
        narration = "The 12th house receives an aspect."
        plan = KundliChartGenerator.parse_astrology_scene(narration)

        assert plan.intent == "ASPECT"
        assert plan.target_house == 12
        assert plan.primary_house is None
        assert len(plan.planets) == 0, f"Expected 0 planets, got {plan.planets}"

        # Visual rendering
        out_p = tmp_path / "case_h.jpg"
        res = KundliChartGenerator.generate_3d_kundli_planet_scene(
            scene_dict={"spoken_line": narration},
            topic="Aspect Received",
            scene_idx=7,
            output_path=out_p,
        )
        assert res.exists()
        with Image.open(res) as img:
            assert img.size == (1080, 1920)

    def test_case_i_three_planet_conjunction(self, tmp_path: Path):
        """Case I: 'Sun, Mercury and Venus are conjunct in the 1st house.' -> All 3 planets displayed cleanly."""
        narration = "Sun, Mercury and Venus are conjunct in the 1st house."
        plan = KundliChartGenerator.parse_astrology_scene(narration)

        assert plan.intent == "CONJUNCTION"
        assert plan.primary_house == 1
        assert len(plan.planets) == 3
        assert set(plan.planets) == {"sun", "mercury", "venus"}

        # Visual rendering
        out_p = tmp_path / "case_i.jpg"
        res = KundliChartGenerator.generate_3d_kundli_planet_scene(
            scene_dict={"spoken_line": narration},
            topic="Triple Conjunction",
            scene_idx=8,
            output_path=out_p,
        )
        assert res.exists()
        with Image.open(res) as img:
            assert img.size == (1080, 1920)

    def test_case_j_scene_transition_no_lingering_entities(self, tmp_path: Path):
        """Case J: Scene 1: 'Venus in the 7th house.' Scene 2: 'The 12th house becomes important.'"""
        scene_1_narration = "Venus in the 7th house."
        scene_2_narration = "The 12th house becomes important."

        plan_1 = KundliChartGenerator.parse_astrology_scene(scene_1_narration)
        assert plan_1.intent == "PLANET_IN_HOUSE"
        assert plan_1.primary_house == 7
        assert plan_1.planets == ["venus"]

        plan_2 = KundliChartGenerator.parse_astrology_scene(scene_2_narration)
        assert plan_2.intent == "HOUSE_ONLY"
        assert plan_2.primary_house == 12
        assert len(plan_2.planets) == 0, "Venus must not linger into Scene 2!"

        out_1 = tmp_path / "case_j_scene_1.jpg"
        out_2 = tmp_path / "case_j_scene_2.jpg"

        res_1 = KundliChartGenerator.generate_3d_kundli_planet_scene(
            scene_dict={"spoken_line": scene_1_narration},
            topic="Transits",
            scene_idx=0,
            output_path=out_1,
        )
        res_2 = KundliChartGenerator.generate_3d_kundli_planet_scene(
            scene_dict={"spoken_line": scene_2_narration},
            topic="Transits",
            scene_idx=1,
            output_path=out_2,
        )
        assert res_1.exists() and res_2.exists()
        assert out_1.read_bytes() != out_2.read_bytes()
