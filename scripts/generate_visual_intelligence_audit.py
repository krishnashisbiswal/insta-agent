"""
Visual Intelligence Audit & Verification Script.
Generates 'after' visual images for all mandatory test scenarios from Section 14:
- Test A: House only ("The 12th house becomes important.")
- Test B: Planet only ("Jupiter brings wisdom and expansion")
- Test C: Planet in a house ("Sun in the 8th house")
- Test D: Conjunction ("Sun and Mercury in the 1st house")
- Test E: Aspect ("Saturn in the 10th house casts its 7th aspect onto the 4th house")
- Test F1: Scene transition 1 ("The 4th house represents mother and peace")
- Test F2: Scene transition 2 ("Mars enters the 10th house")
- Test G: Complex narration ("When Rahu occupies the 8th house, it creates deep transformational shifts")

Creates a side-by-side Before/After comparison contact sheet:
- output/visual_intelligence_audit/comparison_contact_sheet.jpg
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
        "expected_planets": [],
    },
    {
        "id": "case_b_planet_only",
        "title": "Case B: Planet Only",
        "scene_dict": {
            "spoken_line": "Jupiter brings wisdom and expansion",
            "on_screen_text": "JUPITER EXPANSION",
            "visual_description": "Planet Jupiter radiating cosmic wisdom in starry deep space",
        },
        "topic": "Jupiter Guru Guidance",
        "expected_intent": "PLANET_ONLY",
        "expected_house": None,
        "expected_planets": ["jupiter"],
    },
    {
        "id": "case_c_planet_in_house",
        "title": "Case C: Planet in House",
        "scene_dict": {
            "spoken_line": "Sun in the 8th house",
            "on_screen_text": "SURYA IN 8TH HOUSE",
            "visual_description": "Sun positioned inside house 8 with floor contact shadow",
        },
        "topic": "Surya Transformation",
        "expected_intent": "PLANET_IN_HOUSE",
        "expected_house": 8,
        "expected_planets": ["sun"],
    },
    {
        "id": "case_d_conjunction",
        "title": "Case D: Conjunction",
        "scene_dict": {
            "spoken_line": "Sun and Mercury in the 1st house",
            "on_screen_text": "BUDHADITYA YOGA 1ST HOUSE",
            "visual_description": "Both Sun and Mercury together in the 1st house with dual aura",
        },
        "topic": "Royal Astrological Yogas",
        "expected_intent": "CONJUNCTION",
        "expected_house": 1,
        "expected_planets": ["sun", "mercury"],
    },
    {
        "id": "case_e_aspect",
        "title": "Case E: Aspect (Drishti)",
        "scene_dict": {
            "spoken_line": "Saturn in the 10th house casts its 7th aspect onto the 4th house",
            "on_screen_text": "SHANI 7TH DRISHTI ON 4TH HOUSE",
            "visual_description": "Saturn in house 10 casting direct golden ray onto house 4",
        },
        "topic": "Shani Karmic Alignment",
        "expected_intent": "ASPECT",
        "expected_house": 10,
        "expected_planets": ["saturn"],
    },
    {
        "id": "case_f1_transition_scene1",
        "title": "Case F1: Transition (Scene 1)",
        "scene_dict": {
            "spoken_line": "The 4th house represents mother and peace",
            "on_screen_text": "4TH HOUSE SUKHA",
            "visual_description": "4th house highlighted in golden illumination",
        },
        "topic": "Life Houses Journey",
        "expected_intent": "HOUSE_ONLY",
        "expected_house": 4,
        "expected_planets": [],
    },
    {
        "id": "case_f2_transition_scene2",
        "title": "Case F2: Transition (Scene 2)",
        "scene_dict": {
            "spoken_line": "Mars enters the 10th house",
            "on_screen_text": "MARS IN 10TH HOUSE",
            "visual_description": "Mars entering the 10th house of career and leadership",
        },
        "topic": "Life Houses Journey",
        "expected_intent": "PLANET_IN_HOUSE",
        "expected_house": 10,
        "expected_planets": ["mars"],
    },
    {
        "id": "case_g_complex_narration",
        "title": "Case G: Complex Narration",
        "scene_dict": {
            "spoken_line": "When Rahu occupies the 8th house, it creates deep transformational shifts",
            "on_screen_text": "RAHU IN 8TH HOUSE",
            "visual_description": "Rahu in the 8th house of sudden transformations",
        },
        "topic": "Rahu Mysteries",
        "expected_intent": "PLANET_IN_HOUSE",
        "expected_house": 8,
        "expected_planets": ["rahu"],
    },
]


def run_audit():
    print("=" * 70)
    print("STARTING ASTROLOGY VISUAL INTELLIGENCE AUDIT & VERIFICATION")
    print("=" * 70)

    generated_files = {}

    for idx, sc in enumerate(test_scenarios):
        out_p = AFTER_DIR / f"{sc['id']}_after.jpg"
        print(f"\nProcessing [{sc['title']}]...")
        narration = f"{sc['scene_dict']['spoken_line']} {sc['scene_dict']['on_screen_text']}"
        plan = KundliChartGenerator.parse_astrology_scene(narration, fallback_topic=sc["topic"])

        print(f" -> Parsed Intent:   {plan.intent} (Expected: {sc['expected_intent']})")
        print(f" -> Primary House:   {plan.primary_house} (Expected: {sc['expected_house']})")
        print(f" -> Target House:    {plan.target_house}")
        print(f" -> Planets:         {plan.planets} (Expected: {sc['expected_planets']})")
        print(f" -> Badge Title:     '{plan.badge_title}'")

        assert plan.intent == sc["expected_intent"], f"Intent mismatch for {sc['id']}: {plan.intent} != {sc['expected_intent']}"
        if sc["expected_house"] is not None:
            assert plan.primary_house == sc["expected_house"], f"House mismatch for {sc['id']}"
        assert set(plan.planets) == set(sc["expected_planets"]), f"Planets mismatch for {sc['id']}"

        res_path = KundliChartGenerator.generate_3d_kundli_planet_scene(
            scene_dict=sc["scene_dict"],
            topic=sc["topic"],
            scene_idx=idx,
            output_path=out_p,
        )
        assert res_path.exists()
        print(f" -> Generated Image: {res_path.name} ({res_path.stat().st_size // 1024} KB)")
        generated_files[sc["id"]] = res_path

    print("\n" + "=" * 70)
    print("ALL 8 MANDATORY TEST CASES GENERATED AND VERIFIED SUCCESSFULLY!")
    print("=" * 70)

    # Build Side-by-Side Comparison Contact Sheet (Cases A through E)
    comparison_cases = [
        ("case_a_house_only", "Case A: House Only ('12th house becomes important.')"),
        ("case_b_planet_only", "Case B: Planet Only ('Jupiter brings wisdom and expansion')"),
        ("case_c_planet_in_house", "Case C: Planet in House ('Sun in the 8th house')"),
        ("case_d_conjunction", "Case D: Conjunction ('Sun and Mercury in the 1st house')"),
        ("case_e_aspect", "Case E: Aspect ('Saturn 10th casts 7th aspect onto 4th house')"),
    ]

    thumb_w, thumb_h = 360, 640
    header_h = 100
    rows = len(comparison_cases)
    total_w = thumb_w * 2 + 100
    total_h = rows * (thumb_h + header_h) + 120

    sheet = Image.new("RGB", (total_w, total_h), (12, 10, 18))
    sdraw = ImageDraw.Draw(sheet)

    try:
        font_hdr = ImageFont.truetype("arial.ttf", 28)
        font_sub = ImageFont.truetype("arial.ttf", 20)
        font_side = ImageFont.truetype("arial.ttf", 24)
    except Exception:
        font_hdr = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_side = ImageFont.load_default()

    # Main Sheet Header
    sdraw.text((40, 25), "SCRIPT-DRIVEN ASTROLOGY VISUAL INTELLIGENCE", fill=(255, 215, 60), font=font_hdr)
    sdraw.text((40, 65), "Before (Archetype Override & Contamination) vs After (Strict Script Ground Truth)", fill=(200, 190, 180), font=font_sub)

    y_cur = 120
    for cid, ctitle in comparison_cases:
        before_file = BEFORE_DIR / f"{cid}_before.jpg"
        after_file = AFTER_DIR / f"{cid}_after.jpg"

        # Case Title
        sdraw.rectangle([30, y_cur, total_w - 30, y_cur + 40], fill=(22, 18, 30))
        sdraw.text((40, y_cur + 8), ctitle, fill=(255, 235, 140), font=font_side)
        y_cur += 50

        # Before Image
        if before_file.exists():
            b_img = Image.open(before_file).resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            sheet.paste(b_img, (40, y_cur))
            sdraw.rectangle([40, y_cur, 40 + thumb_w, y_cur + thumb_h], outline=(220, 60, 40), width=3)
            sdraw.text((50, y_cur + 15), "BEFORE (Broken)", fill=(255, 80, 80), font=font_side)
        else:
            sdraw.rectangle([40, y_cur, 40 + thumb_w, y_cur + thumb_h], outline=(80, 80, 80), width=2)
            sdraw.text((80, y_cur + thumb_h // 2), "No Before Image", fill=(140, 140, 140), font=font_sub)

        # After Image
        if after_file.exists():
            a_img = Image.open(after_file).resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            sheet.paste(a_img, (40 + thumb_w + 20, y_cur))
            sdraw.rectangle([40 + thumb_w + 20, y_cur, 40 + thumb_w * 2 + 20, y_cur + thumb_h], outline=(50, 220, 100), width=3)
            sdraw.text((50 + thumb_w + 20, y_cur + 15), "AFTER (Fixed & Accurate)", fill=(80, 255, 130), font=font_side)

        y_cur += thumb_h + 30

    comparison_path = OUTPUT_DIR / "comparison_contact_sheet.jpg"
    sheet.save(str(comparison_path), "JPEG", quality=92)
    print(f"\nComparison Contact Sheet Saved: {comparison_path}")
    print("Verification Script Complete!")


if __name__ == "__main__":
    run_audit()
