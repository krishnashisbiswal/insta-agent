import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.video.engine_3d import Engine3D

previews_dir = PROJECT_ROOT / "insta content" / "3d_previews"
previews_dir.mkdir(parents=True, exist_ok=True)

test_scenarios = [
    ("1_mars_astrology.jpg", "MANGAL DOSHA DANGER", "Vedic Astrology", 1),
    ("2_sun_astrology.jpg", "SURYA MAHADASHA ROYALTY", "Vedic Astrology", 1),
    ("3_jupiter_astrology.jpg", "STOP WEARING PUKHRAJ", "Vedic Astrology", 1),
    ("4_crypto_gold_coin.jpg", "BITCOIN 2026 SUPERCYCLE", "Crypto & Web3", 1),
    ("5_cyber_ai_core.jpg", "AI AGENTS REPLACING CODERS", "AI & Technology", 1),
    ("6_rahu_eclipse.jpg", "RAHU OBSESSION ILLUSION", "Vedic Astrology", 1),
]

for filename, topic, niche, scene_num in test_scenarios:
    detected = Engine3D.detect_3d_object_type(topic=topic, niche=niche)
    frame = Engine3D.render_full_3d_scene_frame(
        t=1.8,
        on_screen_text=topic.upper(),
        scene_number=scene_num,
        total_scenes=5,
        planet_type=detected,
        topic=topic,
        niche=niche,
    )
    out_path = previews_dir / filename
    frame.save(out_path, quality=92)
    print(f"[3D ENGINE] Rendered {detected:12} for: \"{topic}\" -> {out_path.name}")

print("\nALL 3D MULTI-NICHE PREVIEWS SAVED TO:", previews_dir)
