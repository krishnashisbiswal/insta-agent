"""
Phase 9 Production Runner & Real Reel Visual Inspector.
Generates and inspects 4 distinct real test Reels across:
1. Multi-Subject Adversarial Reel (Career -> Saturn -> Marriage -> Emerald -> Consultation CTA)
2. Saturn / Marriage Delay (7th House)
3. Career / 10th House (Karma Bhava)
4. Gemstone Recommendation (Emerald / Mercury)

For each Reel:
- Generates 1080x1920 MP4 with audio and frame-synced visuals using the production pipeline.
- Extracts actual physical frames from the rendered video at scene midpoints.
- Builds a 9:16 vertical contact sheet combining extracted frames with narration.
- Executes ProductionReelVerifier and logs complete audit report.
- Asserts strict semantic compliance (no forced gemstones, temples, or irrelevant filler).
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.video.cinematic_composer import create_cinematic_reel_video
from app.video.production_verifier import ProductionReelVerifier
from app.storage.production_workspace import ProductionWorkspaceManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Phase9Inspector")

TEST_REELS = [
    {
        "id": "reel_adversarial_multisect",
        "topic": "संपूर्ण ज्योतिष विश्लेषण: करियर, शनि प्रभाव, विवाह और रत्न परामर्श",
        "expected_domain": "multi_subject",
        "forbidden_in_all_scenes": ["temple", "havan", "fire_altar"],
        "scenes": [
            {
                "scene_idx": 0,
                "spoken_line": "अगर आपके करियर में मेहनत के बाद भी रुकावट आ रही है, तो अपनी कुंडली का दसवां भाव जरूर देखें।",
                "on_screen_text": "CAREER 10TH HOUSE",
                "visual_description": "Executive wooden desk with journal, pen, and focused professional morning workspace atmosphere",
                "scene_expected": "career",
                "scene_forbidden": ["gemstone", "sapphire", "emerald", "temple"],
            },
            {
                "scene_idx": 1,
                "spoken_line": "शनि का प्रभाव आपके कर्म और धैर्य की परीक्षा लेता है, ताकि आपको स्थायी सफलता मिल सके।",
                "on_screen_text": "SHANI KARMIC DISCIPLINE",
                "visual_description": "Planet Saturn with majestic glowing rings in deep cosmic starfield space",
                "scene_expected": "saturn",
                "scene_forbidden": ["gemstone", "emerald", "temple"],
            },
            {
                "scene_idx": 2,
                "spoken_line": "विवाह में आने वाली देरी के लिए कुंडली के सातवें भाव और बृहस्पति की दृष्टि का विश्लेषण जरूरी है।",
                "on_screen_text": "7TH HOUSE MARRIAGE",
                "visual_description": "Authentic North Indian Vedic Kundli birth chart highlighting the 7th house Yuvati Bhava in warm amber light",
                "scene_expected": "marriage",
                "scene_forbidden": ["gemstone", "career", "temple"],
            },
            {
                "scene_idx": 3,
                "spoken_line": "बुध को मजबूत करने के लिए जाम्बियन पन्ना रत्न तभी पहनें जब ग्रह आपकी कुंडली में कारक हो।",
                "on_screen_text": "PANNA EMERALD GEMSTONE",
                "visual_description": "Certified natural vivid green Zambian Emerald gemstone glowing with crystalline facets",
                "scene_expected": "gemstone",
                "scene_forbidden": ["marriage", "temple"],
            },
            {
                "scene_idx": 4,
                "spoken_line": "अपनी कुंडली का व्यक्तिगत विश्लेषण करवाने के लिए नीचे कमेंट करें या सीधे डीएम करें।",
                "on_screen_text": "DM FOR CONSULTATION",
                "visual_description": "A warm, dignified cinematic close-up of a professional Vedic astrologer consultation desk with handwritten horoscope charts on aged parchment and brass reading lamp",
                "scene_expected": "consultation",
                "scene_forbidden": ["gemstone", "temple", "havan"],
            },
        ],
    },
    {
        "id": "reel_saturn_marriage",
        "topic": "शनि और 7वां भाव: विवाह में देरी के असली कारण",
        "expected_domain": "marriage",
        "forbidden_in_all_scenes": ["gemstone", "sapphire", "emerald", "temple", "havan", "fire_altar"],
        "scenes": [
            {
                "scene_idx": 0,
                "spoken_line": "क्या आपकी शादी में बार-बार रिश्ते आकर टूट रहे हैं? इसका कारण शनि हो सकता है।",
                "on_screen_text": "MARRIAGE DELAYS",
                "visual_description": "Vedic Kundli birth chart highlighting 7th house Yuvati Bhava with partnership harmony",
            },
            {
                "scene_idx": 1,
                "spoken_line": "जब शनि की दृष्टि कुंडली के सातवें भाव पर पड़ती है, तो विवाह में देरी और गंभीर परीक्षाएं आती हैं।",
                "on_screen_text": "7TH HOUSE SHANI",
                "visual_description": "North Indian Vedic Kundli birth chart with illuminated 7th House and Saturn placement",
            },
            {
                "scene_idx": 2,
                "spoken_line": "शनि का उद्देश्य विवाह तोड़ना नहीं, बल्कि एक परिपक्व और स्थायी जीवनसाथी चुनना होता है।",
                "on_screen_text": "KARMIC LESSON",
                "visual_description": "Two respectful partner silhouettes walking side by side toward twilight horizon in quiet harmony",
            },
            {
                "scene_idx": 3,
                "spoken_line": "अपनी कुंडली में 7वें भाव की सटीक स्थिति जांचने के लिए कमेंट करें या पर्सनल परामर्श के लिए डीएम करें।",
                "on_screen_text": "DM FOR CONSULTATION",
                "visual_description": "Vedic astrologer consultation desk with authentic parchment charts and brass reading lamp",
            },
        ],
    },
    {
        "id": "reel_career_10th_house",
        "topic": "कुंडली का 10वां भाव और करियर: रुकावट या बड़ी सफलता?",
        "expected_domain": "career",
        "forbidden_in_all_scenes": ["marriage", "wedding", "gemstone", "temple", "havan", "fire_altar"],
        "scenes": [
            {
                "scene_idx": 0,
                "spoken_line": "क्या आप सालों से एक ही पद पर अटके हैं और मेहनत के बाद भी प्रमोशन नहीं मिल रहा?",
                "on_screen_text": "CAREER STAGNATION",
                "visual_description": "Clean executive desk workspace journal focus in morning window light",
            },
            {
                "scene_idx": 1,
                "spoken_line": "आपकी कुंडली का दसवां भाव यानी कर्म भाव तय करता है कि आपको सरकारी पद मिलेगा या बड़ा व्यापार।",
                "on_screen_text": "10TH HOUSE KARMA",
                "visual_description": "Authentic North Indian Vedic Kundli birth chart with illuminated 10th House Karma Bhava",
            },
            {
                "scene_idx": 2,
                "spoken_line": "जब दसवें भाव में शुभ ग्रहों की दृष्टि होती है, तो अचानक बड़ा पद और लीडरशिप रोल मिलता है।",
                "on_screen_text": "LEADERSHIP ROLE",
                "visual_description": "Executive wooden desk with journal, pen, and focused professional morning atmosphere",
            },
            {
                "scene_idx": 3,
                "spoken_line": "अपने करियर की सही दिशा और महादशा जानने के लिए नीचे कमेंट करें या परामर्श के लिए डीएम करें।",
                "on_screen_text": "DM FOR GUIDANCE",
                "visual_description": "Thoughtful Vedic astrologer consultation desk with handwritten horoscope charts on parchment",
            },
        ],
    },
    {
        "id": "reel_gemstone_emerald",
        "topic": "बुध के लिए पन्ना रत्न: क्या आपको एमराल्ड पहनना चाहिए?",
        "expected_domain": "gemstone",
        "forbidden_in_all_scenes": ["marriage", "wedding", "temple", "havan", "fire_altar"],
        "scenes": [
            {
                "scene_idx": 0,
                "spoken_line": "अगर आपकी याददाश्त कमजोर है या बिजनेस में डिसीजन गलत हो रहे हैं, तो बुध कमजोर हो सकता है।",
                "on_screen_text": "WEAK MERCURY",
                "visual_description": "Authentic Vedic Kundli birth chart showing planet Mercury placement with subtle gold aura",
            },
            {
                "scene_idx": 1,
                "spoken_line": "बुध ग्रह को बल देने के लिए प्राकृतिक जाम्बियन पन्ना यानी ग्रीन एमराल्ड धारण किया जाता है।",
                "on_screen_text": "NATURAL EMERALD",
                "visual_description": "Certified natural vivid green Zambian Emerald gemstone glowing with crystalline facets",
            },
            {
                "scene_idx": 2,
                "spoken_line": "लेकिन बिना कुंडली में बुध के भाव और दृष्टि जांचे कोई भी रत्न कभी नहीं पहनना चाहिए।",
                "on_screen_text": "CAUTION",
                "visual_description": "Authentic Vedic Kundli birth chart manuscript with illuminated Sanskrit house divisions and glyphs",
            },
            {
                "scene_idx": 3,
                "spoken_line": "अपनी कुंडली के अनुसार सही रत्न जानने के लिए नीचे कमेंट करें या पर्सनल सलाह के लिए डीएम करें।",
                "on_screen_text": "DM FOR CONSULTATION",
                "visual_description": "Professional Vedic astrologer consultation desk with authentic parchment charts and reading lamp",
            },
        ],
    },
]


def build_contact_sheet(
    reel_id: str,
    video_path: Path,
    scenes: List[Dict[str, Any]],
    output_path: Path,
) -> Path:
    """
    Extracts physical video frames at each scene's midpoint from the rendered MP4
    and compiles a horizontal contact sheet with scene index and narration.
    """
    from moviepy import VideoFileClip
    thumb_w, thumb_h = 360, 640
    padding = 20
    header_h = 80
    total_w = len(scenes) * (thumb_w + padding) + padding
    total_h = thumb_h + header_h + 100

    sheet = Image.new("RGB", (total_w, total_h), (18, 18, 24))
    draw = ImageDraw.Draw(sheet)

    with VideoFileClip(str(video_path)) as clip:
        dur = clip.duration
        sc_dur = dur / len(scenes)

        for idx, sc in enumerate(scenes):
            t_mid = min(dur - 0.2, (idx + 0.5) * sc_dur)
            frame_arr = clip.get_frame(t_mid)
            f_img = Image.fromarray(frame_arr)
            thumb = f_img.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)

            x = padding + idx * (thumb_w + padding)
            y = header_h + 10
            sheet.paste(thumb, (x, y))

            # Draw labels
            sc_num = idx + 1
            draw.text((x + 10, y + 10), f"SCENE {sc_num}", fill=(255, 215, 0))
            draw.text((x + 10, y + thumb_h + 10), sc.get("on_screen_text", ""), fill=(255, 255, 255))
            spoken_snippet = sc.get("spoken_line", "")[:35] + "..."
            draw.text((x + 10, y + thumb_h + 30), spoken_snippet, fill=(200, 200, 200))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=95)
    return output_path


def run_inspection(target_reels: List[str] = None) -> List[Dict[str, Any]]:
    results = []
    print("\n" + "=" * 78)
    print("      PHASE 9: COMPREHENSIVE REEL GENERATION & REAL OUTPUT INSPECTION")
    print("=" * 78)

    reels_to_run = [r for r in TEST_REELS if not target_reels or r["id"] in target_reels]

    for reel_spec in reels_to_run:
        r_id = reel_spec["id"]
        topic = reel_spec["topic"]
        scenes = reel_spec["scenes"]
        print(f"\n[RUNNING REEL TEST] {r_id.upper()}")
        print(f" -> Topic: {topic}")
        print(f" -> Scene Count: {len(scenes)}")

        ws = ProductionWorkspaceManager.create_workspace()
        script_data = {
            "topic": topic,
            "language": "Hinglish",
            "scenes": scenes,
            "selected_hook": {
                "spoken": scenes[0]["spoken_line"],
                "on_screen": scenes[0]["on_screen_text"],
            },
        }

        # Render 1080x1920 video
        video_path = create_cinematic_reel_video(
            script_data=script_data,
            voice="astrologer",
            production_workspace=ws,
            job_id=r_id,
        )

        assert video_path.exists(), f"Video file was not created: {video_path}"
        assert video_path.stat().st_size > 5 * 1024 * 1024, f"Video unexpectedly small ({video_path.stat().st_size} bytes)"

        # Extract frames & Build Contact Sheet
        contact_sheet_path = ws.workspace_dir / f"{r_id}_contact_sheet.jpg"
        build_contact_sheet(r_id, video_path, scenes, contact_sheet_path)
        print(f" -> Contact Sheet Generated: {contact_sheet_path.name}")

        # Run Strict Production Verifier
        report = ProductionReelVerifier.verify_production(
            video_path=video_path,
            script_data=script_data,
            job_id=r_id,
        )

        txt_report = report.format_text_report()
        report_txt_file = ws.workspace_dir / "verification_report.txt"
        report_txt_file.write_text(txt_report, encoding="utf-8")
        report_json_file = ws.workspace_dir / "verification_report.json"
        report_json_file.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

        print(f" -> Verifier Status: [{report.overall_status}]")
        print(f" -> Resolution: {report.video_summary.get('resolution')} (Aspect Ratio: {report.video_summary.get('aspect_ratio')})")
        print(f" -> Duration: {report.video_summary.get('duration'):.2f}s | FPS: {report.video_summary.get('fps')}")

        # Strict Domain & Semantic Verification across all scenes
        scene_assets = []
        scene_descriptions = []
        for idx, sc_rec in enumerate(report.scenes):
            asset_name = sc_rec.selected_asset_name.lower()
            vis_desc = sc_rec.visual_description.lower()
            scene_assets.append(asset_name)
            scene_descriptions.append(vis_desc)

            assert sc_rec.relevance_status == "PASS", f"Scene {sc_rec.scene_number} failed relevance: {sc_rec.relevance_reason}"

            # Check forbidden items across entire reel
            for forb in reel_spec.get("forbidden_in_all_scenes", []):
                assert forb not in asset_name, f"Forbidden element '{forb}' detected in asset filename {asset_name} for Reel '{r_id}' Scene {sc_rec.scene_number}"
                assert forb not in vis_desc, f"Forbidden element '{forb}' detected in visual spec '{vis_desc}' for Reel '{r_id}' Scene {sc_rec.scene_number}"

            # Check per-scene assertions if defined
            sc_def = scenes[idx] if idx < len(scenes) else {}
            for forb in sc_def.get("scene_forbidden", []):
                assert forb not in asset_name, f"Per-scene forbidden element '{forb}' detected in asset {asset_name} for Scene {idx+1}"
                assert forb not in vis_desc, f"Per-scene forbidden element '{forb}' detected in visual description for Scene {idx+1}"

            sc_exp = sc_def.get("scene_expected")
            if sc_exp == "career":
                assert any(k in vis_desc for k in ["career", "desk", "workspace", "10th", "karma"]), f"Career expectation not met in Scene {idx+1}"
            elif sc_exp == "saturn":
                assert any(k in vis_desc for k in ["saturn", "shani", "planet"]), f"Saturn expectation not met in Scene {idx+1}"
            elif sc_exp == "marriage":
                assert any(k in vis_desc for k in ["7th house", "marriage", "kalatra", "yuvati"]), f"Marriage expectation not met in Scene {idx+1}"
            elif sc_exp == "gemstone":
                assert any(k in vis_desc for k in ["emerald", "panna", "gemstone", "mercury"]), f"Gemstone expectation not met in Scene {idx+1}"
            elif sc_exp == "consultation":
                assert any(k in vis_desc for k in ["consultation", "study", "desk", "parchment"]), f"Consultation expectation not met in Scene {idx+1}"

        all_desc = " ".join(scene_descriptions)
        all_assets = " ".join(scene_assets)

        # Topic-specific domain assertions
        if reel_spec["expected_domain"] == "marriage":
            assert any(k in all_desc for k in ["7th", "kundli", "chart", "silhouette", "partnership", "consultation"])
            assert not any("gemstone" in a or "gemstone" in d for a, d in zip(scene_assets, scene_descriptions))
            assert not any("temple" in a or "temple" in d for a, d in zip(scene_assets, scene_descriptions))
        elif reel_spec["expected_domain"] == "career":
            assert any(k in all_desc for k in ["10th", "kundli", "chart", "executive", "desk", "consultation", "karma"])
            assert not any("marriage" in a or "marriage" in d for a, d in zip(scene_assets, scene_descriptions))
            assert not any("gemstone" in a or "gemstone" in d for a, d in zip(scene_assets, scene_descriptions))
            assert not any("temple" in a or "temple" in d for a, d in zip(scene_assets, scene_descriptions))
        elif reel_spec["expected_domain"] == "gemstone":
            assert any(k in all_desc for k in ["emerald", "panna", "gemstone", "mercury", "kundli", "consultation"])
            assert not any("marriage" in a or "marriage" in d for a, d in zip(scene_assets, scene_descriptions))
            assert not any("temple" in a or "temple" in d for a, d in zip(scene_assets, scene_descriptions))

        results.append({
            "reel_id": r_id,
            "topic": topic,
            "video_path": str(video_path),
            "contact_sheet": str(contact_sheet_path),
            "report_path": str(report_txt_file),
            "overall_status": report.overall_status,
            "scenes": [
                {
                    "scene": sc.scene_number,
                    "narration": sc.spoken_narration,
                    "asset": sc.selected_asset_name,
                    "relevance": sc.relevance_status,
                }
                for sc in report.scenes
            ],
        })

    print("\n" + "=" * 78)
    print("      ALL REELS GENERATED AND STRICTLY VERIFIED SUCCESSFULLY!")
    print("=" * 78)
    return results


if __name__ == "__main__":
    target = sys.argv[1:] if len(sys.argv) > 1 else None
    run_inspection(target)
