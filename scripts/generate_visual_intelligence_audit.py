"""
Visual Intelligence Audit & Verification Script.
Generates 'after' visual images for all mandatory test scenarios from Section 8:
- Case A: House only ("The 12th house becomes important.")
- Case B: Planet only ("Jupiter brings wisdom.")
- Case C: Planet in a house ("Sun in the 8th house.")
- Case D: Explicit conjunction ("Sun and Rahu are conjunct in the 8th house.")
- Case E: Two planets mentioned but not conjunct ("Sun brings vitality while Rahu represents disruption.")
- Case F: Aspect with target only ("Saturn aspects the 12th house.")
- Case G: Verified aspect (Saturn in 6th casting 7th aspect onto 12th house via verified chart data)
- Case H: Unknown aspecting planet ("The 12th house receives an aspect.")
- Case I: Three-planet conjunction ("Sun, Mercury and Venus are conjunct in the 1st house.")
- Case J1: Scene transition 1 ("Venus in the 7th house.")
- Case J2: Scene transition 2 ("The 12th house becomes important.")

Creates a comprehensive side-by-side Before/After comparison contact sheet:
- output/visual_intelligence_audit/comparison_contact_sheet.jpg
Where before images are unavailable, they are clearly and honestly labeled [Before Unavailable].
"""

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.video.kundli_chart_generator import KundliChartGenerator

OUTPUT_DIR = PROJECT_ROOT / "output" / "visual_intelligence_audit"
AFTER_DIR = OUTPUT_DIR / "after"
BEFORE_DIR = OUTPUT_DIR / "before"
AFTER_DIR.mkdir(parents=True, exist_ok=True)
BEFORE_DIR.mkdir(parents=True, exist_ok=True)

test_scenarios = [
    {
        "id": "case_a_house_only",
        "title": "Case A: House Only",
        "scene_dict": {
            "spoken_line": "The 12th house becomes important.",
            "on_screen_text": "12TH HOUSE ACTIVATION",
            "visual_description": "Subconscious and spiritual liberation house activates with radiant light",
        },
        "topic": "Vedic Astrology Secrets",
        "expected_intent": "HOUSE_ONLY",
        "expected_house": 12,
        "expected_target": None,
        "expected_planets": [],
    },
    {
        "id": "case_b_planet_only",
        "title": "Case B: Planet Only",
        "scene_dict": {
            "spoken_line": "Jupiter brings wisdom.",
            "on_screen_text": "JUPITER EXPANSION",
            "visual_description": "Planet Jupiter radiating cosmic wisdom in starry deep space",
        },
        "topic": "Jupiter Guru Guidance",
        "expected_intent": "PLANET_ONLY",
        "expected_house": None,
        "expected_target": None,
        "expected_planets": ["jupiter"],
    },
    {
        "id": "case_c_planet_in_house",
        "title": "Case C: Planet in House",
        "scene_dict": {
            "spoken_line": "Sun in the 8th house.",
            "on_screen_text": "SURYA IN 8TH HOUSE",
            "visual_description": "Sun positioned inside house 8 with floor contact shadow",
        },
        "topic": "Surya Transformation",
        "expected_intent": "PLANET_IN_HOUSE",
        "expected_house": 8,
        "expected_target": None,
        "expected_planets": ["sun"],
    },
    {
        "id": "case_d_explicit_conjunction",
        "title": "Case D: Explicit Conjunction",
        "scene_dict": {
            "spoken_line": "Sun and Rahu are conjunct in the 8th house.",
            "on_screen_text": "SURYA RAHU CONJUNCTION",
            "visual_description": "Sun and Rahu together in the 8th house with dual aura",
        },
        "topic": "Grahan Yoga",
        "expected_intent": "CONJUNCTION",
        "expected_house": 8,
        "expected_target": None,
        "expected_planets": ["sun", "rahu"],
    },
    {
        "id": "case_e_two_planets_not_conjunct",
        "title": "Case E: Two Planets (Contrast, NOT Conjunct)",
        "scene_dict": {
            "spoken_line": "Sun brings vitality while Rahu represents disruption.",
            "on_screen_text": "SURYA VS RAHU",
            "visual_description": "Distinct celestial forces of Sun and Rahu in cosmic balance",
        },
        "topic": "Planetary Contrasts",
        "expected_intent": "MULTI_PLANET",
        "expected_house": None,
        "expected_target": None,
        "expected_planets": ["sun", "rahu"],
    },
    {
        "id": "case_f_aspect_target_only",
        "title": "Case F: Aspect (Target Only)",
        "scene_dict": {
            "spoken_line": "Saturn aspects the 12th house.",
            "on_screen_text": "SHANI ASPECTS 12TH HOUSE",
            "visual_description": "Saturn casting powerful aspect rays directly into house 12",
        },
        "topic": "Karmic Alignment",
        "expected_intent": "ASPECT",
        "expected_house": None,
        "expected_target": 12,
        "expected_planets": ["saturn"],
    },
    {
        "id": "case_g_verified_aspect",
        "title": "Case G: Verified Aspect (with Chart Data)",
        "scene_dict": {
            "spoken_line": "Saturn aspects the 12th house.",
            "on_screen_text": "VERIFIED SHANI DRISHTI",
            "visual_description": "Saturn in 6th house casting 7th drishti onto 12th house",
            "chart_data": {"saturn": 6},
        },
        "topic": "Verified Jyotish Placements",
        "expected_intent": "ASPECT",
        "expected_house": 6,
        "expected_target": 12,
        "expected_planets": ["saturn"],
    },
    {
        "id": "case_h_unknown_aspecting_planet",
        "title": "Case H: Unknown Aspecting Planet",
        "scene_dict": {
            "spoken_line": "The 12th house receives an aspect.",
            "on_screen_text": "12TH HOUSE ASPECT RECEIVED",
            "visual_description": "Golden rays illuminating house 12 without invented planet",
        },
        "topic": "Subconscious Illumination",
        "expected_intent": "ASPECT",
        "expected_house": None,
        "expected_target": 12,
        "expected_planets": [],
    },
    {
        "id": "case_i_three_planet_conjunction",
        "title": "Case I: Three-Planet Conjunction",
        "scene_dict": {
            "spoken_line": "Sun, Mercury and Venus are conjunct in the 1st house.",
            "on_screen_text": "TRIPLE CONJUNCTION 1ST HOUSE",
            "visual_description": "All three planets cleanly arrayed inside the ascendant",
        },
        "topic": "Royal Yogas",
        "expected_intent": "CONJUNCTION",
        "expected_house": 1,
        "expected_target": None,
        "expected_planets": ["sun", "mercury", "venus"],
    },
    {
        "id": "case_j1_transition_scene1",
        "title": "Case J1: Transition Scene 1",
        "scene_dict": {
            "spoken_line": "Venus in the 7th house.",
            "on_screen_text": "VENUS IN 7TH HOUSE",
            "visual_description": "Venus positioned in the 7th house of marriage",
        },
        "topic": "Relationship Journey",
        "expected_intent": "PLANET_IN_HOUSE",
        "expected_house": 7,
        "expected_target": None,
        "expected_planets": ["venus"],
    },
    {
        "id": "case_j2_transition_scene2",
        "title": "Case J2: Transition Scene 2 (No Lingering Venus)",
        "scene_dict": {
            "spoken_line": "The 12th house becomes important.",
            "on_screen_text": "12TH HOUSE TRANSIT",
            "visual_description": "12th house illuminated without lingering Venus",
        },
        "topic": "Relationship Journey",
        "expected_intent": "HOUSE_ONLY",
        "expected_house": 12,
        "expected_target": None,
        "expected_planets": [],
    },
]


def run_audit():
    print("=" * 70)
    print("STARTING AUDIT: Script-Driven Astrology Visual Intelligence")
    print("=" * 70)

    generated_files = {}

    for idx, sc in enumerate(test_scenarios):
        print(f"\nEvaluating {sc['title']}...")
        spoken = sc["scene_dict"]["spoken_line"]
        chart_data = sc["scene_dict"].get("chart_data")
        plan = KundliChartGenerator.parse_astrology_scene(spoken, fallback_topic=sc["topic"], chart_data=chart_data)

        print(f"  Parsed Intent: {plan.intent} (Expected: {sc['expected_intent']})")
        print(f"  Primary House (Source): {plan.primary_house} (Expected: {sc['expected_house']})")
        print(f"  Target House: {plan.target_house} (Expected: {sc['expected_target']})")
        print(f"  Planets: {plan.planets} (Expected: {sc['expected_planets']})")
        print(f"  Badge Title: '{plan.badge_title}'")
        print(f"  Relationship: {plan.relationship}")

        # Assertions
        assert plan.intent == sc["expected_intent"], f"Intent mismatch for {sc['id']}"
        assert plan.primary_house == sc["expected_house"], f"Source house mismatch for {sc['id']}"
        assert plan.target_house == sc["expected_target"], f"Target house mismatch for {sc['id']}"
        assert set(plan.planets) == set(sc["expected_planets"]), f"Planets mismatch for {sc['id']}"

        out_p = AFTER_DIR / f"{sc['id']}_after.jpg"
        res_path = KundliChartGenerator.generate_3d_kundli_planet_scene(
            scene_dict=sc["scene_dict"],
            topic=sc["topic"],
            scene_idx=idx,
            output_path=out_p,
            chart_data=chart_data,
        )
        assert res_path.exists()
        print(f"  -> Generated Image: {res_path.name} ({res_path.stat().st_size // 1024} KB)")
        generated_files[sc["id"]] = res_path

    print("\n" + "=" * 70)
    print("ALL 11 MANDATORY TEST CASES GENERATED AND VERIFIED SUCCESSFULLY!")
    print("=" * 70)

    # Build Side-by-Side Comparison Contact Sheet
    thumb_w, thumb_h = 360, 640
    header_h = 90
    rows = len(test_scenarios)
    total_w = thumb_w * 2 + 100
    total_h = rows * (thumb_h + header_h) + 140

    sheet = Image.new("RGB", (total_w, total_h), (12, 10, 18))
    sdraw = ImageDraw.Draw(sheet)

    try:
        font_hdr = ImageFont.truetype("arial.ttf", 28)
        font_sub = ImageFont.truetype("arial.ttf", 20)
        font_side = ImageFont.truetype("arial.ttf", 22)
    except Exception:
        font_hdr = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_side = ImageFont.load_default()

    # Main Sheet Header
    sdraw.text((40, 25), "SCRIPT-DRIVEN ASTROLOGY VISUAL INTELLIGENCE AUDIT", fill=(255, 215, 60), font=font_hdr)
    sdraw.text((40, 65), "Strict Script Ground Truth & Verification: No Invented Entities", fill=(200, 190, 180), font=font_sub)

    y_cur = 130
    for sc in test_scenarios:
        cid = sc["id"]
        ctitle = f"{sc['title']} • '{sc['scene_dict']['spoken_line']}'"
        before_file = BEFORE_DIR / f"{cid}_before.jpg"
        after_file = AFTER_DIR / f"{cid}_after.jpg"

        # Case Title
        sdraw.rectangle([30, y_cur, total_w - 30, y_cur + 42], fill=(22, 18, 30))
        sdraw.text((40, y_cur + 8), ctitle[:65], fill=(255, 235, 140), font=font_side)
        y_cur += 52

        # Before Image (Honest verification: Never fabricate!)
        if before_file.exists():
            b_img = Image.open(before_file).resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            sheet.paste(b_img, (40, y_cur))
            sdraw.rectangle([40, y_cur, 40 + thumb_w, y_cur + thumb_h], outline=(220, 60, 40), width=3)
            sdraw.text((50, y_cur + 15), "BEFORE (Baseline)", fill=(255, 80, 80), font=font_side)
        else:
            sdraw.rectangle([40, y_cur, 40 + thumb_w, y_cur + thumb_h], fill=(16, 12, 22), outline=(80, 80, 80), width=2)
            sdraw.text((60, y_cur + thumb_h // 2 - 20), "[Before Image Unavailable]", fill=(200, 120, 120), font=font_side)
            sdraw.text((60, y_cur + thumb_h // 2 + 15), "No baseline recorded pre-fix.", fill=(140, 140, 140), font=font_sub)

        # After Image
        if after_file.exists():
            a_img = Image.open(after_file).resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            sheet.paste(a_img, (40 + thumb_w + 20, y_cur))
            sdraw.rectangle([40 + thumb_w + 20, y_cur, 40 + thumb_w * 2 + 20, y_cur + thumb_h], outline=(50, 220, 100), width=3)
            sdraw.text((50 + thumb_w + 20, y_cur + 15), "AFTER (Strict Ground Truth)", fill=(80, 255, 130), font=font_side)

        y_cur += thumb_h + 35

    comparison_path = OUTPUT_DIR / "comparison_contact_sheet.jpg"
    sheet.save(str(comparison_path), "JPEG", quality=92)
    print(f"\nComparison Contact Sheet Saved: {comparison_path}")
    print("Verification Script Complete!")


if __name__ == "__main__":
    run_audit()
